frappe.ui.form.on("Payout Period", {
    refresh(frm) {
        if (frm.is_new()) return;

        _load_payout_summary(frm);

        // ── Step 1: Pull streams ──────────────────────────────────────────
        frm.add_custom_button("1 · Pull Streams", () =>
            frm.call("pull_streams").then(() => frm.refresh()), "Payroll");

        // ── Step 2: Generate payouts ──────────────────────────────────────
        frm.add_custom_button("2 · Generate Payouts", () => {
            const count = frm.doc.streams?.length || 0;
            frappe.confirm(
                `Generate a Streamer Payout for every streamer in ${count} stream(s)?`,
                () => frm.call("generate_payouts").then(() => frm.refresh())
            );
        }, "Payroll");

        // ── Step 3: Approve all ───────────────────────────────────────────
        frm.add_custom_button("3 · Approve All Reviewed", () => {
            frappe.confirm(
                "Approve all Reviewed payouts in this period and record loan deductions?",
                () => frm.call("approve_all_reviewed").then(() => frm.refresh())
            );
        }, "Payroll");

        // ── Navigation ────────────────────────────────────────────────────
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

    // Auto-suggest period name from dates when the field is blank
    start_date(frm) { _suggest_period_name(frm); },
    end_date(frm)   { _suggest_period_name(frm); },
});


function _suggest_period_name(frm) {
    if (!frm.doc.start_date || !frm.doc.end_date) return;
    if (frm.doc.period_name) return;  // don't overwrite if already set

    const months = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"];
    const s = frappe.datetime.str_to_obj(frm.doc.start_date);
    const e = frappe.datetime.str_to_obj(frm.doc.end_date);

    let name;
    if (s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()) {
        name = `Week of ${months[s.getMonth()]} ${s.getDate()}–${e.getDate()}, ${s.getFullYear()}`;
    } else {
        name = `${months[s.getMonth()]} ${s.getDate()} – ${months[e.getMonth()]} ${e.getDate()}, ${e.getFullYear()}`;
    }
    frm.set_value("period_name", name);
}


function _load_payout_summary(frm) {
    frm.call("get_payout_summary").then(r => {
        const s = r.message;
        if (!s || s.total === 0) return;

        const fmt = n => "$" + Number(n).toLocaleString("en-US", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });

        // Total indicator
        frm.dashboard.add_indicator(
            `${s.total} Payout(s) · ${fmt(s.total_payout)} total`, "blue"
        );

        // Per-status indicators
        const colors = {
            Draft:    "gray",
            Reviewed: "blue",
            Approved: "green",
            Exported: "purple",
        };
        const order = ["Draft", "Reviewed", "Approved", "Exported"];
        for (const status of order) {
            const d = s.by_status[status];
            if (!d) continue;
            frm.dashboard.add_indicator(
                `${status}: ${d.count} (${fmt(d.amount)})`,
                colors[status] || "gray"
            );
        }
    });
}
