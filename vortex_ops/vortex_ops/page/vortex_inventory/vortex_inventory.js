// Module-level state so action callbacks can refresh without re-building the page
let _state = null;

frappe.pages["vortex-inventory"].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent:        wrapper,
        title:         "Vortex Inventory",
        single_column: true,
    });

    page.add_menu_item("Full Inventory Report", () =>
        frappe.set_route("query-report", "Inventory by Streamer"));

    page.add_menu_item("Stock Ledger (ERPNext)", () =>
        frappe.set_route("query-report", "Stock Ledger"));

    page.add_inner_button("+ New Location", () => _create_location_dialog());
    page.add_inner_button("↺ Refresh",      () => _load());

    const $body = $(`
        <div class="vortex-inv-page" style="padding:20px;">
            <div class="vortex-inv-summary" style="margin-bottom:24px;"></div>
            <div class="vortex-inv-grid"></div>
        </div>
    `).appendTo($(wrapper).find(".page-content"));

    _state = { page, $body };
    _load();
};


function _load() {
    if (!_state) return;
    const { $body } = _state;
    $body.find(".vortex-inv-grid").html(
        `<div style="text-align:center;padding:40px;color:#9ca3af;">Loading…</div>`
    );
    frappe.call({
        method: "vortex_ops.vortex_ops.page.vortex_inventory.vortex_inventory.get_page_data",
        callback(r) {
            const locs = r.message || [];
            _render_summary($body.find(".vortex-inv-summary"), locs);
            _render_grid($body.find(".vortex-inv-grid"), locs);
        },
    });
}


function _render_summary($el, locs) {
    const total_value = locs.reduce((s, l) => s + (l.total_value || 0), 0);
    const total_skus  = locs.reduce((s, l) => s + (l.sku_count  || 0), 0);

    $el.html(`
        <div style="display:flex; gap:20px; flex-wrap:wrap;">
            ${_kpi("Locations",        locs.length,          "")}
            ${_kpi("Total SKUs",       total_skus,            "")}
            ${_kpi("Total Stock Value",_money(total_value),   "")}
        </div>
    `);
}


function _render_grid($el, locs) {
    if (!locs.length) {
        $el.html(`
            <div style="text-align:center; padding:60px; color:#6b7280;">
                <p style="font-size:16px;">No inventory locations yet.</p>
                <p>Create a Streamer and generate their warehouse, or add a standalone location above.</p>
            </div>
        `);
        return;
    }

    const cards = locs.map(loc => {
        const hasStock = loc.sku_count > 0;
        const border   = hasStock ? "#E8630A" : "#e5e7eb";
        const isStreamer = loc.label !== loc.warehouse;
        const wSafe    = _esc(loc.warehouse);
        const lSafe    = _esc(loc.label);

        return `
            <div style="border:1px solid ${border}; border-radius:8px;
                        padding:16px; background:#fff; display:flex;
                        flex-direction:column; justify-content:space-between;">

                <div style="display:flex; justify-content:space-between;
                            align-items:flex-start; margin-bottom:8px;">
                    <div style="cursor:pointer; flex:1;"
                         onclick="frappe.set_route('query-report','Inventory by Streamer',
                                  {warehouse:'${wSafe}'})">
                        <div style="font-weight:600; font-size:14px;">${lSafe}</div>
                        ${isStreamer
                            ? `<div style="font-size:11px;color:#6b7280;">${wSafe}</div>`
                            : ""}
                    </div>
                    <span style="font-size:10px; background:#f3f4f6;
                                 padding:2px 8px; border-radius:4px; color:#374151;
                                 white-space:nowrap; margin-left:8px;">
                        ${loc.wh_type || "Stores"}
                    </span>
                </div>

                <div style="display:flex; gap:20px; margin:8px 0 12px;">
                    <div>
                        <div style="font-size:22px; font-weight:700; color:#E8630A;">
                            ${loc.sku_count || 0}
                        </div>
                        <div style="font-size:11px; color:#6b7280;">SKUs</div>
                    </div>
                    <div>
                        <div style="font-size:22px; font-weight:700; color:#1B2A4A;">
                            ${_money(loc.total_value || 0)}
                        </div>
                        <div style="font-size:11px; color:#6b7280;">Stock Value</div>
                    </div>
                </div>

                <div style="display:flex; gap:6px; border-top:1px solid #f3f4f6;
                            padding-top:10px; flex-wrap:wrap;">
                    <button class="btn btn-xs btn-default"
                            onclick="_vortex_add_stock('${wSafe}','${lSafe}')">
                        + Add Stock
                    </button>
                    <button class="btn btn-xs btn-default"
                            onclick="_vortex_transfer_stock('${wSafe}','${lSafe}')">
                        Transfer In
                    </button>
                    <button class="btn btn-xs btn-default"
                            onclick="_vortex_adjust_stock('${wSafe}','${lSafe}')">
                        Adjust Qty
                    </button>
                    <button class="btn btn-xs btn-default"
                            onclick="frappe.set_route('query-report','Inventory by Streamer',
                                     {warehouse:'${wSafe}'})">
                        View Items
                    </button>
                </div>
            </div>
        `;
    });

    $el.html(`
        <div style="display:grid;
                    grid-template-columns:repeat(auto-fill, minmax(260px,1fr));
                    gap:16px;">
            ${cards.join("")}
        </div>
    `);
}


