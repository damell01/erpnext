"""
Whatnot Show Recap Scraper
==========================
Uses Playwright to navigate to a Whatnot show recap page and Ollama AI to
extract the show summary and item sales — no fragile CSS selectors required.

Two-phase approach:
  1. Playwright logs in and captures the full page text after rendering.
  2. Ollama parses that raw text into structured JSON (totals + item list).
     If Ollama is unavailable, falls back to regex-based extraction.

Setup (run once on the server):
    pip install playwright
    playwright install chromium

Credentials are stored on the Whatnot Channel DocType (encrypted Password field).
The show URL is stored on the Stream Event's whatnot_show_url field.

Usage from UI:
    Stream Event → "Fetch from Whatnot" button  (requires whatnot_show_url set)
    Sales Upload → "Fetch from Whatnot" button  (when no file attached yet)

Usage from Python:
    from vortex_ops.automation.whatnot_scraper import fetch_and_create_upload
    fetch_and_create_upload("STRM-2025-0001")
"""

import frappe
from vortex_ops.utils import safe_float, log_automation


# ── Public whitelisted endpoint ───────────────────────────────────────────────

@frappe.whitelist()
def fetch_and_create_upload(stream_event_name):
    """
    Scrape the Whatnot show recap and create (or update) a Sales Upload for
    the given Stream Event.  Returns the Sales Upload name.
    """
    _assert_playwright()

    stream = frappe.get_doc("Stream Event", stream_event_name)
    if not stream.whatnot_show_url:
        frappe.throw(
            "Set the <b>Whatnot Show URL</b> on this Stream Event first. "
            "Find it in your Whatnot seller dashboard after the show ends."
        )

    channel = stream.channel
    if not channel:
        frappe.throw("Stream Event has no Whatnot Channel linked.")

    creds  = _get_credentials(channel)
    recap  = _scrape_recap(stream.whatnot_show_url, creds)

    # Update Stream Event financials if they're blank and we got good data
    updates = {}
    if recap.get("gross_sales") and not stream.gross_sales:
        updates["gross_sales"] = recap["gross_sales"]
    if recap.get("total_packages") and not stream.total_packages:
        updates["total_packages"] = recap["total_packages"]
    if recap.get("tips") and not stream.tips:
        updates["tips"] = recap["tips"]
    if updates:
        frappe.db.set_value("Stream Event", stream_event_name, updates)

    # Find an existing draft Sales Upload for this stream + streamer, or create one
    existing = frappe.db.exists("Sales Upload", {
        "stream_event": stream_event_name,
        "streamer":     stream.primary_streamer,
        "docstatus":    0,
    })
    su = frappe.get_doc("Sales Upload", existing) if existing \
        else frappe.new_doc("Sales Upload")

    su.stream_event  = stream_event_name
    su.streamer      = stream.primary_streamer
    su.upload_status = "Pending"

    if recap.get("items"):
        su.sales_lines = []
        for item in recap["items"]:
            su.append("sales_lines", {
                "raw_description": (item.get("description") or "")[:200],
                "qty_sold":        max(1, int(item.get("qty") or 1)),
                "sale_amount":     safe_float(item.get("sale_amount")),
                "match_status":    "Unmatched",
            })

    su.save(ignore_permissions=True)
    frappe.db.commit()

    n_items = len(recap.get("items", []))
    log_automation(
        "Whatnot Scrape", "Sales Upload", su.name, "Success",
        output_text=(
            f"Scraped {n_items} line(s) · "
            f"Gross ${recap.get('gross_sales', 0):,.2f} · "
            f"Extracted via {'AI' if recap.get('_ai_used') else 'regex'}"
        ),
    )
    frappe.msgprint(
        f"<b>Scraped {n_items} item(s)</b> from Whatnot "
        f"({'AI extraction' if recap.get('_ai_used') else 'regex fallback'}).<br>"
        f"Sales Upload <b>{su.name}</b> is ready — run AI Match to map items to "
        f"your catalogue, then approve and submit to deduct inventory.",
        indicator="green",
    )
    return su.name


# ── Core scraper ──────────────────────────────────────────────────────────────

def _scrape_recap(show_url: str, creds: dict) -> dict:
    """Log in with Playwright, capture page text, extract via AI then regex."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        try:
            _login(page, creds)
            page.goto(show_url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2500)

            # Scroll to trigger any lazy-loaded content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

            page_text = page.inner_text("body", timeout=10_000)
        finally:
            browser.close()

    # Phase 2 — AI extraction (primary)
    recap = _ai_extract(page_text, show_url)

    # Phase 3 — regex fallback if AI returned nothing useful
    if not recap.get("gross_sales") and not recap.get("items"):
        recap = _regex_extract(page_text)
        recap["_ai_used"] = False
    else:
        recap["_ai_used"] = True

    return recap


# ── AI extraction (Ollama) ────────────────────────────────────────────────────

def _ai_extract(page_text: str, show_url: str) -> dict:
    """
    Ask Ollama to parse the raw Whatnot page text into structured show data.
    Uses a focused sports-card-industry prompt so the model knows what to look for.
    Returns the parsed dict or empty dict if Ollama is unavailable / fails.
    """
    from vortex_ops.utils import ollama_json
    from vortex_ops.ai.business_context import get_context_brief

    # Truncate to ~6 000 chars so we don't blow Ollama's context window
    text_sample = page_text[:6000]

    system = (
        get_context_brief()
        + "\n\nYOU ARE: A data extraction assistant parsing a Whatnot show recap page.\n"
        "The page belongs to a sports card / TCG break business. Extract ONLY factual "
        "numbers you can see in the text — do not invent values. If a field is not "
        "visible, return null or an empty array."
    )

    prompt = f"""
