import frappe
from vortex_ops.utils import safe_float


def execute(filters=None):
    f    = filters or {}
    cond = ["rec.docstatus = 1"]
    vals = []

    if f.get("streamer"):
        cond.append("rec.streamer = %s")
        vals.append(f["streamer"])
    if f.get("status"):
        cond.append("rec.status = %s")
        vals.append(f["status"])

    rows = frappe.db.sql(
        f"""
        SELECT
            rec.name          AS loan_id,
            rec.streamer      AS streamer,
            rec.loan_date     AS loan_date,
            rec.loan_amount   AS loan_amount,
            rec.amount_repaid AS amount_repaid,
            rec.balance       AS balance,
            rec.status        AS status,
            rec.notes         AS notes
        FROM `tabLoan Record` rec
        WHERE {" AND ".join(cond)}
        ORDER BY rec.streamer, rec.loan_date
        """,
        vals,
        as_dict=True,
    )

    data        = list(rows)
    grand_total = round(sum(safe_float(r.get("balance")) for r in data), 2)

    if data:
        data.append({
            "streamer":  "TOTAL OUTSTANDING",
            "balance":   grand_total,
            "_is_total": True,
        })

    return _columns(), data


def _columns():
    return [
        {"label": "Loan ID",     "fieldname": "loan_id",       "fieldtype": "Link",
         "options": "Loan Record", "width": 160},
        {"label": "Streamer",    "fieldname": "streamer",      "fieldtype": "Link",
         "options": "Streamer",    "width": 140},
        {"label": "Loan Date",   "fieldname": "loan_date",     "fieldtype": "Date",     "width": 100},
        {"label": "Loan Amount", "fieldname": "loan_amount",   "fieldtype": "Currency", "width": 120},
        {"label": "Repaid",      "fieldname": "amount_repaid", "fieldtype": "Currency", "width": 110},
        {"label": "Balance",     "fieldname": "balance",       "fieldtype": "Currency", "width": 110},
        {"label": "Status",      "fieldname": "status",        "fieldtype": "Data",     "width": 100},
        {"label": "Notes",       "fieldname": "notes",         "fieldtype": "Data",     "width": 200},
    ]
