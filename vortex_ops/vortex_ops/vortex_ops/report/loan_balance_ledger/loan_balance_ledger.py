import frappe


def execute(filters=None):
    f    = filters or {}
    cond = ["lr.docstatus = 1"]
    vals = []

    if f.get("streamer"):
        cond.append("lr.streamer = %s")
        vals.append(f["streamer"])
    if f.get("status"):
        cond.append("lr.status = %s")
        vals.append(f["status"])

    data = frappe.db.sql(
        f"""
        SELECT
            lr.name          "Loan ID",
            lr.streamer      "Streamer",
            lr.loan_date     "Loan Date",
            lr.loan_amount   "Loan Amount",
            lr.amount_repaid "Repaid",
            lr.balance       "Balance",
            lr.status        "Status",
            lr.notes         "Notes"
        FROM `tabLoan Record` lr
        WHERE {" AND ".join(cond)}
        ORDER BY lr.streamer, lr.loan_date
        """,
        vals,
        as_dict=True,
    )

    columns = [
        {"label": "Loan ID",     "fieldtype": "Link",     "width": 160,
         "options": "Loan Record"},
        {"label": "Streamer",    "fieldtype": "Link",     "width": 130,
         "options": "Streamer"},
        {"label": "Loan Date",   "fieldtype": "Date",     "width": 100},
        {"label": "Loan Amount", "fieldtype": "Currency", "width": 120},
        {"label": "Repaid",      "fieldtype": "Currency", "width": 110},
        {"label": "Balance",     "fieldtype": "Currency", "width": 110},
        {"label": "Status",      "fieldtype": "Data",     "width": 100},
        {"label": "Notes",       "fieldtype": "Data",     "width": 200},
    ]
    return columns, data
