frappe.ui.form.on("Streamer Payout", {
    refresh(frm) {
        _update_indicator(frm);

        if (frm.is_new()) return;

        frm.add_custom_button("Pull Stream Data", () =>
            frm.call("pull_stream_data").then(() => frm.refresh()), "Actions");

        // Approve: Reviewed → Approved (also deducts loans)
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.status === "Reviewed" &&
            (frappe.user.has_role("Vortex Admin") || frappe.user.has_role("Vortex Operations"))
        ) {
            frm.add_custom_button("Approve Payout", () => {
                frappe.confirm(
                    `Approve payout of <strong>$${(frm.doc.total_payout || 0).toFixed(2)}</strong> for ${frm.doc.streamer}?`
                    + (frm.doc.loan_deductions
                        ? `<br><br>Loan deduction of <strong>$${frm.doc.loan_deductions.toFixed(2)}</strong> will be recorded.`
                        : ""),
                    () => frm.call("approve_payout").then(() => frm.refresh())
                );
            }, "Actions");
        }

        // Export to ADP CSV
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
                        frm.doc.legal_name || "",
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

    // Live recalc when any earnings/deduction field changes
    gross_sales:            (frm) => _live_recalc(frm),
    profit_share_pct:       (frm) => _live_recalc(frm),
    package_count:          (frm) => _live_recalc(frm),
    package_rate:           (frm) => _live_recalc(frm),
    tips:                   (frm) => _live_recalc(frm),
    adjustments:            (frm) => _live_recalc(frm),
    owner_platform_fee_pct: (frm) => _live_recalc(frm),
    loan_deductions:        (frm) => _live_recalc(frm),
    payout_type:            (frm) => _live_recalc(frm),
});

function _live_recalc(frm) {
    const gross   = flt(frm.doc.gross_sales);
    const pct     = flt(frm.doc.profit_share_pct);
    const pkgs    = flt(frm.doc.package_count);
    const rate    = flt(frm.doc.package_rate);
    const tips    = flt(frm.doc.tips);
    const adj     = flt(frm.doc.adjustments);
    const fee_pct = flt(frm.doc.owner_platform_fee_pct);
    const loans   = flt(frm.doc.loan_deductions);

    const share_amt = frm.doc.payout_type === "Profit Share"
        ? Math.round(gross * pct / 100 * 100) / 100
        : 0;
    const pkg_pay  = Math.round(pkgs * rate * 100) / 100;
    const fee_amt  = Math.round(gross * fee_pct / 100 * 100) / 100;
    const net      = Math.round((share_amt + pkg_pay + tips + adj - fee_amt - loans) * 100) / 100;

    frm.set_value("profit_share_amount",      share_amt);
    frm.set_value("package_payout",           pkg_pay);
    frm.set_value("owner_platform_fee_amount", fee_amt);
    frm.set_value("total_payout",             net);

    _update_indicator(frm);
}

function _update_indicator(frm) {
    const total = frm.doc.total_payout || 0;
    frm.dashboard.set_headline_alert(
        `Net Payout: $${total.toFixed(2)}`,
        total >= 0 ? "green" : "red"
    );
}
