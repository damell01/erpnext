import frappe


def execute(filters=None):
    f = filters or {}

    streamers = frappe.get_all(
        "Streamer",
        filters={"status": "Active"},
        fields=["name", "streamer_name", "warehouse"],
    )

    # Optionally filter to one streamer
    if f.get("streamer"):
        streamers = [s for s in streamers if s.name == f["streamer"]]

    wh_map = {s.warehouse: s.streamer_name for s in streamers if s.warehouse}
    whs    = [s.warehouse for s in streamers if s.warehouse]

    if not whs:
        return [], []

    ph   = ",".join(["%s"] * len(whs))
    data = frappe.db.sql(
        f"""
        SELECT
            b.warehouse                              "Warehouse",
            i.item_code                              "Item Code",
            i.item_name                              "Item Name",
            i.item_group                             "Category",
            b.actual_qty                             "On Hand",
            b.actual_qty - b.reserved_qty            "Available",
            i.valuation_rate                         "Unit Cost",
            b.actual_qty * i.valuation_rate          "Total Value",
            i.reorder_level                          "Reorder At",
            CASE WHEN b.actual_qty <= i.reorder_level
                 THEN 'LOW STOCK' ELSE '' END        "Alert"
        FROM `tabBin` b
        JOIN `tabItem` i ON i.item_code = b.item_code
        WHERE b.warehouse IN ({ph})
          AND b.actual_qty > 0
          AND i.disabled = 0
        ORDER BY b.warehouse, i.item_name
        """,
        whs,
        as_dict=True,
    )

    for row in data:
        row["Streamer"] = wh_map.get(row["Warehouse"], "")

    columns = [
        {"label": "Streamer",    "fieldtype": "Data",     "width": 130},
        {"label": "Item Code",   "fieldtype": "Link",     "width": 160,
         "options": "Item"},
        {"label": "Item Name",   "fieldtype": "Data",     "width": 230},
        {"label": "Category",    "fieldtype": "Data",     "width": 130},
        {"label": "On Hand",     "fieldtype": "Float",    "width": 90},
        {"label": "Available",   "fieldtype": "Float",    "width": 90},
        {"label": "Unit Cost",   "fieldtype": "Currency", "width": 100},
        {"label": "Total Value", "fieldtype": "Currency", "width": 110},
        {"label": "Reorder At",  "fieldtype": "Float",    "width": 90},
        {"label": "Alert",       "fieldtype": "Data",     "width": 100},
    ]
    return columns, data
