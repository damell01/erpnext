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

    @frappe.whitelist()
    def create_warehouse(self):
        """
        Create an ERPNext Warehouse for this streamer and link it on the record.
        e.g. "Jordan Inventory - VB"
        ERPNext's existing warehouse system handles all stock tracking;
        we just need a dedicated bin for each streamer.
        """
        from vortex_ops.setup.inventory_setup import create_streamer_warehouse

        company = frappe.defaults.get_global_default("company")
        wh_name = create_streamer_warehouse(self.streamer_name, company=company)
        self.db_set("warehouse", wh_name)
        return wh_name

    @frappe.whitelist()
    def get_inventory_summary(self):
        """
        Return current stock totals for this streamer's warehouse.
        Reads from ERPNext's tabBin — no custom inventory system needed.
        """
        if not self.warehouse:
            return {"total_items": 0, "total_value": 0, "lines": []}

        lines = frappe.db.sql(
            """
            SELECT
                b.item_code,
                i.item_name,
                i.item_group,
                b.actual_qty,
                i.valuation_rate,
                b.actual_qty * i.valuation_rate AS total_value
            FROM `tabBin` b
            JOIN `tabItem` i ON i.item_code = b.item_code
            WHERE b.warehouse = %s AND b.actual_qty > 0
            ORDER BY i.item_name
            """,
            self.warehouse,
            as_dict=True,
        )
        return {
            "total_items": len(lines),
            "total_value": sum(l.total_value or 0 for l in lines),
            "lines":       lines,
        }
