"""
Run once after install to seed Vortex Settings and push brand defaults
into System Settings so emails and the login page are correct from day one.

    bench --site <site> execute vortex_ops.vortex_ops.setup.brand_setup.run
"""
import frappe


def run(brand_name="VortexBreaks", primary_color="#E8630A"):
    _seed_vortex_settings(brand_name, primary_color)
    _patch_system_settings(brand_name)
    frappe.db.commit()
    print(f"[vortex] Brand set to '{brand_name}'")


def _seed_vortex_settings(brand_name, primary_color):
    doc = frappe.get_single("Vortex Settings")
    if not doc.brand_name:
        doc.brand_name    = brand_name
        doc.primary_color = primary_color
        doc.login_tagline = "Operations Platform"
        doc.save(ignore_permissions=True)


def _patch_system_settings(brand_name):
    frappe.db.set_value("System Settings", "System Settings", {
        "app_name":             brand_name,
        "footer_items":         brand_name,
        "email_footer_address": brand_name,
    })
