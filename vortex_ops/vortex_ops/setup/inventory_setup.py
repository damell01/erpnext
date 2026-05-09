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

    _ensure_custom_field()
    results += _create_uom()
    results += _create_item_groups()
    results += _create_warehouses(company, abbr)

    frappe.db.commit()

    summary = "\n".join(f"  {r}" for r in results)
    print(f"\nVortex Inventory Setup Complete\n{summary}\n")
    return results


def _ensure_custom_field():
    """Add is_vortex_managed checkbox to Warehouse DocType if not already present."""
    if frappe.db.exists("Custom Field", "Warehouse-is_vortex_managed"):
        return
    cf = frappe.new_doc("Custom Field")
    cf.dt           = "Warehouse"
    cf.fieldname    = "is_vortex_managed"
    cf.fieldtype    = "Check"
    cf.label        = "Vortex Managed"
    cf.insert_after = "warehouse_type"
    cf.hidden       = 1
    cf.no_copy      = 1
    cf.insert(ignore_permissions=True)
    frappe.db.commit()


def _set_vortex_flag(warehouse_name):
    """Mark a warehouse as Vortex-managed. Silent no-op if field not yet created."""
    try:
        if frappe.db.exists("Custom Field", "Warehouse-is_vortex_managed"):
            frappe.db.set_value(
                "Warehouse", warehouse_name, "is_vortex_managed", 1,
                update_modified=False,
            )
    except Exception:
        pass


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
        ("Break Products",     "All Item Groups"),
        ("Sports Cards",       "Break Products"),
        ("Trading Card Games", "Break Products"),
        ("Sealed Wax",         "Break Products"),
        ("Memorabilia",        "Break Products"),
        ("Mystery / Other",    "Break Products"),
    ]
    created = []
    for name, parent in groups:
        if not frappe.db.exists("Item Group", name):
            doc = frappe.new_doc("Item Group")
            doc.item_group_name  = name
            doc.parent_item_group = parent
            doc.insert(ignore_permissions=True)
            created.append(f"Created Item Group: {name}")
        else:
            created.append(f"Item Group exists: {name}")
    return created


# ── Warehouses ────────────────────────────────────────────────────────────────

_BASE_WAREHOUSES = [
    ("Main Storage",       "All Warehouses", "Stores"),
    ("Returned Inventory", "All Warehouses", "Stores"),
    ("Damaged Inventory",  "All Warehouses", "Stores"),
    ("Fulfillment Area",   "All Warehouses", "Transit"),
]


def _create_warehouses(company, abbr):
    _ensure_custom_field()
    created = []
    for name, parent_base, wtype in _BASE_WAREHOUSES:
        full_name   = f"{name} - {abbr}"
        parent_name = f"{parent_base} - {abbr}"
        if not frappe.db.exists("Warehouse", full_name):
            doc = frappe.new_doc("Warehouse")
            doc.warehouse_name   = name
            doc.parent_warehouse = parent_name
            doc.warehouse_type   = wtype
            doc.company          = company
            doc.insert(ignore_permissions=True)
            _set_vortex_flag(full_name)
            created.append(f"Created Warehouse: {full_name}")
        else:
            _set_vortex_flag(full_name)
            created.append(f"Warehouse exists: {full_name}")
    return created


# ── Per-streamer warehouse creation ──────────────────────────────────────────

def create_streamer_warehouse(streamer_name: str, company: str = None, abbr: str = None):
    """
    Create a personal inventory warehouse for a streamer and flag it as Vortex-managed.
    Called from the Streamer DocType "Create Warehouse" button.
    Returns the warehouse name.
    """
    _ensure_custom_field()
    if not company:
        company = frappe.defaults.get_global_default("company")
    if not abbr:
        abbr = frappe.db.get_value("Company", company, "abbr") or "VB"

    warehouse_label = f"{streamer_name} Inventory"
    full_name       = f"{warehouse_label} - {abbr}"
    parent_name     = f"All Warehouses - {abbr}"

    if frappe.db.exists("Warehouse", full_name):
        _set_vortex_flag(full_name)
        frappe.msgprint(f"Warehouse already exists: {full_name}", indicator="blue")
        return full_name

    doc = frappe.new_doc("Warehouse")
    doc.warehouse_name   = warehouse_label
    doc.parent_warehouse = parent_name
    doc.warehouse_type   = "Stores"
    doc.company          = company
    doc.insert(ignore_permissions=True)
    _set_vortex_flag(full_name)
    frappe.db.commit()

    frappe.msgprint(f"Warehouse created: {full_name}", indicator="green")
    return full_name


@frappe.whitelist()
def create_inventory_location(location_name, warehouse_type="Stores",
                              company=None, abbr=None):
    """
    Create a standalone inventory location (not tied to any streamer).
    Use for: 'Back Room', 'Storage Unit A', 'Show Inventory', etc.
    Returns the full warehouse name (e.g. 'Back Room - VB').
    """
    _ensure_custom_field()
    if not company:
        company = frappe.defaults.get_global_default("company")
    if not abbr:
        abbr = frappe.db.get_value("Company", company, "abbr") or "VB"

    full_name   = f"{location_name} - {abbr}"
    parent_name = f"All Warehouses - {abbr}"

    if frappe.db.exists("Warehouse", full_name):
        _set_vortex_flag(full_name)
        frappe.msgprint(f"Location already exists: {full_name}", indicator="blue")
        return full_name

    doc = frappe.new_doc("Warehouse")
    doc.warehouse_name   = location_name
    doc.parent_warehouse = parent_name
    doc.warehouse_type   = warehouse_type
    doc.company          = company
    doc.insert(ignore_permissions=True)
    _set_vortex_flag(full_name)
    frappe.db.commit()

    frappe.msgprint(f"Location created: {full_name}", indicator="green")
    return full_name


