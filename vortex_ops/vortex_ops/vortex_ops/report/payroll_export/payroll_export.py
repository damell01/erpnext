import frappe
from vortex_ops.utils import safe_float


def execute(filters=None):
    f = filters or {}
    period = f.get("payout_period")
    if not period:
        return _columns(), []

    if f.get("include_draft"):
        docstatus_filter = ["!=", 2]   # submitted + draft, exclude cancelled
    else:
        docstatus_filter = ["=", 1]    # submitted only

    payouts = frappe.get_all(
        "Streamer Payout",
        filters={
            "payout_period": period,
            "docstatus":     docstatus_filter,
        },
        fields=[
            "name", "streamer", "adp_employee_id", "status", "docstatus",
            "payout_type", "gross_sales",
            "profit_share_pct", "profit_share_amount",
            "package_count", "package_rate", "package_payout",
            "tips", "adjustments",
            "owner_platform_fee_pct", "owner_platform_fee_amount",
            "loan_deductions", "total_payout",
        ],
        order_by="streamer asc",
    )

    # Pull legal names from Streamer records
    legal_names = {
        s.name: s.legal_name or ""
        for s in frappe.get_all("Streamer", fields=["name", "legal_name"])
    }

    data       = []
    total_net  = 0

    for p in payouts:
        status_label = p.status or ("Draft" if p.docstatus == 0 else "Submitted")
        row = {
            "streamer":                 p.streamer,
            "legal_name":               legal_names.get(p.streamer, ""),
            "adp_employee_id":          p.adp_employee_id or "",
            "payout_type":              p.payout_type or "",
            "gross_sales":              safe_float(p.gross_sales),
            "profit_share_pct":         safe_float(p.profit_share_pct),
            "profit_share_amount":      safe_float(p.profit_share_amount),
            "package_count":            p.package_count or 0,
            "package_rate":             safe_float(p.package_rate),
            "package_payout":           safe_float(p.package_payout),
            "tips":                     safe_float(p.tips),
            "adjustments":              safe_float(p.adjustments),
            "owner_platform_fee_pct":   safe_float(p.owner_platform_fee_pct),
            "owner_platform_fee_amount":safe_float(p.owner_platform_fee_amount),
            "loan_deductions":          safe_float(p.loan_deductions),
            "total_payout":             safe_float(p.total_payout),
            "status":                   status_label,
            "payout_name":              p.name,
        }
        total_net += safe_float(p.total_payout)
        data.append(row)

    if data:
        data.append({
            "streamer":    "TOTAL",
            "total_payout": round(total_net, 2),
            "_is_total":   True,
        })

    return _columns(), data


def _columns():
    return [
        {"label": "Streamer",        "fieldname": "streamer",                "fieldtype": "Link",     "options": "Streamer",       "width": 140},
        {"label": "Legal Name",      "fieldname": "legal_name",              "fieldtype": "Data",                                  "width": 140},
        {"label": "ADP ID",          "fieldname": "adp_employee_id",         "fieldtype": "Data",                                  "width": 80},
        {"label": "Type",            "fieldname": "payout_type",             "fieldtype": "Data",                                  "width": 100},
        {"label": "Gross Sales",     "fieldname": "gross_sales",             "fieldtype": "Currency",                              "width": 110},
        {"label": "Share %",         "fieldname": "profit_share_pct",        "fieldtype": "Percent",                               "width": 70},
        {"label": "Share $",         "fieldname": "profit_share_amount",     "fieldtype": "Currency",                              "width": 90},
        {"label": "Pkgs",            "fieldname": "package_count",           "fieldtype": "Int",                                   "width": 55},
        {"label": "Pkg Rate",        "fieldname": "package_rate",            "fieldtype": "Currency",                              "width": 80},
        {"label": "Pkg Pay",         "fieldname": "package_payout",          "fieldtype": "Currency",                              "width": 80},
        {"label": "Tips",            "fieldname": "tips",                    "fieldtype": "Currency",                              "width": 80},
        {"label": "Adj",             "fieldname": "adjustments",             "fieldtype": "Currency",                              "width": 80},
        {"label": "Fee %",           "fieldname": "owner_platform_fee_pct",  "fieldtype": "Percent",                               "width": 60},
        {"label": "Fee $",           "fieldname": "owner_platform_fee_amount","fieldtype": "Currency",                             "width": 80},
        {"label": "Loan Ded.",       "fieldname": "loan_deductions",         "fieldtype": "Currency",                              "width": 80},
        {"label": "Net Payout",      "fieldname": "total_payout",            "fieldtype": "Currency",                              "width": 110},
        {"label": "Status",          "fieldname": "status",                  "fieldtype": "Data",                                  "width": 90},
        {"label": "Payout Doc",      "fieldname": "payout_name",             "fieldtype": "Link",     "options": "Streamer Payout","width": 130},
    ]
