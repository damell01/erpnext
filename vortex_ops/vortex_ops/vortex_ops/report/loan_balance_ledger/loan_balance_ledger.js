frappe.query_reports["Loan Balance Ledger"] = {
    filters: [
        {
            fieldname: "streamer",
            fieldtype: "Link",
            label:     "Streamer",
            options:   "Streamer",
        },
        {
            fieldname: "status",
            fieldtype: "Select",
            label:     "Status",
            options:   "\nActive\nPaid Off\nForgiven\nOn Hold\nCancelled",
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (data._is_total) {
            value = `<strong>${value}</strong>`;
        }

        if (column.fieldname === "status" && data.status) {
            const colors = {
                "Active":    "#16a34a",
                "Paid Off":  "#6b7280",
                "Forgiven":  "#9333ea",
                "On Hold":   "#d97706",
                "Cancelled": "#dc2626",
            };
            const c = colors[data.status];
            if (c) return `<span style="color:${c}; font-weight:600;">${data.status}</span>`;
        }

        // Highlight outstanding balance in amber
        if (column.fieldname === "balance" && (data.balance || 0) > 0) {
            return `<span style="color:#d97706; font-weight:600;">${value}</span>`;
        }

        return value;
    },
};
