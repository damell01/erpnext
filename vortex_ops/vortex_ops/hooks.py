app_name        = "vortex_ops"
app_title       = "Vortex Ops"
app_publisher   = "DBell Creations"
app_description = "Vortex Breaks Operations Platform"
app_version     = "1.0.0"
app_icon        = "fa fa-fire"
app_color       = "#E8630A"
app_license     = "proprietary"

# ── White-label assets injected into every desk page ─────────────────────────
app_include_css = ["/assets/vortex_ops/css/vortex_theme.css"]
app_include_js  = ["/assets/vortex_ops/js/vortex_boot.js"]

# ── Override boot data so the session carries Vortex branding ─────────────────
boot_session = "vortex_ops.boot.boot_session"

# ── Login / web page branding — reads from Vortex Settings ───────────────────
website_context = "vortex_ops.boot.get_website_context"

# ── Seed brand defaults on first install ──────────────────────────────────────
after_install = "vortex_ops.setup.brand_setup.run"

scheduler_events = {
    "hourly": [
        "vortex_ops.automation.daily_tasks.check_pending_uploads",
    ],
    "daily": [
        "vortex_ops.automation.daily_tasks.run_daily",
        "vortex_ops.automation.missing_reports.check_missing_reports",
        "vortex_ops.ai.low_stock_predictor.run_predictions",
    ],
    "weekly": [
        "vortex_ops.automation.weekly_tasks.run_weekly",
    ],
}

doc_events = {
    "Stream Event": {
        "validate":  "vortex_ops.vortex_ops.doctype.stream_event.stream_event.validate_doc",
        "on_submit": "vortex_ops.vortex_ops.doctype.stream_event.stream_event.on_submit",
        "on_cancel": "vortex_ops.vortex_ops.doctype.stream_event.stream_event.on_cancel",
    },
    "Sales Upload": {
        "validate":  "vortex_ops.vortex_ops.doctype.sales_upload.sales_upload.validate_doc",
        "on_submit": "vortex_ops.vortex_ops.doctype.sales_upload.sales_upload.on_submit",
    },
    "Streamer Payout": {
        "validate":  "vortex_ops.vortex_ops.doctype.streamer_payout.streamer_payout.validate_doc",
        "on_submit": "vortex_ops.vortex_ops.doctype.streamer_payout.streamer_payout.on_submit",
    },
    "Loan Record": {
        "on_submit": "vortex_ops.vortex_ops.doctype.loan_record.loan_record.on_submit",
        "on_cancel": "vortex_ops.vortex_ops.doctype.loan_record.loan_record.on_cancel",
    },
}

fixtures = [
    {"dt": "Role",           "filters": [["name", "like", "Vortex%"]]},
    {"dt": "Workspace",      "filters": [["name", "like", "Vortex%"]]},
    {"dt": "Print Format",   "filters": [["module", "=", "Vortex Ops"]]},
    {"dt": "Report",         "filters": [["module", "=", "Vortex Ops"]]},
    {"dt": "Custom Field",   "filters": [["dt", "=", "Warehouse"],
                                         ["fieldname", "=", "is_vortex_managed"]]},
    # Export brand config so deployments start with the right name/color
    {"dt": "Vortex Settings"},
]
