frappe.ui.form.on("Streamer Payout", {
    refresh(frm) {
        const total = frm.doc.total_payout || 0;
        frm.dashboard.add_indicator(
            `Total Payout: $${total.toFixed(2)}`,
            total > 0 ? "green" : "red"
        );

        if (frm.is_new()) return;

        frm.add_custom_button("Pull Stream Data", () =>
            frm.call("pull_stream_data").then(() => frm.refresh()), "Actions");

        if (
            frappe.user.has_role("Vortex Accounting") &&
            frm.doc.status === "Approved"
        ) {
            frm.add_custom_button("Export to ADP (CSV)", () => {
                const rows = [
                    ["Employee ID", "Streamer", "Legal Name", "Amount", "Period",
                     "Payout Type", "Platform Fee", "Loan Deductions"],
                    [
                        frm.doc.adp_employee_id || "",
                        frm.doc.streamer,
                        "",
                        frm.doc.total_payout,
                        frm.doc.payout_period,
                        frm.doc.payout_type,
                        frm.doc.owner_platform_fee_amount || 0,
                        frm.doc.loan_deductions || 0,
                    ],
                ];
                const csv  = rows.map(r => r.join(",")).join("\n");
                const blob = new Blob([csv], { type: "text/csv" });
                const url  = URL.createObjectURL(blob);
                const a    = document.createElement("a");
                a.href     = url;
                a.download = `payout_${frm.doc.name}_${frm.doc.streamer}.csv`;
                a.click();
                frm.set_value("status", "Exported");
                frm.save();
            }, "Actions");
        }
    },
});
