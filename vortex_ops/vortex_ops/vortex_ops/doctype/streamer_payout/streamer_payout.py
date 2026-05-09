import frappe
from frappe.model.document import Document
from vortex_ops.utils import safe_float


def validate_doc(doc, method=None):
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

    def calc_all(self):
        gross = safe_float(self.gross_sales)
        pct   = safe_float(self.profit_share_pct)
        pkgs  = safe_float(self.package_count)
        rate  = safe_float(self.package_rate)
        tips  = safe_float(self.tips)
        adj   = safe_float(self.adjustments)
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
        r = frappe.db.sql(
            """
            SELECT COALESCE(SUM(repayment_amount), 0) AS t
            FROM `tabLoan Repayment`
            WHERE streamer = %s
              AND payout_period = %s
              AND status = 'Scheduled'
              AND docstatus = 1
            """,
            (self.streamer, self.payout_period),
            as_dict=True,
        )
        return safe_float(r[0].t if r else 0)

    @frappe.whitelist()
    def pull_stream_data(self):
        """
        Pull gross sales, package count, and tips from all streams in the
        payout period where this streamer was listed as primary or additional.
        Handles multi-streamer shows correctly — only counts this streamer's
        attributed data, not the full show total.
        """
        if not self.payout_period:
            frappe.throw("Set Payout Period first")

        period = frappe.get_doc("Payout Period", self.payout_period)
        names  = [s.stream_event for s in period.streams if s.stream_event]
        if not names:
            frappe.throw("No streams linked to this payout period")

        ph = ",".join(["%s"] * len(names))

        # Gross sales from streams where this streamer was primary OR additional
        r = frappe.db.sql(
            f"""
            SELECT
                SUM(se.gross_sales)     g,
                SUM(se.total_packages)  p,
                SUM(se.tips)            t
            FROM `tabStream Event` se
            WHERE se.name IN ({ph})
              AND (
                  se.primary_streamer = %s
                  OR EXISTS (
                      SELECT 1 FROM `tabStream Streamer` ss
                      WHERE ss.parent = se.name AND ss.streamer = %s
                  )
              )
              AND se.docstatus = 1
            """,
            (*names, self.streamer, self.streamer),
            as_dict=True,
        )

        # Also sum packages_sold from Stream Streamer child rows for this streamer
        pkg_override = frappe.db.sql(
            f"""
            SELECT COALESCE(SUM(ss.packages_sold), 0) pkg
            FROM `tabStream Streamer` ss
            WHERE ss.parent IN ({ph})
              AND ss.streamer = %s
            """,
            (*names, self.streamer),
            as_dict=True,
        )
        override_pkgs = int(pkg_override[0].pkg if pkg_override else 0)

        if r and r[0].g is not None:
            self.gross_sales   = safe_float(r[0].g)
            self.package_count = override_pkgs if override_pkgs > 0 else int(r[0].p or 0)
            self.tips          = safe_float(r[0].t)
            self.save()
            frappe.msgprint("Stream data pulled successfully.", indicator="green")
        else:
            frappe.msgprint(
                "No stream data found for this streamer in the selected period.",
                indicator="orange",
            )
