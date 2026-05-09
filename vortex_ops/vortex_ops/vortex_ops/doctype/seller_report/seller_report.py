import frappe
from frappe.model.document import Document


class SellerReport(Document):
    def validate(self):
        if self.stream_event and not self.report_date:
            self.report_date = frappe.db.get_value(
                "Stream Event", self.stream_event, "stream_date"
            )
        if (self.adjustments or 0) != 0 and not self.adjustment_reason:
            frappe.throw("Adjustment Reason is required when Adjustments is non-zero")

    def on_submit(self):
        self.db_set("submitted_by", frappe.session.user)
        self.db_set("status", "Submitted")
