import frappe
from vortex_ops.utils import ollama_chat, log_automation, safe_float
from vortex_ops.ai.business_context import get_context_brief


def generate(stream_name: str) -> str:
    stream = frappe.get_doc("Stream Event", stream_name)

    streamers = [stream.primary_streamer] + [
        r.streamer for r in (stream.additional_streamers or []) if r.streamer
    ]

    seller = frappe.get_all(
        "Seller Report",
        filters={"stream_event": stream_name, "docstatus": 1},
        fields=["streamer", "packages_sold", "adjustments", "notes"],
    )
    fulfil = frappe.get_all(
        "Fulfillment Report",
        filters={"stream_event": stream_name, "docstatus": 1},
        fields=["total_packages", "packages_shipped", "issues"],
    )

    system = (
        get_context_brief()
        + "\n\nYOUR TASK: Write a brief operational summary for an internal team record. "
        "Plain, professional language. 2-3 sentences. No markdown, no bullet points. "
        "Focus on what happened operationally — how many streamers, sales performance, "
        "fulfillment status, and any notable issues. Do not speculate."
    )

    streamer_list = ", ".join(streamers) if streamers else "Unknown"
    prompt = (
        f"Stream: {stream.stream_title}\n"
        f"Date: {stream.stream_date} | Channel: {stream.channel}\n"
        f"Streamer(s): {streamer_list}\n"
        f"Gross Sales: ${safe_float(stream.gross_sales):,.2f} | "
        f"Net Earned: ${safe_float(stream.net_earned):,.2f}\n"
        f"Total Packages: {stream.total_packages or 0} | "
        f"Tips: ${safe_float(stream.tips):,.2f}\n"
        f"Seller Reports: {seller}\n"
        f"Fulfillment: {fulfil}\n\n"
        "Write 2-3 sentences summarizing this stream operationally."
    )

    try:
        summary = ollama_chat(prompt, system=system, max_tokens=200)
        stream.db_set("ai_summary", summary)
        log_automation(
            "AI Summary", "Stream Event", stream_name, "Success", output_text=summary
        )
        return summary
    except Exception as e:
        log_automation(
            "AI Summary", "Stream Event", stream_name, "Failed", error=str(e)
        )
        return ""
