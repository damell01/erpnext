"""
Vortex Ops — Inventory Foundation Setup
========================================
Run once after installing the app to create all the ERPNext base records
needed before adding streamers or inventory.

Usage (on the server):
    cd ~/frappe-bench
    bench --site vortex.yourdomain.com execute vortex_ops.setup.inventory_setup.run

Or from a Frappe console:
    from vortex_ops.setup.inventory_setup import run
    run()
"""

import frappe
from frappe.utils import now_datetime


def run():
    """Entry point. Call from bench execute or the UI setup button."""
    company = frappe.defaults.get_global_default("company")
    if not company:
        frappe.throw(
            "No default company found. "
            "Go to Accounting > Setup > Company and create one first."
        )

    abbr = frappe.db.get_value("Company", company, "abbr") or "VB"
    results = []

    results += _create_uom()
    results += _create_item_groups()
    results += _create_warehouses(company, abbr)

    frappe.db.commit()

    summary = "\n".join(f"  {r}" for r in results)
    print(f"\nVortex Inventory Setup Complete\n{summary}\n")
    return results


# ── Units of Measure ──────────────────────────────────────────────────────────

def _create_uom():
    uoms = ["Box", "Case", "Pack", "Lot", "Card"]
    created = []
    for name in uoms:
        if not frappe.db.exists("UOM", name):
            doc = frappe.new_doc("UOM")
            doc.uom_name = name
            doc.insert(ignore_permissions=True)
            created.append(f"Created UOM: {name}")
        else:
            created.append(f"UOM exists:  {name}")
    return created


# ── Item Groups ───────────────────────────────────────────────────────────────

def _create_item_groups():
    groups = [
        ("Break Products",    "All Item Groups"),
        ("Sports Cards",      "Break Products"),
        ("Trading Card Games","Break Products"),
        ("Sealed Wax",        "Break Products"),
        ("Memorabilia",       "Break Products"),
        ("Mystery / Other",   "Break Products"),
    ]
    created = []
    for name, parent in groups:
        if not frappe.db.exists("Item Group", name):
            doc = frappe.new_doc("Item Group")
            doc.item_group_name = name
            doc.parent_item_group = parent
            doc.insert(ignore_permissions=True)
            created.append(f"Created Item Group: {name}")
        else:
            created.append(f"Item Group exists: {name}")
    return created


# ── Warehouses ────────────────────────────────────────────────────────────────

_BASE_WAREHOUSES = [
    # (name, parent_suffix, warehouse_type)
    ("Main Storage",        "All Warehouses", "Stores"),
    ("Returned Inventory",  "All Warehouses", "Stores"),
    ("Damaged Inventory",   "All Warehouses", "Stores"),
    ("Fulfillment Area",    "All Warehouses", "Transit"),
]


def _create_warehouses(company, abbr):
    created = []
    for name, parent_base, wtype in _BASE_WAREHOUSES:
        full_name   = f"{name} - {abbr}"
        parent_name = f"{parent_base} - {abbr}"
        if not frappe.db.exists("Warehouse", full_name):
            doc = frappe.new_doc("Warehouse")
            doc.warehouse_name = name
            doc.parent_warehouse = parent_name
            doc.warehouse_type  = wtype
            doc.company         = company
            doc.insert(ignore_permissions=True)
            created.append(f"Created Warehouse: {full_name}")
        else:
            created.append(f"Warehouse exists: {full_name}")
    return created


# ── Per-streamer warehouse creation ──────────────────────────────────────────

def create_streamer_warehouse(streamer_name: str, company: str = None, abbr: str = None):
    """
    Create a personal inventory warehouse for a streamer.
    Called from the Streamer DocType "Create Warehouse" button.
    Returns the warehouse name.
    """
    if not company:
        company = frappe.defaults.get_global_default("company")
    if not abbr:
        abbr = frappe.db.get_value("Company", company, "abbr") or "VB"

    warehouse_label = f"{streamer_name} Inventory"
    full_name       = f"{warehouse_label} - {abbr}"
    parent_name     = f"All Warehouses - {abbr}"

    if frappe.db.exists("Warehouse", full_name):
        frappe.msgprint(f"Warehouse already exists: {full_name}", indicator="blue")
        return full_name

    doc = frappe.new_doc("Warehouse")
    doc.warehouse_name  = warehouse_label
    doc.parent_warehouse = parent_name
    doc.warehouse_type  = "Stores"
    doc.company         = company
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.msgprint(
        f"Warehouse created: {full_name}",
        indicator="green",
    )
    return full_name


@frappe.whitelist()
def setup_from_ui():
    """Called from the Vortex Ops workspace setup button."""
    results = run()
    return results


@frappe.whitelist()
def transfer_stock(from_warehouse, to_warehouse, item_code, qty, remarks=""):
    """
    Material Transfer between warehouses.
    Typical use: split a bulk shipment from Main Storage into streamer warehouses.
    ERPNext handles valuation and ledger — we just build the Stock Entry.
    """
    company = frappe.defaults.get_global_default("company")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer"
    se.company          = company
    se.remarks          = remarks or f"Transfer from {from_warehouse} to {to_warehouse}"

    se.append("items", {
        "item_code":   item_code,
        "qty":         float(qty),
        "s_warehouse": from_warehouse,
        "t_warehouse": to_warehouse,
    })

    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()

    return se.name


@frappe.whitelist()
def quick_stock_receipt(warehouse, item_code, qty, basic_rate=0, remarks=""):
    """
    Create a Material Receipt Stock Entry into a specific warehouse.
    ERPNext's existing stock system handles all ledger math.
    Called from the Streamer form "Add Stock" dialog.
    Returns the Stock Entry name.
    """
    company = frappe.defaults.get_global_default("company")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.company          = company
    se.remarks          = remarks or f"Stock receipt into {warehouse}"

    se.append("items", {
        "item_code":   item_code,
        "qty":         float(qty),
        "t_warehouse": warehouse,
        "basic_rate":  float(basic_rate or 0),
    })

    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()

    return se.name
