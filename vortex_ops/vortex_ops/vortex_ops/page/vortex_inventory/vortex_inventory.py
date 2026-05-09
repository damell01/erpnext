import frappe


@frappe.whitelist()
def get_page_data():
    from vortex_ops.setup.inventory_setup import list_inventory_locations
    return list_inventory_locations()
