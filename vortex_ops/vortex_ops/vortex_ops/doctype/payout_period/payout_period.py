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
    def pull_streams(self):
        if not self.start_date or not self.end_date:
            frappe.throw("Set Start and End Date first")
        streams = frappe.get_all(
            "Stream Event",
            filters={
                "stream_date": ["between", [self.start_date, self.end_date]],
                "docstatus":   1,
            },
            fields=["name", "stream_date"],
        )
        self.streams = []
        for s in streams:
            self.append("streams", {
                "stream_event": s.name,
                "stream_date":  s.stream_date,
            })
        self.save()
        frappe.msgprint(f"Pulled {len(streams)} stream(s) into this period")
