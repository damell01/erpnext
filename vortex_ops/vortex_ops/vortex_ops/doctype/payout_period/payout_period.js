frappe.ui.form.on("Payout Period", {
    refresh(frm) {
        if (frm.is_new()) return;

        // ── Step 1: Pull streams ───────────────────────────────────────────
        frm.add_custom_button("1 · Pull Streams", () =>
            frm.call("pull_streams").then(() => frm.refresh()), "Payroll");

        // ── Step 2: Generate payouts for all streamers ────────────────────
        frm.add_custom_button("2 · Generate Payouts", () => {
            frappe.confirm(
                `Generate a Streamer Payout for every streamer in this period's ${frm.doc.streams?.length || 0} stream(s)?`,
                () => frm.call("generate_payouts").then(() => frm.refresh())
            );
        }, "Payroll");

        // ── Step 3: Review + export ───────────────────────────────────────
        frm.add_custom_button("View All Payouts", () =>
            frappe.set_route("List", "Streamer Payout",
                { payout_period: frm.doc.name }), "Payroll");

        frm.add_custom_button("Payroll Export", () =>
            frappe.set_route("query-report", "Payroll Export",
                { payout_period: frm.doc.name }), "Payroll");

        if (frappe.user.has_role("Vortex Admin")) {
            frm.add_custom_button("Run Anomaly Check", () => {
                frappe.call({
                    method:   "vortex_ops.ai.anomaly_detection.run_anomaly_check",
                    args:     { payout_period_name: frm.doc.name },
                    callback(r) { frm.refresh(); },
                });
            }, "AI");
        }
    },
});
