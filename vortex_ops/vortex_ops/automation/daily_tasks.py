import frappe
from frappe.utils import now
from vortex_ops.utils import log_automation, send_vortex_notification


def run_daily():
    """Daily housekeeping: flag stale pending uploads and send digest."""
    stale = frappe.get_all(
        "Sales Upload",
        filters={"upload_status": "Pending", "docstatus": 0},
        fields=["name", "stream_event", "upload_date"],
    )
    if stale:
        lines = "\n".join(
            f"  {s.name} — Stream: {s.stream_event} — Uploaded: {s.upload_date}"
            for s in stale
        )
        send_vortex_notification(
            subject=f"{len(stale)} Sales Upload(s) Still Pending Review",
            message=(
                f"<h3>Pending Sales Uploads</h3>"
                f"<p>The following uploads have not been reviewed yet:</p>"
                f"<pre>{lines}</pre>"
                "<p>Log in to Vortex Ops to review and approve.</p>"
            ),
        )
    log_automation(
        "Daily Tasks", "System", "daily", "Success",
        output_text=f"Stale uploads flagged: {len(stale)}",
    )


def check_pending_uploads():
    """Hourly check — notify ops if a new upload has been sitting > 2 hours."""
    results = frappe.db.sql(
        """
        SELECT name, stream_event, upload_date
        FROM `tabSales Upload`
        WHERE upload_status = 'Pending'
          AND docstatus = 0
          AND TIMESTAMPDIFF(HOUR, modified, NOW()) >= 2
        """,
        as_dict=True,
    )
    if results:
        log_automation(
            "Pending Upload Check", "Sales Upload", "hourly", "Success",
            output_text=f"{len(results)} uploads awaiting review > 2h",
        )
