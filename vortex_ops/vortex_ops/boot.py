import frappe
from vortex_ops.vortex_ops.doctype.vortex_settings.vortex_settings import get_brand


def boot_session(bootinfo):
    """
    Injects brand config into every desk session so the client never sees
    ERPNext / Frappe anywhere — name, logo, and color all come from
    Vortex Settings (configurable by admin without a code deploy).
    """
    brand = get_brand()

    # Core desk identity
    bootinfo.app_title             = brand["brand_name"]
    bootinfo.app_name              = "vortex_ops"
    bootinfo.app_logo_url          = brand["logo_url"]

    # Expose brand values to vortex_boot.js for DOM/title scrubbing
    bootinfo.vortex_brand_name     = brand["brand_name"]
    bootinfo.vortex_primary_color  = brand["primary_color"]
    bootinfo.vortex_login_tagline  = brand["login_tagline"]

    # Suppress third-party references
    bootinfo.sysdefaults["powered_by"]    = ""
    bootinfo.sysdefaults["product_name"]  = brand["brand_name"]
    bootinfo.update_info = {}


def get_website_context(context):
    """Injects brand into the login page and all web-facing Frappe pages."""
    brand = get_brand()
    context["app_name"]      = brand["brand_name"]
    context["app_logo_url"]  = brand["logo_url"]
    context["login_tagline"] = brand["login_tagline"]
    context["top_bar_items"] = []
