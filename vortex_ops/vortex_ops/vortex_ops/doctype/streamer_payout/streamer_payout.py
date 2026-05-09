import frappe
from frappe.model.document import Document
from vortex_ops.utils import safe_float


def validate_doc(doc, method=None):
    # Only pull settings when first creating — avoids clobbering manual rate edits on every save
    if doc.is_new() or not doc.payout_type:
        doc.pull_settings()
    doc.calc_all()


def on_submit(doc, method=None):
    doc.db_set("status", "Reviewed")


class StreamerPayout(Document):

    def pull_settings(self):
        if not self.streamer:
            return
        s = frappe.get_doc("Streamer", self.streamer)
        self.payout_type              = s.payout_type
        self.profit_share_pct         = s.payout_percentage or 0
        self.package_rate             = s.package_rate      or 0
        self.adp_employee_id          = s.adp_employee_id
        self.owner_platform_fee_pct   = s.owner_platform_fee_pct or 0
        self.include_tips             = s.include_tips if hasattr(s, "include_tips") else 1

    def calc_all(self):
        gross   = safe_float(self.gross_sales)
        pct     = safe_float(self.profit_share_pct)
        pkgs    = safe_float(self.package_count)
        rate    = safe_float(self.package_rate)
        tips    = safe_float(self.tips) if self.include_tips else 0
        adj     = safe_float(self.adjustments)
        fee_pct = safe_float(self.owner_platform_fee_pct)

        self.profit_share_amount = (
            round(gross * pct / 100, 2) if self.payout_type == "Profit Share" else 0
        )
        self.package_payout            = round(pkgs * rate, 2)
        self.owner_platform_fee_amount = round(gross * fee_pct / 100, 2)
        self.loan_deductions           = self._get_loans()

        self.total_payout = round(
            safe_float(self.profit_share_amount)
            + self.package_payout
            + tips
            + adj
            - self.owner_platform_fee_amount
            - self.loan_deductions,
            2,
        )

        if self.total_payout < 0:
            frappe.msgprint(
                f"Warning: total payout is negative (${self.total_payout:.2f}). "
                "Review deductions before approving.",
                indicator="orange",
            )

    def _get_loans(self):
        """
        Sum all Scheduled repayments from Active Loan Records for this streamer.
        Picks up rows explicitly assigned to this payout period plus unassigned rows
        (payout_period blank), so the schedule works whether or not periods are
        pre-filled on each repayment row.
        """
        if not self.streamer or not self.payout_period:
            return 0.0

        r = frappe.db.sql(
            """
            SELECT COALESCE(SUM(lr.repayment_amount), 0) AS t
            FROM `tabLoan Repayment` lr
            JOIN `tabLoan Record` rec ON rec.name = lr.parent
            WHERE rec.streamer   = %s
              AND rec.docstatus  = 1
              AND rec.status     = 'Active'
              AND lr.status      = 'Scheduled'
              AND (lr.payout_period = %s OR lr.payout_period IS NULL OR lr.payout_period = '')
            """,
            (self.streamer, self.payout_period),
            as_dict=True,
        )
        return safe_float(r[0].t if r else 0)

    @frappe.whitelist()
    def approve_payout(self):
        """
        Advance status from Reviewed → Approved and mark matching loan
        repayment rows as Deducted so the loan balance updates.
        """
        if self.status != "Reviewed":
            frappe.throw("Only Reviewed payouts can be approved.")

        if self.loan_deductions and self.payout_period:
            loan_records = frappe.get_all(
                "Loan Record",
                filters={"streamer": self.streamer, "docstatus": 1, "status": "Active"},
                fields=["name"],
            )
            for lr_meta in loan_records:
                lr_doc = frappe.get_doc("Loan Record", lr_meta.name)
                changed = False
                for row in lr_doc.repayments:
                    if row.status == "Scheduled" and (
                        not row.payout_period or row.payout_period == self.payout_period
                    ):
                        row.status         = "Deducted"
                        row.payout_period  = self.payout_period
                        changed = True
                if changed:
                    lr_doc.save(ignore_permissions=True)

        self.db_set("status", "Approved")
        frappe.msgprint("Payout approved. Loan deductions recorded.", indicator="green")

    @frappe.whitelist()
    def pull_stream_data(self):
        """
        Pull gross sales, package count, and tips for this streamer from all
        streams in the payout period.

        For single-streamer shows the full show gross is attributed to the
        primary streamer.  For multi-streamer shows, co-hosts/guests should
        have their individual gross_sales entered on the Stream Streamer child
        row — if set, that value is used instead of the show total, preventing
        double-counting across streamers.
        """
        if not self.payout_period:
            frappe.throw("Set Payout Period first")

        period = frappe.get_doc("Payout Period", self.payout_period)
        names  = [s.stream_event for s in period.streams if s.stream_event]
        if not names:
            frappe.throw("No streams linked to this payout period")

        ph = ",".join(["%s"] * len(names))

        # Shows where this streamer is the primary (use full show gross)
        primary_r = frappe.db.sql(
            f"""
            SELECT
                COALESCE(SUM(se.gross_sales), 0)    g,
                COALESCE(SUM(se.total_packages), 0) p,
                COALESCE(SUM(se.tips), 0)           t
            FROM `tabStream Event` se
            WHERE se.name IN ({ph})
              AND se.primary_streamer = %s
              AND se.docstatus = 1
            """,
            (*names, self.streamer),
            as_dict=True,
        )

        # Shows where this streamer is listed as additional
        # Use their individual gross_sales from the child row if set,
        # otherwise fall back to the full show gross (handles legacy data)
        additional_r = frappe.db.sql(
            f"""
            SELECT
                COALESCE(
                    NULLIF(ss.gross_sales, 0),
                    se.gross_sales
                )                                   g,
                COALESCE(ss.packages_sold, 0)       p,
                se.tips                             t
            FROM `tabStream Streamer` ss
            JOIN `tabStream Event` se ON se.name = ss.parent
            WHERE ss.parent IN ({ph})
              AND ss.streamer = %s
              AND se.docstatus = 1
            """,
            (*names, self.streamer),
            as_dict=True,
        )

        total_gross = safe_float(primary_r[0].g if primary_r else 0)
        total_pkgs  = int(primary_r[0].p if primary_r else 0)
        total_tips  = safe_float(primary_r[0].t if primary_r else 0)

        for row in additional_r:
            total_gross += safe_float(row.g)
            total_pkgs  += int(row.p or 0)
            total_tips  += safe_float(row.t)

        # Package count from child rows takes priority over show-level total
        pkg_override = frappe.db.sql(
            f"""
            SELECT COALESCE(SUM(ss.packages_sold), 0) pkg
            FROM `tabStream Streamer` ss
            WHERE ss.parent IN ({ph}) AND ss.streamer = %s
            """,
            (*names, self.streamer),
            as_dict=True,
        )
        override_pkgs = int(pkg_override[0].pkg if pkg_override else 0)

        self.gross_sales   = round(total_gross, 2)
        self.package_count = override_pkgs if override_pkgs > 0 else total_pkgs
        self.tips          = round(total_tips, 2)
        self.save()
        frappe.msgprint("Stream data pulled successfully.", indicator="green")
