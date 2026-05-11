frappe.ui.form.on("Vortex Settings", {
    refresh(frm) {
        frm.set_intro(
            "Changes here are pushed to System Settings immediately on save — " +
            "emails, the login page, and the app header will all update.",
            "blue"
        );

        frm.add_custom_button("Test Ollama Connection", () => {
            frappe.show_alert({ message: "Connecting to Ollama…", indicator: "blue" });
            frappe.call({
                method: "vortex_ops.vortex_ops.doctype.vortex_settings.vortex_settings.test_ollama_connection",
                callback(r) {
                    const res = r.message;
                    if (res.ok) {
                        const models = res.models.length
                            ? res.models.join(", ")
                            : "none downloaded yet";
                        frappe.show_alert({
                            message: `✓ Ollama connected. Available models: ${models}`,
                            indicator: "green",
                        });
                    } else {
                        frappe.show_alert({
                            message: `✗ Could not reach Ollama: ${res.error}`,
                            indicator: "red",
                        });
                    }
                },
            });
        }, "AI");
    },

    primary_color(frm) {
        if (frm.doc.primary_color) {
            document.documentElement.style.setProperty(
                "--vortex-primary", frm.doc.primary_color
            );
        }
    },
});
