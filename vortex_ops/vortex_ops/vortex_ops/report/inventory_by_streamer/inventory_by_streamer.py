import frappe


def execute(filters=None):
    f = filters or {}
    company = frappe.defaults.get_global_default("company")

    # Build a map of warehouse -> display label.
    # Streamer-linked warehouses show the streamer name.
    # All other warehouses show the warehouse name itself.
    streamer_wh_map = {}
    for s in frappe.get_all(
        "Streamer",
        filters={"status": ["!=", ""]},
        fields=["streamer_name", "warehouse"],
    ):
        if s.warehouse:
            streamer_wh_map[s.warehouse] = s.streamer_name

    # Build WHERE clause
    cond = [
        "b.actual_qty > 0",
        "i.disabled = 0",
        "i.is_stock_item = 1",
        "w.company = %s",
    ]
    vals = [company]

    if f.get("warehouse"):
        cond.append("b.warehouse = %s")
        vals.append(f["warehouse"])
    elif f.get("streamer"):
        wh = frappe.db.get_value("Streamer", f["streamer"], "warehouse")
        if not wh:
            return [], []
        cond.append("b.warehouse = %s")
        vals.append(wh)

    if f.get("item_group"):
        cond.append("i.item_group = %s")
        vals.append(f["item_group"])

    where = " AND ".join(cond)

    data = frappe.db.sql(
        f"""
        SELECT
            b.warehouse                                         AS warehouse,
            i.item_code                                         AS item_code,
            i.item_name                                         AS item_name,
            i.item_group                                        AS item_group,
            b.actual_qty                                        AS on_hand,
            GREATEST(b.actual_qty - b.reserved_qty, 0)         AS available,
            i.valuation_rate                                    AS unit_cost,
            b.actual_qty * i.valuation_rate                     AS total_value,
            i.reorder_level                                     AS reorder_at,
            CASE WHEN b.actual_qty <= i.reorder_level
                 AND i.reorder_level > 0
                 THEN 'LOW STOCK' ELSE '' END                   AS alert
        FROM `tabBin` b
        JOIN `tabItem` i     ON i.item_code     = b.item_code
        JOIN `tabWarehouse` w ON w.name         = b.warehouse
        WHERE {where}
        ORDER BY b.warehouse, i.item_name
        """,
        vals,
        as_dict=True,
    )

    # Attach display label and total row per location
    current_wh   = None
    output       = []
    grand_value  = 0

    for row in data:
        wh = row["warehouse"]

        # Location section header row when warehouse changes
        if wh != current_wh:
            if current_wh is not None:
                # blank separator
                output.append({})
            current_wh = wh

        location = streamer_wh_map.get(wh, wh)   # person name OR warehouse name
        row["location"] = location
        grand_value += row["total_value"] or 0
        output.append(row)

    # Grand total footer
    if output:
        output.append({
            "location":    "TOTAL",
            "total_value": grand_value,
        })

    columns = [
        {"label": "Location",    "fieldname": "location",    "fieldtype": "Data",     "width": 160},
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
        {"label": "Alert",       "fieldname": "alert",       "fieldtype": "Data",     "width": 90},
    ]
    return columns, output
