import frappe
from frappe.model.document import Document


class FulfillmentReport(Document):
    def validate(self):
        shipped = self.packages_shipped or 0
        held    = self.packages_held    or 0
        total   = self.total_packages   or 0
        if shipped + held > total:
            frappe.throw(
                f"Shipped ({shipped}) + Held ({held}) cannot exceed Total ({total})"
            )

    def on_submit(self):
        self.db_set("status", "Submitted")
