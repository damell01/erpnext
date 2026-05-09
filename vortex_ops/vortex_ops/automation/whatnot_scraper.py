"""
Whatnot Show Recap Scraper
==========================
Uses Playwright to log into Whatnot and pull the post-show sales summary
for a given show URL.  The result populates a Sales Upload document.

Setup (run once on the server):
    pip install playwright
    playwright install chromium

Credentials are stored on the Whatnot Channel DocType (encrypted Password field).
The show URL is stored on the Stream Event's whatnot_show_url field.

Call from Python:
    from vortex_ops.automation.whatnot_scraper import fetch_show_recap
    result = fetch_show_recap("STRM-2025-0001")

Or via whitelisted endpoint (button in UI):
    frappe.call({ method: "vortex_ops.automation.whatnot_scraper.fetch_and_create_upload",
                  args: { stream_event_name: "STRM-2025-0001" } })
"""

import frappe
from vortex_ops.utils import safe_float, log_automation


# ── Public entry point called from the UI button ──────────────────────────────

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
            "Set the Whatnot Show URL on this Stream Event before scraping. "
            "You can find it in the Whatnot seller dashboard after the show ends."
        )

    channel = frappe.db.get_value("Stream Event", stream_event_name, "channel")
    if not channel:
        frappe.throw("Stream Event has no Whatnot Channel linked.")

    creds = _get_credentials(channel)
    recap = _scrape_recap(stream.whatnot_show_url, creds)

    # Update Stream Event financials if they look better than what's on record
    if recap.get("gross_sales") and not stream.gross_sales:
        frappe.db.set_value("Stream Event", stream_event_name, {
            "gross_sales":    recap["gross_sales"],
            "total_packages": recap.get("total_packages") or stream.total_packages,
            "tips":           recap.get("tips")          or stream.tips,
        })

    # Create or find existing Sales Upload for this stream / primary streamer
    existing = frappe.db.exists("Sales Upload", {
        "stream_event": stream_event_name,
        "streamer":     stream.primary_streamer,
        "docstatus":    0,
    })
    if existing:
        su = frappe.get_doc("Sales Upload", existing)
    else:
        su = frappe.new_doc("Sales Upload")
        su.stream_event = stream_event_name
        su.streamer     = stream.primary_streamer

    # Populate lines from scraped items
    if recap.get("items"):
        su.sales_lines = []
        for item in recap["items"]:
            su.append("sales_lines", {
                "raw_description": item.get("description", ""),
                "qty_sold":        item.get("qty", 1),
                "sale_amount":     item.get("sale_amount", 0),
                "match_status":    "Unmatched",
            })

    su.upload_status = "Pending"
    su.save(ignore_permissions=True)
    frappe.db.commit()

    log_automation(
        "Whatnot Scrape", "Sales Upload", su.name, "Success",
        output_text=(
            f"Scraped {len(recap.get('items', []))} line(s) · "
            f"Gross ${recap.get('gross_sales', 0):,.2f}"
        ),
    )
    frappe.msgprint(
        f"Scraped {len(recap.get('items', []))} item(s) from Whatnot. "
        f"Sales Upload {su.name} is ready — run AI match or map items manually, then approve.",
        indicator="green",
    )
    return su.name


# ── Core scraper ──────────────────────────────────────────────────────────────

