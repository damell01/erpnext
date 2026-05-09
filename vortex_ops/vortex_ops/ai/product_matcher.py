import frappe
from vortex_ops.utils import ollama_json, log_automation
from vortex_ops.ai.business_context import get_context


def ai_match_upload(upload_name: str):
    upload    = frappe.get_doc("Sales Upload", upload_name)
    unmatched = [
        l for l in upload.sales_lines
        if not l.item_code or l.match_status == "Unmatched"
    ]
    if not unmatched:
        frappe.msgprint("All lines already matched", indicator="green")
        return

    items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "is_stock_item": 1},
        fields=["item_code", "item_name", "item_group"],
    )
    catalog = "\n".join(
        f"{i.item_code} | {i.item_name} | {i.item_group}" for i in items
    )

    descs    = [l.raw_description for l in unmatched]
    desc_txt = "\n".join(f"{i+1}. {d}" for i, d in enumerate(descs))

    system = (
        get_context()
        + "\n\nYOUR TASK: Match Whatnot recap sales descriptions to ERPNext inventory items.\n"
        "Sales descriptions come from streamer recap sheets and Whatnot exports — they are "
        "often abbreviated, informal, or incomplete. Use sports card industry knowledge to "
        "interpret them. Be lenient: short names, abbreviations, and year-only references are common.\n"
        "A show may have had multiple streamers; the upload may contain items from any "
        "streamer's inventory. Match to item_code only — warehouse assignment is handled separately."
    )

    prompt = (
        f"Match each numbered description to the best catalog item.\n\n"
        f"CATALOG (item_code | item_name | group):\n{catalog}\n\n"
        f"DESCRIPTIONS TO MATCH:\n{desc_txt}\n\n"
        "Return a JSON array with one object per description:\n"
        '[{"index": 1, "item_code": "ITEM-001" or null, '
        '"confidence": "high/medium/low", "reason": "brief explanation"}]'
    )

    try:
        matches = ollama_json(prompt, system=system)
        count   = 0
        for i, line in enumerate(unmatched):
            m = next((x for x in matches if x.get("index") == i + 1), None)
            if m and m.get("item_code"):
                line.item_code     = m["item_code"]
                line.ai_confidence = m.get("confidence", "low")
                line.ai_reason     = str(m.get("reason", ""))[:140]
                line.match_status  = (
                    "Matched" if m["confidence"] == "high" else "AI Suggested"
                )
                count += 1
        upload.save(ignore_permissions=True)
        log_automation(
            "AI Match", "Sales Upload", upload_name, "Success",
            input_text=f"{len(descs)} descriptions vs {len(items)} catalog items",
            output_text=f"Matched {count}/{len(unmatched)}",
        )
        frappe.msgprint(
            f"Ollama matched {count}/{len(unmatched)} lines.",
            indicator="green" if count == len(unmatched) else "orange",
        )
    except Exception as e:
        log_automation("AI Match", "Sales Upload", upload_name, "Failed", error=str(e))
        frappe.throw(f"AI matching failed: {e}")
