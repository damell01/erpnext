import frappe


def boot_session(bootinfo):
    """
    Overrides session-level branding so the client never sees 'ERPNext' or
    'Frappe' in the desk.  Called once per login via the boot_session hook.
    """
    # Replace the app title shown in desk header / browser title fallback
    bootinfo.app_title    = "Vortex Ops"
    bootinfo.app_name     = "vortex_ops"
    bootinfo.app_logo_url = "/assets/vortex_ops/images/vortex_logo.png"

    # Suppress the "Powered by Frappe" tagline that appears in the footer
    bootinfo.sysdefaults["powered_by"] = ""

    # Suppress "Update available for ERPNext" notifications
    bootinfo.update_info = {}

    # Set a neutral product name that appears in About dialog etc.
    bootinfo.sysdefaults["product_name"] = "Vortex Ops"
