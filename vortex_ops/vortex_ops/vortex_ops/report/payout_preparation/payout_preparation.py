import frappe


def execute(filters=None):
    f      = filters or {}
    period = f.get("payout_period")
    if not period:
        frappe.throw("Select a Payout Period to run this report")

    rows = frappe.db.sql(
        """
        SELECT
            sp.streamer                  "Streamer",
            st.legal_name                "Legal Name",
            st.adp_employee_id           "ADP ID",
            sp.payout_type               "Type",
            sp.gross_sales               "Gross Sales",
            sp.profit_share_pct          "Share %",
            sp.profit_share_amount       "Profit Share",
            sp.package_count             "Packages",
            sp.package_payout            "Pkg Pay",
            sp.tips                      "Tips",
            sp.owner_platform_fee_amount "Platform Fee",
            sp.adjustments               "Adj",
            sp.loan_deductions           "Loan Ded",
            sp.total_payout              "TOTAL",
            sp.status                    "Status"
        FROM `tabStreamer Payout` sp
        JOIN `tabStreamer` st ON st.name = sp.streamer
        WHERE sp.payout_period = %s AND sp.docstatus != 2
        ORDER BY sp.streamer
        """,
        period,
        as_dict=True,
    )

    if rows:
        totals = {
            "Streamer":     "TOTALS",
            "Legal Name":   "",
            "Gross Sales":  sum(r.get("Gross Sales")  or 0 for r in rows),
            "Tips":         sum(r.get("Tips")         or 0 for r in rows),
            "Platform Fee": sum(r.get("Platform Fee") or 0 for r in rows),
            "Loan Ded":     sum(r.get("Loan Ded")     or 0 for r in rows),
            "TOTAL":        sum(r.get("TOTAL")        or 0 for r in rows),
        }
        rows.append(totals)

    columns = [
        {"label": "Streamer",     "fieldtype": "Link",     "width": 130, "options": "Streamer"},
        {"label": "Legal Name",   "fieldtype": "Data",     "width": 160},
        {"label": "ADP ID",       "fieldtype": "Data",     "width": 80},
        {"label": "Type",         "fieldtype": "Data",     "width": 110},
        {"label": "Gross Sales",  "fieldtype": "Currency", "width": 110},
        {"label": "Share %",      "fieldtype": "Percent",  "width": 80},
        {"label": "Profit Share", "fieldtype": "Currency", "width": 110},
        {"label": "Packages",     "fieldtype": "Int",      "width": 80},
        {"label": "Pkg Pay",      "fieldtype": "Currency", "width": 90},
        {"label": "Tips",         "fieldtype": "Currency", "width": 90},
        {"label": "Platform Fee", "fieldtype": "Currency", "width": 110},
        {"label": "Adj",          "fieldtype": "Currency", "width": 90},
        {"label": "Loan Ded",     "fieldtype": "Currency", "width": 100},
        {"label": "TOTAL",        "fieldtype": "Currency", "width": 110},
        {"label": "Status",       "fieldtype": "Data",     "width": 100},
    ]
    return columns, rows
