frappe.ui.form.on("Payout Period", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button("Pull Streams into Period", () =>
                frm.call("pull_streams").then(() => frm.refresh()), "Actions");

            frm.add_custom_button("View Payouts", () =>
                frappe.set_route("List", "Streamer Payout",
                    { payout_period: frm.doc.name }), "View");

            if (frappe.user.has_role("Vortex Admin")) {
                frm.add_custom_button("Run Anomaly Check", () => {
                    frappe.call({
                        method: "vortex_ops.ai.anomaly_detection.run_anomaly_check",
                        args:   { payout_period_name: frm.doc.name },
                        callback(r) { frm.refresh(); },
                    });
                }, "AI");
            }
        }
    },
});
