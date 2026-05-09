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

                // ── Adjust qty (correction / damage / found stock) ────────────
                frm.add_custom_button("Adjust Stock", () => {
                    _open_adjust_dialog(frm);
                }, "Inventory");

                // ── Transfer from another warehouse ──────────────────────────
                frm.add_custom_button("Transfer Stock In", () => {
                    _open_transfer_dialog(frm);
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
    const d = new frappe.ui.Dialog({
        title: `Add Stock to ${frm.doc.streamer_name}`,
        fields: [
            {
                fieldname: "item_code",
                fieldtype: "Link",
                label:     "Item",
                options:   "Item",
                reqd:      1,
                filters:   { is_stock_item: 1, disabled: 0 },
                onchange() {
                    const item = d.get_value("item_code");
                    if (!item || !frm.doc.warehouse) { d.set_value("current_qty", 0); return; }
                    frappe.call({
                        method:   "vortex_ops.setup.inventory_setup.get_bin_qty",
                        args:     { warehouse: frm.doc.warehouse, item_code: item },
                        callback(r) {
                            d.set_value("current_qty", r.message ? r.message.actual_qty : 0);
                        },
                    });
                },
            },
            {
                fieldname: "current_qty",
                fieldtype: "Float",
                label:     "Already in Stock",
                read_only: 1,
            },
            {
                fieldname: "qty",
                fieldtype: "Float",
                label:     "Quantity to Add",
                reqd:      1,
                default:   1,
            },
            {
                fieldname:   "basic_rate",
                fieldtype:   "Currency",
                label:       "Cost per Unit ($)",
                description: "Your cost — used for COGS and profit calculations",
            },
            {
                fieldname: "remarks",
                fieldtype: "Small Text",
                label:     "Notes",
                default:   `Stock received for ${frm.doc.streamer_name}`,
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


function _open_adjust_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: `Adjust Stock — ${frm.doc.streamer_name}`,
        fields: [
            {
                fieldname: "item_code",
                fieldtype: "Link",
                label:     "Item",
                options:   "Item",
                reqd:      1,
                filters:   { is_stock_item: 1, disabled: 0 },
                onchange() {
                    const item = d.get_value("item_code");
                    if (!item || !frm.doc.warehouse) { d.set_value("current_qty", 0); return; }
                    frappe.call({
                        method:   "vortex_ops.setup.inventory_setup.get_bin_qty",
                        args:     { warehouse: frm.doc.warehouse, item_code: item },
                        callback(r) {
                            d.set_value("current_qty", r.message ? r.message.actual_qty : 0);
                        },
                    });
                },
            },
            {
                fieldname: "current_qty",
                fieldtype: "Float",
                label:     "Currently in Stock",
                read_only: 1,
            },
            {
                fieldname: "adjustment_type",
                fieldtype: "Select",
                label:     "Adjustment Type",
                options:   "Add (received / found)\nRemove (damaged / lost / correction)",
                reqd:      1,
                default:   "Add (received / found)",
            },
            { fieldname: "qty",    fieldtype: "Float",      label: "Quantity", reqd: 1, default: 1 },
            { fieldname: "reason", fieldtype: "Small Text", label: "Reason",   reqd: 1,
              description: "Required — e.g. 'Damaged in transit', 'Recount correction'" },
        ],
        primary_action_label: "Apply Adjustment",
        primary_action(values) {
            const is_add = values.adjustment_type.startsWith("Add");
            frappe.call({
                method: "vortex_ops.setup.inventory_setup.adjust_stock",
                args: {
                    warehouse:       frm.doc.warehouse,
                    item_code:       values.item_code,
                    qty:             values.qty,
                    adjustment_type: is_add ? "receipt" : "issue",
                    reason:          values.reason,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message:   `Adjusted. Entry: ${r.message}`,
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


function _open_transfer_dialog(frm) {
    /*
     * Transfer stock FROM another warehouse (e.g. Main Storage) INTO this
     * streamer's warehouse. Uses ERPNext Material Transfer — no custom logic.
     * Common workflow: bulk shipment arrives in Main Storage, then gets split
     * to each streamer's personal warehouse.
     */
    const d = new frappe.ui.Dialog({
        title: `Transfer Stock into ${frm.doc.streamer_name}`,
        fields: [
            {
                fieldname:   "from_warehouse",
                fieldtype:   "Link",
                label:       "From Warehouse",
                options:     "Warehouse",
                reqd:        1,
                description: "Where stock is coming from — another streamer's warehouse or any holding location",
            },
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
                label:      "Quantity to Transfer",
                reqd:       1,
                default:    1,
            },
            {
                fieldname:  "remarks",
                fieldtype:  "Small Text",
                label:      "Notes",
                default:    `Transfer to ${frm.doc.streamer_name}`,
            },
        ],
        primary_action_label: "Transfer",
        primary_action(values) {
            frappe.call({
                method: "vortex_ops.setup.inventory_setup.transfer_stock",
                args: {
                    from_warehouse: values.from_warehouse,
                    to_warehouse:   frm.doc.warehouse,
                    item_code:      values.item_code,
                    qty:            values.qty,
                    remarks:        values.remarks,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: `Transferred. Entry: ${r.message}`,
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
