/* ═══════════════════════════════════════════════════════════════════════════
   Vortex Ops — Boot Script
   Runs on every Frappe desk page load.  Scrubs ERPNext / Frappe branding
   from the DOM and the browser tab title without touching server config.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const BRAND_STRINGS = [/ERPNext/gi, /Frappe/gi];
    const APP_NAME      = "Vortex Ops";

    /* ── Title sanitiser ────────────────────────────────────────────────────── */

    function sanitiseTitle() {
        const raw = document.title;
        let clean = raw;
        BRAND_STRINGS.forEach(function (rx) { clean = clean.replace(rx, APP_NAME); });
        if (clean !== raw) { document.title = clean; }
    }

    // Watch for Frappe's router changing the title dynamically
    const titleObserver = new MutationObserver(sanitiseTitle);
    titleObserver.observe(document.querySelector("title") || document.documentElement, {
        subtree: true, childList: true, characterData: true,
    });

    sanitiseTitle(); // run once immediately on load

    /* ── DOM text node scrubber ─────────────────────────────────────────────── */

    function scrubNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            let val = node.nodeValue;
            let changed = false;
            BRAND_STRINGS.forEach(function (rx) {
                const next = val.replace(rx, APP_NAME);
                if (next !== val) { val = next; changed = true; }
            });
            if (changed) { node.nodeValue = val; }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            // skip script / style / input nodes — only visible text matters
            if (!["SCRIPT", "STYLE", "INPUT", "TEXTAREA"].includes(node.tagName)) {
                node.childNodes.forEach(scrubNode);
            }
        }
    }

    // Scrub after Frappe renders each page
    $(document).on("page-change", function () {
        requestAnimationFrame(function () { scrubNode(document.body); });
    });

    // Also observe for dynamically injected text (modals, toasts, etc.)
    const bodyObserver = new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            m.addedNodes.forEach(scrubNode);
        });
    });

    frappe.ready(function () {
        scrubNode(document.body);
        bodyObserver.observe(document.body, { subtree: true, childList: true });
        _hideHelpLinks();
        _hideUpdateBanner();
    });

    /* ── Help menu — remove links to erpnext.com / frappe.io ───────────────── */

    function _hideHelpLinks() {
        const targets = [
            "erpnext.com", "frappe.io", "docs.erpnext",
            "discuss.frappe", "frappeframework",
        ];

        // Frappe renders the help dropdown lazily; poll briefly for it
        let attempts = 0;
        const poll = setInterval(function () {
            if (++attempts > 20) { clearInterval(poll); return; }
            document.querySelectorAll(".help-links a, .navbar-help a").forEach(function (a) {
                const href = (a.getAttribute("href") || "").toLowerCase();
                if (targets.some(function (t) { return href.includes(t); })) {
                    const li = a.closest("li");
                    if (li) { li.remove(); } else { a.remove(); }
                }
            });
        }, 300);
    }

    /* ── Update banner ──────────────────────────────────────────────────────── */

    function _hideUpdateBanner() {
        [".update-banner", ".frappe-update-message", '[class*="update-banner"]'].forEach(function (sel) {
            document.querySelectorAll(sel).forEach(function (el) { el.remove(); });
        });
    }

}());
