import frappe
from frappe.model.document import Document
from vortex_ops.utils import safe_float


def validate_doc(doc, method=None):
    if doc.start_date and doc.end_date:
        if doc.start_date > doc.end_date:
            frappe.throw("Start Date must be before End Date")
    doc.calc_totals()


class PayoutPeriod(Document):

    def calc_totals(self):
        names = [s.stream_event for s in (self.streams or []) if s.stream_event]
        if not names:
            return
        ph = ",".join(["%s"] * len(names))
        r = frappe.db.sql(
            f"""
            SELECT
                SUM(gross_sales) g,
                SUM(net_earned)  n,
                SUM(tips)        t
            FROM `tabStream Event`
            WHERE name IN ({ph}) AND docstatus = 1
            """,
            names,
            as_dict=True,
        )
        if r:
            self.total_gross = safe_float(r[0].g)
            self.total_net   = safe_float(r[0].n)
            self.total_tips  = safe_float(r[0].t)

    @frappe.whitelist()
    def get_payout_summary(self):
        """Return per-status counts and totals for the payouts in this period."""
        payouts = frappe.get_all(
            "Streamer Payout",
            filters={"payout_period": self.name, "docstatus": ["!=", 2]},
            fields=["status", "total_payout", "streamer"],
        )
        total_payout = round(sum(safe_float(p.total_payout) for p in payouts), 2)
        by_status = {}
        for p in payouts:
            s = p.status or "Draft"
            if s not in by_status:
                by_status[s] = {"count": 0, "amount": 0.0}
            by_status[s]["count"]  += 1
            by_status[s]["amount"] = round(
                by_status[s]["amount"] + safe_float(p.total_payout), 2
            )

        return {
            "total":        len(payouts),
            "total_payout": total_payout,
            "by_status":    by_status,
        }

    @frappe.whitelist()
    def approve_all_reviewed(self):
        """Approve every Reviewed payout in this period and record loan deductions."""
        reviewed = frappe.get_all(
            "Streamer Payout",
            filters={"payout_period": self.name, "status": "Reviewed", "docstatus": 1},
            fields=["name", "streamer"],
        )
        if not reviewed:
            frappe.msgprint("No Reviewed payouts to approve.", indicator="blue")
            return []

        approved = []
        errors   = []
        for r in reviewed:
            try:
                doc = frappe.get_doc("Streamer Payout", r.name)
                doc.approve_payout()
                approved.append(r.streamer)
            except Exception as e:
                frappe.log_error(f"approve_all_reviewed failed for {r.streamer}: {e}")
                errors.append(r.streamer)

        parts = []
        if approved:
            parts.append(f"Approved {len(approved)}: {', '.join(approved)}")
        if errors:
            parts.append(f"Failed {len(errors)}: {', '.join(errors)} — check Error Log")

        frappe.msgprint("<br>".join(parts), indicator="green" if not errors else "orange")
        return approved

    @frappe.whitelist()
    def pull_streams(self):
        """Pull all submitted Stream Events in the date range for this business."""
        if not self.start_date or not self.end_date:
            frappe.throw("Set Start and End Date first")
        if not self.company:
            frappe.throw("Set Business first")

        filters = {
            "stream_date": ["between", [self.start_date, self.end_date]],
            "docstatus":   1,
            "company":     self.company,
        }

        streams = frappe.get_all(
            "Stream Event",
            filters=filters,
            fields=["name", "stream_date", "stream_title"],
            order_by="stream_date asc",
        )
        self.streams = []
        for s in streams:
            self.append("streams", {
                "stream_event": s.name,
                "stream_date":  s.stream_date,
            })
        self.save()
        frappe.msgprint(
            f"Pulled {len(streams)} stream(s) for {self.company}",
            indicator="green",
        )

    @frappe.whitelist()
    def generate_payouts(self):
        """
        Find every streamer who appeared in this period's streams (primary or
        additional) and create a Streamer Payout for each one.  Already-existing
        payouts for this period are skipped.  Stream data is pulled automatically.
        """
        stream_names = [s.stream_event for s in (self.streams or []) if s.stream_event]
        if not stream_names:
            frappe.throw("Pull streams into this period first, then generate payouts.")

        ph = ",".join(["%s"] * len(stream_names))

        streamers = set()

        for r in frappe.db.sql(
            f"SELECT DISTINCT primary_streamer s FROM `tabStream Event` "
            f"WHERE name IN ({ph}) AND primary_streamer IS NOT NULL AND docstatus = 1",
            stream_names, as_dict=True,
        ):
            if r.s:
                streamers.add(r.s)

        for r in frappe.db.sql(
            f"SELECT DISTINCT streamer s FROM `tabStream Streamer` "
            f"WHERE parent IN ({ph}) AND streamer IS NOT NULL",
            stream_names, as_dict=True,
        ):
            if r.s:
                streamers.add(r.s)

        created = []
        skipped = []

        for streamer in sorted(streamers):
            if frappe.db.exists("Streamer Payout", {
                "payout_period": self.name,
                "streamer":      streamer,
                "docstatus":     ["!=", 2],
            }):
                skipped.append(streamer)
                continue

            payout = frappe.new_doc("Streamer Payout")
            payout.payout_period = self.name
            payout.streamer      = streamer
            payout.insert(ignore_permissions=True)

            try:
                payout.reload()
                payout.pull_stream_data()
            except Exception as e:
                frappe.log_error(f"pull_stream_data failed for {streamer}: {e}")

            created.append(streamer)

        frappe.db.commit()

        parts = []
        if created:
            parts.append(f"Created {len(created)} payout(s): {', '.join(created)}")
        if skipped:
            parts.append(f"Skipped {len(skipped)} already existing")

        frappe.msgprint(
            "<br>".join(parts) or "No new payouts needed",
            indicator="green",
        )
        return created
