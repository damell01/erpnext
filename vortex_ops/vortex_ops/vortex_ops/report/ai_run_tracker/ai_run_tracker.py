import frappe


def execute(filters=None):
    f    = filters or {}
    cond = ["1=1"]
    vals = []

    if f.get("automation_type"):
        cond.append("automation_type = %s")
        vals.append(f["automation_type"])
    if f.get("status"):
        cond.append("status = %s")
        vals.append(f["status"])
    if f.get("from_date"):
        cond.append("DATE(run_at) >= %s")
        vals.append(f["from_date"])

    data = frappe.db.sql(
        f"""
        SELECT
            automation_type         "Type",
            related_doctype         "DocType",
            related_name            "Doc",
            status                  "Status",
            run_at                  "Run At",
            run_by                  "Run By",
            LEFT(output_summary, 100) "Output",
            LEFT(error_message, 80)   "Error"
        FROM `tabAutomation Log`
        WHERE {" AND ".join(cond)}
        ORDER BY run_at DESC
        LIMIT 500
        """,
        vals,
        as_dict=True,
    )

    columns = [
        {"label": "Type",    "fieldtype": "Data",     "width": 170},
        {"label": "DocType", "fieldtype": "Data",     "width": 130},
        {"label": "Doc",     "fieldtype": "Data",     "width": 150},
        {"label": "Status",  "fieldtype": "Data",     "width": 90},
        {"label": "Run At",  "fieldtype": "Datetime", "width": 160},
        {"label": "Run By",  "fieldtype": "Data",     "width": 140},
        {"label": "Output",  "fieldtype": "Data",     "width": 260},
        {"label": "Error",   "fieldtype": "Data",     "width": 200},
    ]
    return columns, data
