import frappe
import json
from vortex_ops.utils import ollama_json, log_automation, send_vortex_notification
from vortex_ops.ai.business_context import get_context_brief


def run_predictions():
    inventory = frappe.db.sql(
        """
        SELECT
            i.item_code,
            i.item_name,
            i.item_group,
            COALESCE(SUM(b.actual_qty), 0) qty,
            i.reorder_level,
            i.valuation_rate cost
        FROM `tabItem` i
        LEFT JOIN `tabBin` b ON b.item_code = i.item_code
        WHERE i.is_stock_item = 1 AND i.disabled = 0
        GROUP BY i.item_code
        """,
        as_dict=True,
    )

    velocity = frappe.db.sql(
        """
        SELECT sed.item_code, SUM(sed.qty) sold_30d
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.stock_entry_type = 'Material Issue'
          AND se.docstatus = 1
          AND se.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY sed.item_code
        """,
        as_dict=True,
    )

    vel = {v.item_code: float(v.sold_30d) for v in velocity}
    for item in inventory:
        item["sold_30d"] = vel.get(item["item_code"], 0)
        item["days_left"] = (
            round(float(item["qty"]) / (item["sold_30d"] / 30), 1)
            if item["sold_30d"] > 0
            else 999
        )

    system = (
        get_context_brief()
        + "\n\nYOUR TASK: Analyze inventory levels and flag items that need reordering. "
        "Remember that inventory is tracked per streamer warehouse, so qty here is the "
        "aggregate across all warehouses. Items are sports cards, TCG packs, sealed wax, "
        "memorabilia, and mystery lots. Flag items with under 14 days supply at current "
        "sales velocity OR below their reorder_level threshold."
    )

    prompt = (
        "Flag inventory items that need reordering soon.\n\n"
        f"{json.dumps([dict(i) for i in inventory], default=str)}\n\n"
        "Return a JSON array. Each object needs: "
        "item_code, item_name, qty, days_left, "
        "urgency (critical/soon/watch), recommendation"
    )

    try:
        alerts   = ollama_json(prompt, system=system)
        critical = [a for a in alerts if a.get("urgency") == "critical"]
        if critical:
            lines = "\n".join(
                f"  {a.get('item_name','?')} — "
                f"{a.get('qty', 0)} left ({a.get('days_left','?')}d supply)"
                for a in critical
            )
            send_vortex_notification(
                "URGENT: Low Stock Alert",
                f"<h3>Critical Stock Levels</h3><pre>{lines}</pre>",
                role="Vortex Admin",
            )
        log_automation(
            "Low Stock", "Item", "all", "Success",
            output_text=f"{len(alerts)} flagged, {len(critical)} critical",
        )
    except Exception as e:
        log_automation("Low Stock", "Item", "all", "Failed", error=str(e))