function _create_location_dialog() {
    const d = new frappe.ui.Dialog({
        title: "New Inventory Location",
        fields: [
            {
                fieldname:   "location_name",
                fieldtype:   "Data",
                label:       "Location Name",
                reqd:        1,
                description: 'e.g. "Back Room", "Storage Unit A", "Show Inventory"',
            },
            {
                fieldname: "warehouse_type",
                fieldtype: "Select",
                label:     "Type",
                options:   "Stores\nTransit",
                default:   "Stores",
            },
        ],
        primary_action_label: "Create Location",
        primary_action(values) {
            frappe.call({
                method: "vortex_ops.setup.inventory_setup.create_inventory_location",
                args: {
                    location_name:  values.location_name,
                    warehouse_type: values.warehouse_type,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({ message: `Created: ${r.message}`, indicator: "green" });
                        d.hide();
                        _load();
                    }
                },
            });
        },
    });
    d.show();
}


// ── KPI / formatting helpers ───────────────────────────────────────────────────

function _kpi(label, value) {
    return `
        <div style="background:#f9fafb; border-radius:8px; padding:16px 24px; min-width:140px;">
            <div style="font-size:24px; font-weight:700; color:#1B2A4A;">${value}</div>
            <div style="font-size:12px; color:#6b7280; margin-top:2px;">${label}</div>
        </div>
    `;
}

function _money(val) {
    return "$" + Number(val).toLocaleString("en-US", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });
}

function _esc(str) {
    return (str || "").replace(/'/g, "\\'").replace(/"/g, "&quot;");
}


// ── Global action handlers (called from inline onclick on cards) ───────────────

window._vortex_add_stock = function (warehouse, label) {
    const d = new frappe.ui.Dialog({
        title:  `Add Stock — ${label}`,
        fields: [
            {
                fieldname: "item_code", fieldtype: "Link", label: "Item",
                options: "Item", reqd: 1, filters: { is_stock_item: 1, disabled: 0 },
            },
            { fieldname: "qty",        fieldtype: "Float",    label: "Quantity",          reqd: 1, default: 1 },
            { fieldname: "basic_rate", fieldtype: "Currency", label: "Cost per Unit ($)",
              description: "Your purchase cost — used for COGS and profit calculations" },
            { fieldname: "remarks",    fieldtype: "Small Text", label: "Notes",
              default: `Stock received into ${label}` },
        ],
        primary_action_label: "Add to Inventory",
        primary_action(v) {
            frappe.call({
                method:   "vortex_ops.setup.inventory_setup.quick_stock_receipt",
                args:     { warehouse, item_code: v.item_code, qty: v.qty,
                            basic_rate: v.basic_rate || 0, remarks: v.remarks },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({ message: `Stock added. Entry: ${r.message}`, indicator: "green" });
                        d.hide();
                        _load();
                    }
                },
            });
        },
    });
    d.show();
};


window._vortex_transfer_stock = function (to_warehouse, label) {
    const d = new frappe.ui.Dialog({
        title:  `Transfer Stock Into — ${label}`,
        fields: [
            {
                fieldname:   "from_warehouse",
                fieldtype:   "Link",
                label:       "From Location",
                options:     "Warehouse",
                reqd:        1,
                description: "Where stock is coming from",
            },
            {
                fieldname: "item_code", fieldtype: "Link", label: "Item",
                options: "Item", reqd: 1, filters: { is_stock_item: 1, disabled: 0 },
            },
            { fieldname: "qty",     fieldtype: "Float",     label: "Quantity to Transfer", reqd: 1, default: 1 },
            { fieldname: "remarks", fieldtype: "Small Text", label: "Notes",
              default: `Transfer into ${label}` },
        ],
        primary_action_label: "Transfer",
        primary_action(v) {
            frappe.call({
                method: "vortex_ops.setup.inventory_setup.transfer_stock",
                args: {
                    from_warehouse: v.from_warehouse,
                    to_warehouse:   to_warehouse,
                    item_code:      v.item_code,
                    qty:            v.qty,
                    remarks:        v.remarks,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({ message: `Transferred. Entry: ${r.message}`, indicator: "green" });
                        d.hide();
                        _load();
                    }
                },
            });
        },
    });
    d.show();
};


window._vortex_adjust_stock = function (warehouse, label) {
    const d = new frappe.ui.Dialog({
        title:  `Adjust Stock — ${label}`,
        fields: [
            {
                fieldname: "item_code", fieldtype: "Link", label: "Item",
                options: "Item", reqd: 1, filters: { is_stock_item: 1, disabled: 0 },
            },
            {
                fieldname: "adjustment_type", fieldtype: "Select", label: "Adjustment Type",
                options: "Add (received / found)\nRemove (damaged / lost / correction)",
                reqd: 1, default: "Add (received / found)",
            },
            { fieldname: "qty",    fieldtype: "Float",      label: "Quantity", reqd: 1, default: 1 },
            { fieldname: "reason", fieldtype: "Small Text", label: "Reason",   reqd: 1,
              description: "Required for audit trail — e.g. 'Damaged in transit', 'Recount correction'" },
        ],
        primary_action_label: "Apply Adjustment",
        primary_action(v) {
            const is_add = v.adjustment_type.startsWith("Add");
            frappe.call({
                method:   "vortex_ops.setup.inventory_setup.adjust_stock",
                args: {
                    warehouse,
                    item_code:       v.item_code,
                    qty:             v.qty,
                    adjustment_type: is_add ? "receipt" : "issue",
                    reason:          v.reason,
                },
                callback(r) {
                    if (!r.exc) {
                        frappe.show_alert({ message: `Adjusted. Entry: ${r.message}`, indicator: "green" });
                        d.hide();
                        _load();
                    }
                },
            });
        },
    });
    d.show();
};
