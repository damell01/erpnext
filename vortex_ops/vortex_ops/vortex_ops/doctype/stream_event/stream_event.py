import frappe
from frappe.model.document import Document
from frappe.utils import nowdate
from vortex_ops.utils import safe_float, send_vortex_notification


def validate_doc(doc, method=None):
    if not doc.stream_date:
        doc.stream_date = nowdate()
    if not doc.stream_status:
        doc.stream_status = "Draft"
    if doc.stream_date > nowdate():
        frappe.throw("Stream date cannot be in the future")
    gross = safe_float(doc.gross_sales)
    fees  = safe_float(doc.platform_fees)
    cogs  = safe_float(doc.cogs)
    doc.net_earned   = round(gross - fees, 2)
    doc.gross_profit = round(doc.net_earned - cogs, 2)


def on_submit(doc, method=None):
    doc.db_set("stream_status", "Completed")

    # Build streamer list for notification (show may have multiple)
    streamers = [doc.primary_streamer] + [
        r.streamer for r in (doc.additional_streamers or []) if r.streamer
    ]
    streamer_str = ", ".join(streamers)

    send_vortex_notification(
        subject=f"Stream Completed: {doc.stream_title}",
        message=(
            f"<h3>{doc.stream_title}</h3>"
            f"<p>Date: {doc.stream_date}<br>"
            f"Streamer(s): {streamer_str}<br>"
            f"Net Earned: ${safe_float(doc.net_earned):,.2f}<br>"
            f"Packages: {doc.total_packages or 0}</p>"
            "<p>Please submit seller and fulfillment reports, then upload the sales recap.</p>"
        ),
    )
    try:
        from vortex_ops.ai.stream_summary import generate
        generate(doc.name)
    except Exception as e:
        frappe.log_error(f"AI summary failed for {doc.name}: {e}")


def on_cancel(doc, method=None):
    doc.db_set("stream_status", "Cancelled")


class StreamEvent(Document):
    def update_cogs(self, amount):
        self.db_set("cogs", amount)
        self.db_set(
            "gross_profit",
            round(safe_float(self.net_earned) - amount, 2),
        )
