import frappe
from frappe.model.document import Document


class AutomationLog(Document):
    def before_insert(self):
        if not self.run_by:
            self.run_by = frappe.session.user

    def after_insert(self):
        # Keep log lean — prune entries older than 90 days
        frappe.db.sql(
            "DELETE FROM `tabAutomation Log` "
            "WHERE run_at < DATE_SUB(NOW(), INTERVAL 90 DAY)"
        )
