import frappe


def execute(filters=None):
    f    = filters or {}
    cond = ["se.docstatus = 1"]
    vals = []

    if f.get("from_date"):
        cond.append("se.stream_date >= %s")
        vals.append(f["from_date"])
    if f.get("to_date"):
        cond.append("se.stream_date <= %s")
        vals.append(f["to_date"])
    if f.get("channel"):
        cond.append("se.channel = %s")
        vals.append(f["channel"])
    if f.get("streamer"):
        cond.append(
            "(se.primary_streamer = %s OR EXISTS ("
            "SELECT 1 FROM `tabStream Streamer` ss "
            "WHERE ss.parent = se.name AND ss.streamer = %s))"
        )
        vals.extend([f["streamer"], f["streamer"]])

    where = " AND ".join(cond)

    data = frappe.db.sql(
        f"""
        SELECT
            se.stream_date                                              "Date",
            se.stream_title                                             "Stream",
            se.channel                                                  "Channel",
            se.primary_streamer                                         "Streamer",
            se.gross_sales                                              "Gross",
            se.platform_fees                                            "Fees",
            se.net_earned                                               "Net Earned",
            se.cogs                                                     "COGS",
            se.gross_profit                                             "Gross Profit",
            se.total_packages                                           "Packages",
            se.tips                                                     "Tips",
            CASE WHEN se.gross_sales > 0
                 THEN ROUND(se.gross_profit / se.gross_sales * 100, 1)
                 ELSE 0 END                                             "Margin %",
            se.stream_status                                            "Status"
        FROM `tabStream Event` se
        WHERE {where}
        ORDER BY se.stream_date DESC
        """,
        vals,
        as_dict=True,
    )

    columns = [
        {"label": "Date",         "fieldtype": "Date",     "width": 100},
        {"label": "Stream",       "fieldtype": "Data",     "width": 220},
        {"label": "Channel",      "fieldtype": "Link",     "width": 140,
         "options": "Whatnot Channel"},
        {"label": "Streamer",     "fieldtype": "Link",     "width": 130,
         "options": "Streamer"},
        {"label": "Gross",        "fieldtype": "Currency", "width": 110},
        {"label": "Fees",         "fieldtype": "Currency", "width": 90},
        {"label": "Net Earned",   "fieldtype": "Currency", "width": 110},
        {"label": "COGS",         "fieldtype": "Currency", "width": 100},
        {"label": "Gross Profit", "fieldtype": "Currency", "width": 110},
        {"label": "Packages",     "fieldtype": "Int",      "width": 90},
        {"label": "Tips",         "fieldtype": "Currency", "width": 90},
        {"label": "Margin %",     "fieldtype": "Percent",  "width": 90},
        {"label": "Status",       "fieldtype": "Data",     "width": 100},
    ]
    return columns, data
