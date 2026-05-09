import frappe


def execute(filters=None):
    f    = filters or {}
    cond = ["1=1"]
    vals = []

    if f.get("upload_status"):
        cond.append("su.upload_status = %s")
        vals.append(f["upload_status"])
    if f.get("from_date"):
        cond.append("su.upload_date >= %s")
        vals.append(f["from_date"])
    if f.get("to_date"):
        cond.append("su.upload_date <= %s")
        vals.append(f["to_date"])

    data = frappe.db.sql(
        f"""
        SELECT
            su.name                "Upload ID",
            su.stream_event        "Stream",
            su.upload_date         "Date",
            su.upload_status       "Status",
            su.total_lines         "Total Lines",
            su.matched_lines       "Matched",
            su.unmatched_lines     "Unmatched",
            su.inventory_processed "Inv Done",
            su.stock_entry_ref     "Stock Entry",
            su.reviewed_by         "Reviewed By"
        FROM `tabSales Upload` su
        WHERE {" AND ".join(cond)}
        ORDER BY su.upload_date DESC
        """,
        vals,
        as_dict=True,
    )

    columns = [
        {"label": "Upload ID",   "fieldtype": "Link",  "width": 160,
         "options": "Sales Upload"},
        {"label": "Stream",      "fieldtype": "Link",  "width": 160,
         "options": "Stream Event"},
        {"label": "Date",        "fieldtype": "Date",  "width": 100},
        {"label": "Status",      "fieldtype": "Data",  "width": 120},
        {"label": "Total Lines", "fieldtype": "Int",   "width": 90},
        {"label": "Matched",     "fieldtype": "Int",   "width": 80},
        {"label": "Unmatched",   "fieldtype": "Int",   "width": 90},
        {"label": "Inv Done",    "fieldtype": "Check", "width": 80},
        {"label": "Stock Entry", "fieldtype": "Data",  "width": 150},
        {"label": "Reviewed By", "fieldtype": "Data",  "width": 150},
    ]
    return columns, data
