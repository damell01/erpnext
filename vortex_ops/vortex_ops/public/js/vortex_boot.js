/* ═══════════════════════════════════════════════════════════════════════════
   Vortex Ops — Boot Script
   Runs on every Frappe desk page load.  All brand values come from
   frappe.boot (populated by boot_session → Vortex Settings) so changing
   the brand name or color in the UI takes effect on next login — no deploy.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    /* ── Brand values from server (set in Vortex Settings) ─────────────────── */

    function _boot(key, fallback) {
        return (typeof frappe !== "undefined" && frappe.boot && frappe.boot[key]) || fallback;
    }

    const BRAND_NAME    = _boot("vortex_brand_name",    "VortexBreaks");
    const PRIMARY_COLOR = _boot("vortex_primary_color", "#E8630A");

    // Patterns to scrub — anything matching these gets replaced with BRAND_NAME
    const SCRUB_PATTERNS = [/ERPNext/gi, /Frappe/gi];

    /* ── Inject CSS custom properties ──────────────────────────────────────── */

    function _injectColors() {
        const hover = _darken(PRIMARY_COLOR, 15);
        const style = document.createElement("style");
        style.id = "vortex-brand-vars";
        style.textContent =
            ":root{" +
            "--vortex-primary:" + PRIMARY_COLOR + ";" +
            "--vortex-primary-hover:" + hover + ";" +
            "}";
        document.head.appendChild(style);
    }

    function _darken(hex, pct) {
        hex = hex.replace("#", "");
        if (hex.length === 3) { hex = hex.split("").map(c => c + c).join(""); }
        const amt = Math.round(255 * pct / 100);
        const r   = Math.max(0, parseInt(hex.slice(0, 2), 16) - amt);
        const g   = Math.max(0, parseInt(hex.slice(2, 4), 16) - amt);
        const b   = Math.max(0, parseInt(hex.slice(4, 6), 16) - amt);
        return "#" + [r, g, b].map(function (v) { return v.toString(16).padStart(2, "0"); }).join("");
    }

    _injectColors();

    /* ── Title sanitiser ────────────────────────────────────────────────────── */

    function _sanitiseTitle() {
        var raw   = document.title;
        var clean = raw;
        SCRUB_PATTERNS.forEach(function (rx) { clean = clean.replace(rx, BRAND_NAME); });
        if (clean !== raw) { document.title = clean; }
    }

    var titleEl = document.querySelector("title") || document.documentElement;
    new MutationObserver(_sanitiseTitle).observe(titleEl, {
        subtree: true, childList: true, characterData: true,
    });

    _sanitiseTitle();

    /* ── DOM text node scrubber ─────────────────────────────────────────────── */

    function _scrubNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            var val = node.nodeValue;
            var changed = false;
            SCRUB_PATTERNS.forEach(function (rx) {
                var next = val.replace(rx, BRAND_NAME);
                if (next !== val) { val = next; changed = true; }
            });
            if (changed) { node.nodeValue = val; }
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (!["SCRIPT", "STYLE", "INPUT", "TEXTAREA"].includes(node.tagName)) {
                node.childNodes.forEach(_scrubNode);
            }
        }
    }

    $(document).on("page-change", function () {
        requestAnimationFrame(function () { _scrubNode(document.body); });
    });

    var bodyObserver = new MutationObserver(function (mutations) {
        mutations.forEach(function (m) { m.addedNodes.forEach(_scrubNode); });
    });

    frappe.ready(function () {
        _scrubNode(document.body);
        bodyObserver.observe(document.body, { subtree: true, childList: true });
        _hideHelpLinks();
        _hideUpdateBanner();
    });

    /* ── Help menu — remove links to erpnext.com / frappe.io ───────────────── */

    function _hideHelpLinks() {
        var targets = [
            "erpnext.com", "frappe.io", "docs.erpnext",
            "discuss.frappe", "frappeframework",
        ];
        var attempts = 0;
        var poll = setInterval(function () {
            if (++attempts > 20) { clearInterval(poll); return; }
            document.querySelectorAll(".help-links a, .navbar-help a").forEach(function (a) {
                var href = (a.getAttribute("href") || "").toLowerCase();
                if (targets.some(function (t) { return href.includes(t); })) {
                    var li = a.closest("li");
                    if (li) { li.remove(); } else { a.remove(); }
                }
            });
        }, 300);
    }

    /* ── Update banner ──────────────────────────────────────────────────────── */

    function _hideUpdateBanner() {
        [".update-banner", ".frappe-update-message", '[class*="update-banner"]'].forEach(
            function (sel) {
                document.querySelectorAll(sel).forEach(function (el) { el.remove(); });
            }
        );
    }

}());
