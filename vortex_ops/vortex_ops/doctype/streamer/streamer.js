frappe.ui.form.on("Streamer", {
    refresh(frm) {
        frm.trigger("payout_type");

        if (!frm.is_new()) {
            // ── Warehouse ────────────────────────────────────────────────────
            if (!frm.doc.warehouse) {
                frm.dashboard.add_indicator("No Warehouse Assigned", "red");
                frm.add_custom_button("Create Warehouse", () => {
                    frappe.confirm(
                        `Create warehouse "${frm.doc.streamer_name} Inventory" for this streamer?`,
                        () => frm.call("create_warehouse").then(r => {
                            frappe.show_alert({
                                message: `Warehouse created: ${r.message}`,
                                indicator: "green",
                            });
                            frm.reload_doc();
                        })
                    );
                }, "Inventory");
            } else {
                frm.dashboard.add_indicator("Warehouse: " + frm.doc.warehouse, "green");

                // ── Stock summary badge ──────────────────────────────────────
                frm.call("get_inventory_summary").then(r => {
                    const s = r.message;
                    if (s && s.total_items > 0) {
                        frm.dashboard.add_indicator(
                            `${s.total_items} SKU(s) · $${(s.total_value || 0).toFixed(2)}`,
                            "blue"
                        );
                    } else {
                        frm.dashboard.add_indicator("No stock on hand", "gray");
                    }
                });

                // ── Quick Stock Receipt button ────────────────────────────────
                frm.add_custom_button("Add Stock (Receipt)", () => {
                    _open_stock_receipt_dialog(frm);
                }, "Inventory");

                // ── View full inventory ──────────────────────────────────────
                frm.add_custom_button("View Inventory", () =>
                    frappe.set_route("query-report", "Inventory by Streamer",
                        { streamer: frm.doc.name }), "Inventory");

                // ── ERPNext stock ledger for this warehouse ───────────────────
                frm.add_custom_button("Stock Ledger", () =>
                    frappe.set_route("query-report", "Stock Ledger",
                        { warehouse: frm.doc.warehouse }), "Inventory");
            }

            // ── Reports ──────────────────────────────────────────────────────
            frm.add_custom_button("Payout History", () =>
                frappe.set_route("List", "Streamer Payout",
                    { streamer: frm.doc.name }), "Reports");

            // ── Loan balance indicator ────────────────────────────────────────
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
    },
});


function _open_stock_receipt_dialog(frm) {
    /*
     * Opens a dialog that creates an ERPNext Stock Entry (Material Receipt)
     * directly into this streamer's warehouse.
     * ERPNext handles all the ledger entries — we just provide the UI shortcut.
     */
    const d = new frappe.ui.Dialog({
        title: `Add Stock to ${frm.doc.streamer_name}`,
        fields: [
            {
                fieldname:  "item_code",
                fieldtype:  "Link",
                label:      "Item",
                options:    "Item",
                reqd:       1,
                filters:    { is_stock_item: 1, disabled: 0 },
            },
            {
                fieldname:  "qty",
                fieldtype:  "Float",
                label:      "Quantity",
                reqd:       1,
                default:    1,
            },
            {
                fieldname:  "basic_rate",
                fieldtype:  "Currency",
                label:      "Cost per Unit ($)",
                description: "Your cost — used for COGS and profit calculations",
            },
            {
                fieldname:  "remarks",
                fieldtype:  "Small Text",
                label:      "Notes",
                default:    `Opening stock for ${frm.doc.streamer_name}`,
            },
        ],
        primary_action_label: "Add to Inventory",
        primary_action(values) {
            frappe.call({
                method: "vortex_ops.setup.inventory_setup.quick_stock_receipt",
                args: {
                    warehouse:  frm.doc.warehouse,
                    item_code:  values.item_code,
                    qty:        values.qty,
                    basic_rate: values.basic_rate || 0,
                    remarks:    values.remarks,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: `Stock added. Entry: ${r.message}`,
                            indicator: "green",
                        });
                        d.hide();
                        frm.reload_doc();
                    }
                },
            });
        },
    });
    d.show();
}
