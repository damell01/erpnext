frappe.ui.form.on("Sales Upload", {
    refresh(frm) {
        const total    = frm.doc.total_lines    || 0;
        const matched  = frm.doc.matched_lines  || 0;
        const pct      = total > 0 ? Math.round((matched / total) * 100) : 0;

        if (total > 0) {
            frm.dashboard.add_indicator(
                `${pct}% Matched (${matched}/${total})`,
                pct === 100 ? "green" : "orange"
            );
        }

        if (frm.is_new()) return;

        if (frm.doc.upload_status === "Pending") {
            frm.add_custom_button("Parse CSV / Excel File", () =>
                frm.call("parse_csv").then(() => frm.refresh()), "Actions");
        }

        if ((frm.doc.unmatched_lines || 0) > 0) {
            frm.add_custom_button("Run AI Match (Ollama)", () => {
                frappe.confirm(
                    `Run Ollama AI on ${frm.doc.unmatched_lines} unmatched line(s)? `
                    + "This uses your local Ollama model and may take a moment.",
                    () => {
                        frappe.show_progress("Running Ollama AI...", 50, 100);
                        frm.call("run_ai_match").then(() => {
                            frappe.hide_progress();
                            frm.refresh();
                        });
                    }
                );
            }, "Actions");
        }

        if (
            frappe.user.has_role("Vortex Operations") &&
            frm.doc.upload_status === "Under Review"
        ) {
            frm.add_custom_button("Approve Upload", () =>
                frm.call("approve").then(() => frm.refresh()), "Actions");
        }
    },
});
