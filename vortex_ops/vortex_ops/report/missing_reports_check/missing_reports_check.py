import frappe
from frappe.utils import add_days, today


def execute(filters=None):
    f      = filters or {}
    cutoff = f.get("as_of_date") or add_days(today(), -1)

    streams = frappe.get_all(
        "Stream Event",
        filters={
            "stream_status": ["in", ["Completed", "Finalized"]],
            "stream_date":   ["<=", cutoff],
            "docstatus":     1,
        },
        fields=["name", "stream_title", "stream_date", "primary_streamer", "channel"],
    )

    data = []
    for s in streams:
        seller  = frappe.db.exists("Seller Report",
                    {"stream_event": s.name, "docstatus": 1})
        fulfill = frappe.db.exists("Fulfillment Report",
                    {"stream_event": s.name, "docstatus": 1})
        upload  = frappe.db.exists("Sales Upload",
                    {"stream_event": s.name, "upload_status": "Processed"})

        if not seller or not fulfill:
            data.append({
                "Stream":      s.stream_title,
                "Date":        s.stream_date,
                "Channel":     s.channel,
                "Streamer":    s.primary_streamer,
                "Seller Rpt":  "OK" if seller  else "MISSING",
                "Fulfil Rpt":  "OK" if fulfill else "MISSING",
                "Upload":      "Processed" if upload else "Pending",
            })

    columns = [
        {"label": "Stream",     "fieldtype": "Data", "width": 220},
        {"label": "Date",       "fieldtype": "Date", "width": 100},
        {"label": "Channel",    "fieldtype": "Link", "width": 140,
         "options": "Whatnot Channel"},
        {"label": "Streamer",   "fieldtype": "Link", "width": 130,
         "options": "Streamer"},
        {"label": "Seller Rpt", "fieldtype": "Data", "width": 100},
        {"label": "Fulfil Rpt", "fieldtype": "Data", "width": 100},
        {"label": "Upload",     "fieldtype": "Data", "width": 100},
    ]
    return columns, data
