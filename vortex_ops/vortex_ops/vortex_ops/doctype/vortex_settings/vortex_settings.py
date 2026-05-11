import frappe
from frappe.model.document import Document


class VortexSettings(Document):
    def on_update(self):
        _sync_to_system(self)
        frappe.clear_cache()


def _sync_to_system(doc):
    """
    Push brand values into Frappe's System Settings so every surface that
    reads from there (emails, login page, About dialog) picks up our brand.
    """
    brand = doc.brand_name or "VortexBreaks"
    footer = doc.email_footer_text or brand

    updates = {
        "app_name":            brand,
        "footer_items":        footer,
        "email_footer_address": footer,
    }
    if doc.logo_url:
        updates["app_logo_url"] = doc.logo_url

    frappe.db.set_value("System Settings", "System Settings", updates)


def get_brand():
    """
    Return the current brand dict.  Safe to call from boot / website_context
    even before Vortex Settings has been saved — falls back to defaults.
    """
    try:
        doc = frappe.get_cached_doc("Vortex Settings")
        return {
            "brand_name":    doc.brand_name    or "VortexBreaks",
            "logo_url":      doc.logo_url      or "",
            "primary_color": doc.primary_color or "#E8630A",
            "login_tagline": doc.login_tagline or "",
            "email_footer":  doc.email_footer_text or doc.brand_name or "VortexBreaks",
        }
    except Exception:
        return {
            "brand_name":    "VortexBreaks",
            "logo_url":      "",
            "primary_color": "#E8630A",
            "login_tagline": "",
            "email_footer":  "VortexBreaks",
        }
