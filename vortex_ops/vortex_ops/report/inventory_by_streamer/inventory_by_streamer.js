frappe.query_reports["Inventory by Streamer"] = {
    filters: [
        {
            fieldname: "warehouse",
            fieldtype: "Link",
            label:     "Location / Warehouse",
            options:   "Warehouse",
        },
        {
            fieldname: "streamer",
            fieldtype: "Link",
            label:     "Streamer",
            options:   "Streamer",
            // Clearing warehouse when streamer is picked keeps filters consistent
            onchange() {
                if (this.value) {
                    frappe.query_report.set_filter_value("warehouse", "");
                }
            },
        },
        {
            fieldname: "item_group",
            fieldtype: "Link",
            label:     "Category",
            options:   "Item Group",
        },
        {
            fieldname: "include_zero_stock",
            fieldtype: "Check",
            label:     "Include Zero Stock",
            default:   0,
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // Bold the subtotal and grand total rows
        if (data._is_subtotal || data._is_total) {
            value = `<strong>${value}</strong>`;
        }

        // Orange text for LOW STOCK alert column
        if (column.fieldname === "alert" && data.alert === "LOW STOCK") {
            value = `<span style="color:#E8630A; font-weight:600;">⚠ LOW STOCK</span>`;
        }

        // Light orange row background for low-stock items
        if (data.alert === "LOW STOCK" && !data._is_subtotal && !data._is_total) {
            value = `<span style="background:#fff7ed; padding:2px 4px; border-radius:3px;">${value}</span>`;
        }

        return value;
    },
};
