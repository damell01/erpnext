import frappe


def execute(filters=None):
    f = filters or {}
    company = frappe.defaults.get_global_default("company")

    streamer_wh_map = {
        s.warehouse: s.streamer_name
        for s in frappe.get_all("Streamer", fields=["streamer_name", "warehouse"])
        if s.warehouse
    }

    has_flag = frappe.db.exists("Custom Field", "Warehouse-is_vortex_managed")

    cond = [
        "i.disabled = 0",
        "i.is_stock_item = 1",
        "w.company = %s",
        "w.is_group = 0",
        "w.disabled = 0",
    ]
    if has_flag:
        cond.append("w.is_vortex_managed = 1")
    vals = [company]

    if not f.get("include_zero_stock"):
        cond.append("b.actual_qty > 0")

    if f.get("warehouse"):
        cond.append("b.warehouse = %s")
        vals.append(f["warehouse"])
    elif f.get("streamer"):
        wh = frappe.db.get_value("Streamer", f["streamer"], "warehouse")
        if not wh:
            return _columns(), []
        cond.append("b.warehouse = %s")
        vals.append(wh)

    if f.get("item_group"):
        cond.append("i.item_group = %s")
        vals.append(f["item_group"])

    where = " AND ".join(cond)

    rows = frappe.db.sql(
        f"""
        SELECT
            b.warehouse                                         AS warehouse,
            i.item_code                                         AS item_code,
            i.item_name                                         AS item_name,
            i.item_group                                        AS item_group,
            COALESCE(b.actual_qty, 0)                          AS on_hand,
            GREATEST(COALESCE(b.actual_qty, 0)
                     - COALESCE(b.reserved_qty, 0), 0)         AS available,
            COALESCE(i.valuation_rate, 0)                      AS unit_cost,
            COALESCE(b.actual_qty, 0)
                * COALESCE(i.valuation_rate, 0)                AS total_value,
            COALESCE(i.reorder_level, 0)                       AS reorder_at,
            CASE WHEN b.actual_qty <= i.reorder_level
                      AND i.reorder_level > 0
                 THEN 'LOW STOCK' ELSE '' END                  AS alert
        FROM `tabBin` b
        JOIN `tabItem`      i ON i.item_code = b.item_code
        JOIN `tabWarehouse` w ON w.name      = b.warehouse
        WHERE {where}
        ORDER BY b.warehouse, i.item_name
        """,
        vals,
        as_dict=True,
    )

    output      = []
    grand_value = 0
    current_wh  = None
    wh_value    = 0
    wh_rows     = 0

    for row in rows:
        wh = row["warehouse"]

        if wh != current_wh:
            # Subtotal for previous location
            if current_wh is not None and wh_rows > 0:
                output.append(_subtotal_row(current_wh, streamer_wh_map, wh_value, wh_rows))
                output.append({})  # blank spacer

            current_wh = wh
            wh_value   = 0
            wh_rows    = 0

        row["location"] = streamer_wh_map.get(wh, wh)
        val = row["total_value"] or 0
        wh_value    += val
        grand_value += val
        wh_rows     += 1
        output.append(row)

    # Final location subtotal
    if current_wh is not None and wh_rows > 0:
        output.append(_subtotal_row(current_wh, streamer_wh_map, wh_value, wh_rows))

    # Grand total
    if output:
        output.append({})
        output.append({
            "location":    "GRAND TOTAL",
            "total_value": grand_value,
            "_is_total":   True,
        })

    return _columns(), output


def _subtotal_row(warehouse, streamer_wh_map, total_value, item_count):
    label = streamer_wh_map.get(warehouse, warehouse)
    return {
        "location":    f"{label} — Subtotal ({item_count} SKU{'s' if item_count != 1 else ''})",
        "warehouse":   warehouse,
        "total_value": total_value,
        "_is_subtotal": True,
    }


def _columns():
    return [
        {"label": "Location",    "fieldname": "location",    "fieldtype": "Data",     "width": 200},
        {"label": "Warehouse",   "fieldname": "warehouse",   "fieldtype": "Link",     "width": 180,
         "options": "Warehouse"},
        {"label": "Item Code",   "fieldname": "item_code",   "fieldtype": "Link",     "width": 150,
         "options": "Item"},
        {"label": "Item Name",   "fieldname": "item_name",   "fieldtype": "Data",     "width": 220},
        {"label": "Category",    "fieldname": "item_group",  "fieldtype": "Data",     "width": 130},
        {"label": "On Hand",     "fieldname": "on_hand",     "fieldtype": "Float",    "width": 90},
        {"label": "Available",   "fieldname": "available",   "fieldtype": "Float",    "width": 90},
        {"label": "Unit Cost",   "fieldname": "unit_cost",   "fieldtype": "Currency", "width": 100},
        {"label": "Total Value", "fieldname": "total_value", "fieldtype": "Currency", "width": 110},
        {"label": "Reorder At",  "fieldname": "reorder_at",  "fieldtype": "Float",    "width": 90},
        {"label": "Alert",       "fieldname": "alert",       "fieldtype": "Data",     "width": 100},
    ]
