frappe.ui.form.on("Stream Event", {
    refresh(frm) {
        const clr = {
            Draft:     "gray",
            Active:    "blue",
            Completed: "orange",
            Finalized: "green",
            Cancelled: "red",
        };
        frm.dashboard.add_indicator(
            frm.doc.stream_status,
            clr[frm.doc.stream_status] || "gray"
        );

        if (!frm.is_new()) {
            _add_financial_indicators(frm);

            // Whatnot auto-scrape — only shown when a show URL is set
            if (frm.doc.whatnot_show_url && frm.doc.docstatus === 1) {
                frm.add_custom_button("Fetch from Whatnot", () => {
                    frappe.confirm(
                        "Scrape the Whatnot show recap and create a Sales Upload automatically?<br><br>"
                        + `<small>${frm.doc.whatnot_show_url}</small>`,
                        () => {
                            frappe.show_progress("Scraping Whatnot…", 50, 100,
                                "Logging in and pulling show data…");
                            frappe.call({
                                method: "vortex_ops.automation.whatnot_scraper.fetch_and_create_upload",
                                args:   { stream_event_name: frm.doc.name },
                                callback(r) {
                                    frappe.hide_progress();
                                    if (r.message) {
                                        frappe.set_route("Form", "Sales Upload", r.message);
                                    }
                                },
                            });
                        }
                    );
                }, "Actions");
            }

            if (frm.doc.docstatus === 1) {
                [
                    ["Seller Report",       "stream_event"],
                    ["Fulfillment Report",  "stream_event"],
                    ["Sales Upload",        "stream_event"],
                ].forEach(([dt, flt]) => {
                    frm.add_custom_button(dt + "s", () =>
                        frappe.set_route("List", dt, { [flt]: frm.doc.name }), "View");
                });

                if (
                    frappe.user.has_role("Vortex Admin") &&
                    frm.doc.stream_status === "Completed"
                ) {
                    frm.add_custom_button("Finalize Stream", () => {
                        frappe.confirm(
                            "Mark as Finalized? This locks all linked records.",
                            () => {
                                frm.set_value("stream_status", "Finalized");
                                frm.save();
                            }
                        );
                    }, "Actions");
                }
            }
        }
    },

    channel(frm) {
        if (frm.doc.channel) {
            frappe.db.get_value("Whatnot Channel", frm.doc.channel, "business", r => {
                if (r && r.business) frm.set_value("company", r.business);
            });
        }
    },

    gross_sales(frm)   { frm.trigger("recalc"); },
    platform_fees(frm) { frm.trigger("recalc"); },

    recalc(frm) {
        const net = Math.round(
            ((frm.doc.gross_sales || 0) - (frm.doc.platform_fees || 0)) * 100
        ) / 100;
        frm.set_value("net_earned", net);
    },
});


function _add_financial_indicators(frm) {
    const fmt = n => "$" + Number(n || 0).toLocaleString("en-US", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });

    const gross  = frm.doc.gross_sales    || 0;
    const net    = frm.doc.net_earned     || 0;
    const tips   = frm.doc.tips           || 0;
    const pkgs   = frm.doc.total_packages || 0;
    const cogs   = frm.doc.cogs           || 0;
    const profit = frm.doc.gross_profit   || 0;

    if (gross > 0) {
        frm.dashboard.add_indicator(`Gross: ${fmt(gross)}`, "blue");
        frm.dashboard.add_indicator(`Net: ${fmt(net)}`, net >= 0 ? "green" : "red");
    }
    if (tips > 0) {
        frm.dashboard.add_indicator(`Tips: ${fmt(tips)}`, "green");
    }
    if (pkgs > 0) {
        frm.dashboard.add_indicator(`${pkgs} Pkg${pkgs !== 1 ? "s" : ""}`, "gray");
    }
    if (cogs > 0) {
        frm.dashboard.add_indicator(
            `Profit: ${fmt(profit)}`,
            profit >= 0 ? "green" : "red"
        );
    }
}
