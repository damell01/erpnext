frappe.ui.form.on("Vortex Settings", {
    refresh(frm) {
        frm.set_intro(
            "Changes here are pushed to System Settings immediately on save — " +
            "emails, the login page, and the app header will all update.",
            "blue"
        );
    },

    primary_color(frm) {
        if (frm.doc.primary_color) {
            // Live preview: inject the new color into the current session
            document.documentElement.style.setProperty(
                "--vortex-primary", frm.doc.primary_color
            );
        }
    },
});