# ── Inventory item quick-create ───────────────────────────────────────────────

@frappe.whitelist()
def create_inventory_item(item_name, item_group="Break Products", uom="Nos",
                          reorder_level=0, description=""):
    """
    Quick-create a stock item for use in Vortex inventory.
    Item code equals item name (trimmed). Returns item_code.
    If the item already exists, returns the existing code without error.
    """
    item_code = item_name.strip()
    if frappe.db.exists("Item", item_code):
        frappe.msgprint(f"Item already exists: {item_code}", indicator="blue")
        return item_code

    item = frappe.new_doc("Item")
    item.item_code     = item_code
    item.item_name     = item_name.strip()
    item.item_group    = item_group or "Break Products"
    item.stock_uom     = uom or "Nos"
    item.is_stock_item = 1
    item.reorder_level = float(reorder_level or 0)
    item.description   = description or item_name.strip()
    item.insert(ignore_permissions=True)
    frappe.db.commit()
    return item.item_code


# ── Stock query helpers ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_bin_qty(warehouse, item_code):
    """Return actual_qty and reserved_qty for a warehouse + item combination."""
    result = frappe.db.get_value(
        "Bin",
        {"warehouse": warehouse, "item_code": item_code},
        ["actual_qty", "reserved_qty"],
        as_dict=True,
    )
    if result:
        return {
            "actual_qty":   float(result.actual_qty   or 0),
            "reserved_qty": float(result.reserved_qty or 0),
        }
    return {"actual_qty": 0.0, "reserved_qty": 0.0}


# ── Full inventory overview ───────────────────────────────────────────────────

@frappe.whitelist()
def list_inventory_locations():
    """
    Return all active Vortex-managed warehouses with current stock summary.
    Filters to is_vortex_managed = 1 so ERPNext system warehouses are excluded.
    Falls back to showing all company warehouses if setup has not been run yet.
    """
    company = frappe.defaults.get_global_default("company")
    if not company:
        return []

    streamer_wh_map = {
        s.warehouse: s.streamer_name
        for s in frappe.get_all("Streamer", fields=["streamer_name", "warehouse"])
        if s.warehouse
    }

    has_flag      = frappe.db.exists("Custom Field", "Warehouse-is_vortex_managed")
    vortex_clause = "AND w.is_vortex_managed = 1" if has_flag else ""

    locations = frappe.db.sql(
        f"""
        SELECT
            w.name                                                  AS warehouse,
            w.warehouse_type                                        AS wh_type,
            COALESCE(SUM(b.actual_qty), 0)                         AS total_qty,
            COALESCE(SUM(b.actual_qty * i.valuation_rate), 0)      AS total_value,
            COUNT(DISTINCT CASE WHEN b.actual_qty > 0
                                THEN b.item_code END)              AS sku_count,
            COUNT(DISTINCT CASE
                WHEN b.actual_qty > 0
                 AND i.reorder_level > 0
                 AND b.actual_qty <= i.reorder_level
                THEN b.item_code END)                              AS low_stock_count
        FROM `tabWarehouse` w
        LEFT JOIN `tabBin`  b ON b.warehouse = w.name
        LEFT JOIN `tabItem` i ON i.item_code = b.item_code
                              AND i.disabled = 0
        WHERE w.company  = %s
          AND w.is_group = 0
          AND w.disabled = 0
          {vortex_clause}
        GROUP BY w.name
        ORDER BY w.name
        """,
        company,
        as_dict=True,
    )

    for loc in locations:
        loc["label"] = streamer_wh_map.get(loc["warehouse"], loc["warehouse"])

    return locations


# ── UI entry point ────────────────────────────────────────────────────────────

@frappe.whitelist()
def setup_from_ui():
    """Called from the Vortex Ops workspace setup button."""
    return run()


# ── Stock operations ──────────────────────────────────────────────────────────

@frappe.whitelist()
def adjust_stock(warehouse, item_code, qty, adjustment_type="receipt", reason=""):
    """
    Adjust stock up (receipt) or down (issue) with a mandatory reason.
    adjustment_type: 'receipt' = add qty | 'issue' = remove qty
    Always creates a real Stock Entry so the audit trail is preserved.
    """
    company   = frappe.defaults.get_global_default("company")
    entry_map = {"receipt": "Material Receipt", "issue": "Material Issue"}
    se_type   = entry_map.get(adjustment_type, "Material Receipt")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = se_type
    se.company          = company
    se.remarks          = f"Manual adjustment — {reason}"

    item_row = {
        "item_code":  item_code,
        "qty":        abs(float(qty)),
        "basic_rate": 0,
    }
    if se_type == "Material Receipt":
        item_row["t_warehouse"] = warehouse
    else:
        item_row["s_warehouse"] = warehouse

    se.append("items", item_row)
    se.insert(ignore_permissions=True)
    se.submit()
    frappe.db.commit()
    return se.name


@frappe.whitelist()
def transfer_stock(from_warehouse, to_warehouse, item_code, qty, remarks=""):
    """
    Material Transfer between warehouses.
    Typical use: split a bulk shipment or transfer between streamers.
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
    Called from the Streamer form 'Add Stock' dialog and the Inventory page.
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
