import frappe
from frappe.model.document import Document
from vortex_ops.utils import safe_float


def on_submit(doc, method=None):
    doc.db_set("status", "Active")


def on_cancel(doc, method=None):
    doc.db_set("status", "Cancelled")


class LoanRecord(Document):
    def validate(self):
        self.calc_balance()
        self.check_schedule()

    def calc_balance(self):
        repaid = sum(
            safe_float(r.repayment_amount)
            for r in self.repayments
            if r.status == "Deducted"
        )
        self.amount_repaid = round(repaid, 2)
        self.balance       = round(safe_float(self.loan_amount) - repaid, 2)
        if self.balance <= 0 and self.status == "Active":
            self.status = "Paid Off"

    def check_schedule(self):
        scheduled = sum(safe_float(r.repayment_amount) for r in self.repayments)
        if scheduled > safe_float(self.loan_amount):
            frappe.msgprint(
                f"Scheduled repayments (${scheduled:,.2f}) exceed loan amount "
                f"(${self.loan_amount:,.2f}). Review the schedule.",
                indicator="orange",
            )
