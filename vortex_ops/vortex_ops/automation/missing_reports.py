import frappe
from frappe.utils import add_days, today
from vortex_ops.utils import send_vortex_notification, log_automation


def check_missing_reports():
    """Daily check: flag completed streams missing seller or fulfillment reports."""
    cutoff  = add_days(today(), -1)
    streams = frappe.get_all(
        "Stream Event",
        filters={
            "stream_status": "Completed",
            "stream_date":   ["<=", cutoff],
            "docstatus":     1,
        },
        fields=["name", "stream_title", "primary_streamer", "stream_date"],
    )

    missing = []
    for s in streams:
        seller  = frappe.db.exists("Seller Report",  {"stream_event": s.name, "docstatus": 1})
        fulfill = frappe.db.exists("Fulfillment Report", {"stream_event": s.name, "docstatus": 1})
        if not seller or not fulfill:
            missing.append({
                "stream":    s.stream_title,
                "date":      s.stream_date,
                "streamer":  s.primary_streamer,
                "no_seller": not seller,
                "no_fulfil": not fulfill,
            })

    if not missing:
        log_automation("Missing Reports", "System", "daily", "Skipped",
                       output_text="All completed streams have reports")
        return

    rows = "".join(
        "<tr>"
        f"<td>{m['stream']}</td><td>{m['date']}</td><td>{m['streamer']}</td>"
        f"<td style='color:{'red' if m['no_seller'] else 'green'}'>"
        f"{'MISSING' if m['no_seller'] else 'OK'}</td>"
        f"<td style='color:{'red' if m['no_fulfil'] else 'green'}'>"
        f"{'MISSING' if m['no_fulfil'] else 'OK'}</td>"
        "</tr>"
        for m in missing
    )

    send_vortex_notification(
        subject=f"Missing Reports: {len(missing)} stream(s) incomplete",
        message=(
            "<h3>Streams Missing Reports</h3>"
            '<table border="1" cellpadding="4">'
            "<tr><th>Stream</th><th>Date</th><th>Streamer</th>"
            "<th>Seller Rpt</th><th>Fulfil Rpt</th></tr>"
            f"{rows}</table>"
        ),
    )

    log_automation(
        "Missing Reports", "System", "daily", "Success",
        output_text=f"{len(missing)} streams missing reports",
    )
