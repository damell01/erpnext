import frappe
from frappe.model.document import Document
from vortex_ops.utils import safe_float, get_streamer_loan_balance


class Streamer(Document):
    def validate(self):
        self._check_payout()
        self._sync_email()

    def _check_payout(self):
        if self.payout_type == "Profit Share":
            if not self.payout_percentage or self.payout_percentage <= 0:
                frappe.throw("Profit Share % is required for Profit Share payout type")
        elif self.payout_type == "Package":
            if not self.package_rate or self.package_rate <= 0:
                frappe.throw("Package Rate is required for Package payout type")

    def _sync_email(self):
        if self.user and not self.email:
            self.email = frappe.db.get_value("User", self.user, "email")

    @frappe.whitelist()
    def get_loan_balance(self):
        return get_streamer_loan_balance(self.name)
