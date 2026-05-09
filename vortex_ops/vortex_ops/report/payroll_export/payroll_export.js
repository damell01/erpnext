frappe.query_reports["Payroll Export"] = {
    filters: [
        {
            fieldname: "payout_period",
            fieldtype: "Link",
            label:     "Payout Period",
            options:   "Payout Period",
            reqd:      1,
        },
        {
            fieldname: "include_draft",
            fieldtype: "Check",
            label:     "Include Draft Payouts",
            default:   0,
        },
    ],

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        if (data._is_total) {
            value = `<strong>${value}</strong>`;
        }

        // Highlight negative net payout in red
        if (column.fieldname === "total_payout" && data.total_payout < 0) {
            value = `<span style="color:red;">${value}</span>`;
        }

        // Highlight status
        if (column.fieldname === "status") {
            const colours = {
                "Draft":    "#6b7280",
                "Reviewed": "#2563eb",
                "Approved": "#16a34a",
                "Exported": "#7c3aed",
            };
            const c = colours[data.status];
            if (c) value = `<span style="color:${c}; font-weight:600;">${data.status}</span>`;
        }

        return value;
    },
};
