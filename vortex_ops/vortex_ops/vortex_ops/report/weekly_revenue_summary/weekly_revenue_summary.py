import frappe


def execute(filters=None):
    f     = filters or {}
    weeks = int(f.get("weeks") or 12)

    data = frappe.db.sql(
        """
        SELECT
            MIN(stream_date)                    "Week Start",
            COUNT(*)                            "Streams",
            SUM(gross_sales)                    "Gross",
            SUM(net_earned)                     "Net Earned",
            SUM(cogs)                           "COGS",
            SUM(gross_profit)                   "Profit",
            SUM(total_packages)                 "Packages",
            SUM(tips)                           "Tips",
            ROUND(AVG(net_earned), 2)           "Avg Net/Stream"
        FROM `tabStream Event`
        WHERE docstatus = 1
          AND stream_date >= DATE_SUB(CURDATE(), INTERVAL %s WEEK)
        GROUP BY YEARWEEK(stream_date, 1)
        ORDER BY YEARWEEK(stream_date, 1) DESC
        """,
        weeks,
        as_dict=True,
    )

    columns = [
        {"label": "Week Start",     "fieldtype": "Date",     "width": 110},
        {"label": "Streams",        "fieldtype": "Int",      "width": 80},
        {"label": "Gross",          "fieldtype": "Currency", "width": 110},
        {"label": "Net Earned",     "fieldtype": "Currency", "width": 110},
        {"label": "COGS",           "fieldtype": "Currency", "width": 100},
        {"label": "Profit",         "fieldtype": "Currency", "width": 110},
        {"label": "Packages",       "fieldtype": "Int",      "width": 90},
        {"label": "Tips",           "fieldtype": "Currency", "width": 90},
        {"label": "Avg Net/Stream", "fieldtype": "Currency", "width": 120},
    ]
    return columns, data