Extract show summary data from this Whatnot page text.

PAGE TEXT:
{text_sample}

Return a single JSON object with this exact structure:
{{
  "gross_sales":    <total show sales as a number, e.g. 1250.00>,
  "total_packages": <total number of packages/lots sold as an integer>,
  "tips":           <total tips received as a number>,
  "items": [
    {{
      "description": "<item title or lot description>",
      "qty":         <quantity sold as integer>,
      "sale_amount": <sale price as number>
    }}
  ]
}}

Rules:
- gross_sales is the total dollar amount sold in the show (before any fees).
- Each item in the array is ONE distinct product or lot sold.
- If the page shows individual sold items/lots, list each one.
- If only totals are shown (no individual items), return an empty items array.
- Dollar amounts must be plain numbers with no $ sign.
- Return ONLY the JSON object — no explanation, no markdown.
"""

    try:
        result = ollama_json(prompt, system=system)
        if not isinstance(result, dict):
            return {}
        # Coerce types defensively
        return {
            "gross_sales":    safe_float(result.get("gross_sales")),
            "total_packages": int(result.get("total_packages") or 0),
            "tips":           safe_float(result.get("tips")),
            "items":          result.get("items") or [],
        }
    except Exception as e:
        frappe.log_error(
            f"Whatnot scraper — Ollama extraction failed for {show_url}: {e}",
            "Whatnot AI Extract"
        )
        return {}


# ── Regex fallback ────────────────────────────────────────────────────────────

def _regex_extract(page_text: str) -> dict:
    """
    Best-effort regex extraction when Ollama is unavailable.
    Looks for currency amounts and common label patterns in the page text.
    """
    import re

    result = {"gross_sales": 0.0, "total_packages": 0, "tips": 0.0, "items": []}

    # Find total gross — look for labeled amounts
    gross_match = re.search(
        r"(?:total\s+sales?|gross\s+sales?|total\s+revenue)[^\d]*\$?\s*([\d,]+(?:\.\d{2})?)",
        page_text, re.I,
    )
    if gross_match:
        result["gross_sales"] = safe_float(gross_match.group(1).replace(",", ""))

    tips_match = re.search(
        r"(?:tips?)[^\d]*\$?\s*([\d,]+(?:\.\d{2})?)",
        page_text, re.I,
    )
    if tips_match:
        result["tips"] = safe_float(tips_match.group(1).replace(",", ""))

    # Pull all dollar amounts from the text as potential line items
    money_lines = re.findall(
        r"([A-Za-z0-9][^\n]{4,60}?)\s+\$?\s*([\d,]+\.\d{2})",
        page_text,
    )
    for desc, amount in money_lines[:50]:
        desc   = desc.strip()
        amount = safe_float(amount.replace(",", ""))
        if desc and amount > 0:
            result["items"].append({
                "description": desc[:200],
                "qty":         1,
                "sale_amount": amount,
            })

    if not result["gross_sales"] and result["items"]:
        result["gross_sales"] = round(sum(i["sale_amount"] for i in result["items"]), 2)

    result["total_packages"] = len(result["items"])

    # Log page snippet so developers can tune if needed
    if not result["items"]:
        frappe.log_error(
            f"Whatnot scraper regex found no data.\nPage snippet:\n{page_text[:800]}",
            "Whatnot Scraper — No Data"
        )

    return result


# ── Auth ──────────────────────────────────────────────────────────────────────

def _login(page, creds: dict):
    """Navigate to Whatnot login and authenticate."""
    from playwright.sync_api import TimeoutError as PWTimeout

    page.goto("https://www.whatnot.com/login", wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    try:
        page.fill(
            'input[type="email"], input[name="email"], input[placeholder*="email" i]',
            creds["username"], timeout=10_000,
        )
    except PWTimeout:
        frappe.throw("Whatnot login page — email field not found. Page structure may have changed.")

    try:
        page.fill('input[type="password"]', creds["password"], timeout=5_000)
    except PWTimeout:
        frappe.throw("Whatnot login page — password field not found.")

    page.keyboard.press("Enter")

    try:
        page.wait_for_url(lambda url: "login" not in url, timeout=15_000)
    except PWTimeout:
        frappe.throw(
            "Whatnot login failed or timed out. "
            "Check the username and password on the Whatnot Channel record."
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_credentials(channel_name: str) -> dict:
    channel  = frappe.get_doc("Whatnot Channel", channel_name)
    username = channel.whatnot_username
    password = channel.get_password("whatnot_password") if channel.whatnot_password else None
    if not username or not password:
        frappe.throw(
            f"Whatnot Channel <b>{channel_name}</b> is missing username or password. "
            "Set them on the Whatnot Channel record before scraping."
        )
    return {"username": username, "password": password}


def _assert_playwright():
    try:
        import playwright  # noqa
    except ImportError:
        frappe.throw(
            "Playwright is not installed on this server.<br><br>"
            "Run via SSH:<br>"
            "<code>pip install playwright &amp;&amp; playwright install chromium</code>"
        )
