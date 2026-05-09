import frappe
from vortex_ops.utils import log_automation, send_vortex_notification


def run_weekly():
    """Weekly summary: open payout periods and outstanding loans."""
    open_periods = frappe.get_all(
        "Payout Period",
        filters={"status": "Open"},
        fields=["name", "period_name", "start_date", "end_date"],
    )

    active_loans = frappe.db.sql(
        """
        SELECT streamer, SUM(balance) total_balance
        FROM `tabLoan Record`
        WHERE status = 'Active' AND docstatus = 1
        GROUP BY streamer
        ORDER BY total_balance DESC
        """,
        as_dict=True,
    )

    period_lines = "\n".join(
        f"  {p.period_name} ({p.start_date} – {p.end_date})" for p in open_periods
    ) or "  None"

    loan_lines = "\n".join(
        f"  {l.streamer}: ${l.total_balance:,.2f}" for l in active_loans
    ) or "  None"

    send_vortex_notification(
        subject="Weekly Vortex Ops Summary",
        message=(
            f"<h3>Weekly Ops Digest</h3>"
            f"<h4>Open Payout Periods</h4><pre>{period_lines}</pre>"
            f"<h4>Active Loan Balances</h4><pre>{loan_lines}</pre>"
        ),
        role="Vortex Accounting",
    )

    log_automation(
        "Weekly Tasks", "System", "weekly", "Success",
        output_text=(
            f"Open periods: {len(open_periods)} | "
            f"Streamers with active loans: {len(active_loans)}"
        ),
    )
