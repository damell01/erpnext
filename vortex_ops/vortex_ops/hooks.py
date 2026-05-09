app_name        = "vortex_ops"
app_title       = "Vortex Ops"
app_publisher   = "DBell Creations"
app_description = "Vortex Breaks Operations Platform"
app_version     = "1.0.0"
app_icon        = "fa fa-fire"
app_color       = "#E8630A"
app_license     = "proprietary"

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
    {"dt": "Role",         "filters": [["name", "like", "Vortex%"]]},
    {"dt": "Workspace",    "filters": [["name", "like", "Vortex%"]]},
    {"dt": "Print Format", "filters": [["module", "=", "Vortex Ops"]]},
    {"dt": "Report",       "filters": [["module", "=", "Vortex Ops"]]},
]
