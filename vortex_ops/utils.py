import frappe
import json
import logging
import requests as _req
from frappe.utils import now

logger = logging.getLogger(__name__)
_DEFAULT_URL   = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.1:8b"


def _ai_settings():
    """Read AI config from Vortex Settings, fall back to defaults."""
    try:
        doc = frappe.get_cached_doc("Vortex Settings")
        return {
            "enabled": bool(doc.ai_enabled),
            "url":     doc.ollama_url   or _DEFAULT_URL,
            "model":   doc.ollama_model or _DEFAULT_MODEL,
        }
    except Exception:
        return {"enabled": True, "url": _DEFAULT_URL, "model": _DEFAULT_MODEL}


def ollama_chat(prompt, system="", model=None, max_tokens=1500):
    cfg   = _ai_settings()
    if not cfg["enabled"]:
        frappe.throw("AI features are disabled. Enable them in Vortex Settings → AI Settings.")
    model = model or cfg["model"]
    msgs  = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    try:
        r = _req.post(
            f"{cfg['url']}/api/chat",
            json={
                "model": model,
                "messages": msgs,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.1},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except _req.exceptions.ConnectionError:
        frappe.throw(f"Ollama not reachable at {cfg['url']}. Check Vortex Settings → AI Settings or run: sudo systemctl start ollama")
    except _req.exceptions.Timeout:
        frappe.throw("Ollama timed out. Try again in 30 seconds.")
    except Exception as e:
        frappe.throw(f"Ollama error: {e}")


def ollama_json(prompt, system="", model=None):
    sys2 = (system + "\n\n" if system else "") + \
           "Return ONLY valid JSON. No markdown. No explanation."
    for attempt in range(2):
        raw   = ollama_chat(prompt, system=sys2, model=model)
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            if attempt == 0:
                prompt += "\nReturn ONLY a JSON array or object. Nothing else."
            else:
                frappe.throw(f"Ollama returned invalid JSON: {raw[:200]}")


def log_automation(atype, doctype, name, status,
                   input_text="", output_text="", error=""):
    try:
        doc = frappe.new_doc("Automation Log")
        doc.update({
            "automation_type":  atype,
            "related_doctype":  doctype,
            "related_name":     name,
            "status":           status,
            "input_summary":    str(input_text)[:2000],
            "output_summary":   str(output_text)[:2000],
            "error_message":    str(error)[:1000],
            "run_at":           now(),
            "run_by":           frappe.session.user,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        logger.error(f"Automation log failed: {e}")


def safe_float(val, default=0.0):
    try:
        return float(val or default)
    except Exception:
        return default


def send_vortex_notification(subject, message, role="Vortex Operations"):
    users = frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent",
    )
    if users:
        frappe.sendmail(recipients=users, subject=subject, message=message, now=True)


def get_streamer_warehouse(streamer):
    return frappe.db.get_value("Streamer", streamer, "warehouse")


@frappe.whitelist()
def get_streamer_loan_balance(streamer):
    r = frappe.db.sql(
        """
        SELECT COALESCE(SUM(loan_amount - amount_repaid), 0) AS bal
        FROM `tabLoan Record`
        WHERE streamer = %s AND status = 'Active' AND docstatus = 1
        """,
        streamer,
        as_dict=True,
    )
    return safe_float(r[0].bal if r else 0)
