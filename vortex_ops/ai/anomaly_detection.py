import frappe
import json
from vortex_ops.utils import ollama_json, log_automation
from vortex_ops.ai.business_context import get_context


@frappe.whitelist()
def run_anomaly_check(payout_period_name: str):
    payouts = frappe.get_all(
        "Streamer Payout",
        filters={"payout_period": payout_period_name, "docstatus": ["!=", 2]},
        fields=[
            "name", "streamer", "gross_sales", "total_payout",
            "profit_share_amount", "package_payout",
            "tips", "loan_deductions", "adjustments", "payout_type",
        ],
    )

    # Historical averages — last 12 weeks
    history = frappe.db.sql(
        """
        SELECT
            p.streamer,
            AVG(p.total_payout)  avg_payout,
            MAX(p.total_payout)  max_payout,
            MIN(p.total_payout)  min_payout,
            COUNT(*)             periods
        FROM `tabStreamer Payout` p
        JOIN `tabPayout Period` pp ON pp.name = p.payout_period
        WHERE p.docstatus = 1
          AND pp.end_date >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)
        GROUP BY p.streamer
        """,
        as_dict=True,
    )

    system = (
        get_context()
        + "\n\nYOUR TASK: Review payout records for anomalies before they are sent to payroll.\n"
        "Remember:\n"
        "- Streamers have different payout types (profit share, per package, flat rate, etc.).\n"
        "- Tips, loan deductions, and owner platform fees affect totals.\n"
        "- A show may involve multiple streamers splitting sales — so individual gross_sales\n"
        "  per streamer may be lower than the total show gross.\n"
        "- Flag amounts 50%+ above or below the streamer's historical average.\n"
        "- Flag any payout where required components are missing (e.g. profit share is 0\n"
        "  but payout type is Profit Share).\n"
        "- Flag obvious calculation errors.\n"
        "- Do NOT flag first-time streamers with no history as anomalies — note them instead."
    )

    prompt = (
        f"Check these payouts for anomalies.\n\n"
        f"CURRENT PERIOD PAYOUTS:\n{json.dumps([dict(p) for p in payouts], default=str)}\n\n"
        f"HISTORICAL AVERAGES (last 12 weeks):\n{json.dumps([dict(h) for h in history], default=str)}\n\n"
        "Return a JSON array — one object per payout — with fields:\n"
        "name, streamer, flag (bool), severity (high/medium/low), reason (string)"
    )

    try:
        results = ollama_json(prompt, system=system)
        flagged = [r for r in results if r.get("flag")]
        log_automation(
            "Anomaly Detection", "Payout Period", payout_period_name,
            "Success" if not flagged else "Partial",
            output_text=f"Flagged {len(flagged)}/{len(payouts)}",
        )
        if flagged:
            names = ", ".join(f["streamer"] for f in flagged)
            frappe.msgprint(
                f"{len(flagged)} payout(s) flagged: {names}. "
                "Review before ADP export.",
                indicator="orange",
            )
        return results
    except Exception as e:
        log_automation(
            "Anomaly Detection", "Payout Period", payout_period_name, "Failed", error=str(e)
        )
        frappe.throw(f"Anomaly check failed: {e}")
