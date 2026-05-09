frappe.ui.form.on("Streamer", {
    refresh(frm) {
        frm.trigger("payout_type");
        if (!frm.is_new()) {
            frm.add_custom_button("View Inventory", () =>
                frappe.set_route("query-report", "Inventory by Streamer",
                    { streamer: frm.doc.name }), "Reports");
            frm.add_custom_button("Payout History", () =>
                frappe.set_route("List", "Streamer Payout",
                    { streamer: frm.doc.name }), "Reports");
            frm.call("get_loan_balance").then(r => {
                if (r.message > 0) {
                    frm.dashboard.add_indicator(
                        `Active Loan: $${r.message.toFixed(2)}`, "orange");
                }
            });
        }
    },

    payout_type(frm) {
        frm.toggle_display("payout_percentage", frm.doc.payout_type === "Profit Share");
        frm.toggle_display("package_rate",      frm.doc.payout_type === "Package");
    }
});
