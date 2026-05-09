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

        if (!frm.is_new() && frm.doc.docstatus === 1) {
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
    },

    gross_sales(frm)    { frm.trigger("recalc"); },
    platform_fees(frm)  { frm.trigger("recalc"); },

    recalc(frm) {
        const net = Math.round(
            ((frm.doc.gross_sales || 0) - (frm.doc.platform_fees || 0)) * 100
        ) / 100;
        frm.set_value("net_earned", net);
    },
});