def _scrape_recap(show_url: str, creds: dict) -> dict:
    """
    Log into Whatnot and extract the show recap.
    Returns a dict:
        {
            "gross_sales":    float,
            "total_packages": int,
            "tips":           float,
            "items": [
                {"description": str, "qty": int, "sale_amount": float},
                ...
            ]
        }
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        try:
            _login(page, creds)
            return _extract_recap(page, show_url)
        finally:
            browser.close()


def _login(page, creds: dict):
    """Navigate to Whatnot login and authenticate."""
    from playwright.sync_api import TimeoutError as PWTimeout

    page.goto("https://www.whatnot.com/login", wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1500)

    # Fill username/email
    try:
        page.fill('input[type="email"], input[name="email"], input[placeholder*="email" i]',
                  creds["username"], timeout=10_000)
    except PWTimeout:
        frappe.throw("Whatnot login page structure has changed — email field not found.")

    # Fill password
    try:
        page.fill('input[type="password"]', creds["password"], timeout=5_000)
    except PWTimeout:
        frappe.throw("Whatnot login page — password field not found.")

    # Submit
    page.keyboard.press("Enter")

    # Wait for redirect away from login page
    try:
        page.wait_for_url(lambda url: "login" not in url, timeout=15_000)
    except PWTimeout:
        frappe.throw(
            "Whatnot login failed or timed out. "
            "Check the username/password on the Whatnot Channel record."
        )


def _extract_recap(page, show_url: str) -> dict:
    """
    Navigate to the show URL and extract summary + item sales.
    Whatnot show recap pages vary in structure — this uses content-based
    extraction with multiple fallback strategies.
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    page.goto(show_url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2000)

    result = {
        "gross_sales":    0.0,
        "total_packages": 0,
        "tips":           0.0,
        "items":          [],
    }

    # ── Summary numbers ────────────────────────────────────────────────────────
    # Try to find the gross sales total from common patterns on the recap page
    for selector in [
        "[data-testid*='total-sales']",
        "[data-testid*='gross-sales']",
        ".show-summary [class*='total']",
        "text=/Total Sales/",
    ]:
        try:
            el = page.locator(selector).first
            txt = el.inner_text(timeout=3_000)
            val = _parse_money(txt)
            if val > 0:
                result["gross_sales"] = val
                break
        except Exception:
            continue

    # ── Item-level sales rows ─────────────────────────────────────────────────
    # Whatnot recap typically shows a list of items sold with qty and price.
    # Try table rows, then list items.
    item_rows = []

    for row_sel in [
        "table tbody tr",
        "[data-testid*='item-row']",
        "[class*='lot-row']",
        "[class*='sale-row']",
        "[class*='item-list'] > *",
    ]:
        try:
            rows = page.locator(row_sel).all()
            if len(rows) >= 1:
                item_rows = rows
                break
        except Exception:
            continue

    for row in item_rows:
        try:
            text = row.inner_text(timeout=2_000).strip()
            if not text:
                continue

            # Parse amount from row text
            amount = _parse_money(text)

            # Parse qty — look for patterns like "x2", "2x", "Qty: 2"
            import re
            qty_match = re.search(r"\bx\s*(\d+)\b|\b(\d+)\s*x\b|qty[:\s]+(\d+)", text, re.I)
            qty = int(qty_match.group(1) or qty_match.group(2) or qty_match.group(3)) \
                if qty_match else 1

            # Use first non-numeric text chunk as description
            desc_lines = [l.strip() for l in text.splitlines() if l.strip()]
            desc = desc_lines[0] if desc_lines else text[:80]

            if amount > 0 or desc:
                result["items"].append({
                    "description":  desc[:200],
                    "qty":          qty,
                    "sale_amount":  amount,
                })
        except Exception:
            continue

    # ── Full-page fallback ────────────────────────────────────────────────────
    # If no structured rows found, log the page text so the dev can tune selectors
    if not result["items"] and not result["gross_sales"]:
        snippet = page.inner_text("body", timeout=5_000)[:500]
        frappe.log_error(
            f"Whatnot scraper found no data on {show_url}.\n"
            f"Page snippet:\n{snippet}\n\n"
            "Update selectors in automation/whatnot_scraper.py _extract_recap().",
            "Whatnot Scraper — No Data"
        )
        frappe.msgprint(
            "Scraper connected to Whatnot but couldn't find show data on the page. "
            "An error log has been created — a developer can adjust the page selectors.",
            indicator="orange",
        )

    result["total_packages"] = len(result["items"])
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_credentials(channel_name: str) -> dict:
    channel = frappe.get_doc("Whatnot Channel", channel_name)
    username = channel.whatnot_username
    password = channel.get_password("whatnot_password") if channel.whatnot_password else None
    if not username or not password:
        frappe.throw(
            f"Whatnot Channel '{channel_name}' is missing username or password. "
            "Set them on the Whatnot Channel record before scraping."
        )
    return {"username": username, "password": password}


def _parse_money(text: str) -> float:
    """Extract the first dollar amount from a string."""
    import re
    match = re.search(r"\$?\s*([\d,]+(?:\.\d{1,2})?)", text.replace(",", ""))
    return safe_float(match.group(1)) if match else 0.0


def _assert_playwright():
    try:
        import playwright  # noqa
    except ImportError:
        frappe.throw(
            "Playwright is not installed. Run on the server:<br>"
            "<code>pip install playwright && playwright install chromium</code>"
        )
