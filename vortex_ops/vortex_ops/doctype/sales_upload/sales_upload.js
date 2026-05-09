frappe.ui.form.on("Sales Upload", {
    refresh(frm) {
        _update_indicators(frm);
        if (frm.is_new()) return;

        const status    = frm.doc.upload_status;
        const unmatched = frm.doc.unmatched_lines || 0;
        const total     = frm.doc.total_lines     || 0;

        // Whatnot auto-scrape — shown when stream has a show URL and no file yet
        if (!frm.doc.uploaded_file && status === "Pending" && frm.doc.stream_event) {
            frappe.db.get_value("Stream Event", frm.doc.stream_event, "whatnot_show_url", r => {
                if (r && r.whatnot_show_url) {
                    frm.add_custom_button("Fetch from Whatnot", () => {
                        frappe.confirm(
                            "Scrape the Whatnot show recap and populate lines automatically?",
                            () => {
                                frappe.show_progress("Scraping Whatnot…", 50, 100);
                                frappe.call({
                                    method: "vortex_ops.automation.whatnot_scraper.fetch_and_create_upload",
                                    args:   { stream_event_name: frm.doc.stream_event },
                                    callback(r) {
                                        frappe.hide_progress();
                                        frm.refresh();
                                    },
                                });
                            }
                        );
                    }, "Actions");
                }
            });
        }

        // CSV path — only show if a file is attached
        if (frm.doc.uploaded_file && status === "Pending") {
            frm.add_custom_button("Parse CSV File", () =>
                frm.call("parse_csv").then(() => frm.refresh()), "Actions");
        }

        // AI match for unmatched lines
        if (unmatched > 0 && status !== "Approved" && status !== "Processed") {
            frm.add_custom_button("Run AI Match", () => {
                frappe.confirm(
                    `Run Ollama AI on ${unmatched} unmatched line(s)?`,
                    () => {
                        frappe.show_progress("Running AI match…", 50, 100);
                        frm.call("run_ai_match").then(() => {
                            frappe.hide_progress();
                            frm.refresh();
                        });
                    }
                );
            }, "Actions");
        }

        // Approve when lines are ready (all matched, or admin overrides)
        const allMatched = total > 0 && unmatched === 0;
        if (
            frappe.user.has_role("Vortex Operations") &&
            (status === "Under Review" || (status === "Pending" && allMatched))
        ) {
            frm.add_custom_button("Approve Upload", () =>
                frm.call("approve").then(() => frm.refresh()), "Actions");
        }
    },

    // Auto-fill streamer from stream event's primary streamer
    stream_event(frm) {
        if (!frm.doc.stream_event) return;
        frappe.db.get_value("Stream Event", frm.doc.stream_event, "primary_streamer", r => {
            if (r && r.primary_streamer && !frm.doc.streamer) {
                frm.set_value("streamer", r.primary_streamer);
            }
        });
    },

    // When streamer changes, fill warehouse on any unassigned lines
    streamer(frm) {
        if (!frm.doc.streamer) return;
        frappe.db.get_value("Streamer", frm.doc.streamer, "warehouse", r => {
            if (!r || !r.warehouse) return;
            let changed = false;
            (frm.doc.sales_lines || []).forEach(line => {
                if (!line.warehouse) {
                    frappe.model.set_value(line.doctype, line.name, "warehouse", r.warehouse);
                    changed = true;
                }
            });
            if (changed) frm.refresh_field("sales_lines");
        });
    },
});


// Fill warehouse when a new line's item is set
frappe.ui.form.on("Sales Upload Line", {
    item_code(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.warehouse && frm.doc.streamer) {
            frappe.db.get_value("Streamer", frm.doc.streamer, "warehouse", r => {
                if (r && r.warehouse) {
                    frappe.model.set_value(cdt, cdn, "warehouse", r.warehouse);
                }
            });
        }
        // Auto-set match status to Manual when item is picked by hand
        if (row.item_code && !row.match_status) {
            frappe.model.set_value(cdt, cdn, "match_status", "Manual");
        }
    },

    qty_sold(frm) { frm.trigger("_recalc_lines"); },
    sale_amount(frm) { frm.trigger("_recalc_lines"); },
});


function _update_indicators(frm) {
    const total    = frm.doc.total_lines    || 0;
    const matched  = frm.doc.matched_lines  || 0;
    const pct      = total > 0 ? Math.round((matched / total) * 100) : 0;
    const fmt      = n => "$" + Number(n || 0).toLocaleString("en-US", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });

    if (total > 0) {
        frm.dashboard.add_indicator(
            `${pct}% Matched (${matched}/${total})`,
            pct === 100 ? "green" : "orange"
        );
    }
    if ((frm.doc.total_sale_amount || 0) > 0) {
        frm.dashboard.add_indicator(
            `Sales: ${fmt(frm.doc.total_sale_amount)}`, "blue"
        );
    }
    if ((frm.doc.total_cogs_estimate || 0) > 0) {
        frm.dashboard.add_indicator(
            `Est. COGS: ${fmt(frm.doc.total_cogs_estimate)}`, "gray"
        );
    }

    const statusColors = {
        Pending:      "gray",
        "Under Review": "blue",
        Approved:     "green",
        Processed:    "purple",
        Rejected:     "red",
    };
    if (frm.doc.upload_status) {
        frm.dashboard.add_indicator(
            frm.doc.upload_status,
            statusColors[frm.doc.upload_status] || "gray"
        );
    }
}
