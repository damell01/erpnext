# ─────────────────────────────────────────────────────────────────────────────
# Vortex Ops — Custom ERPNext Image
#
# Extends frappe/erpnext with:
#   - vortex_ops app (installed as a Python package)
#   - Playwright + Chromium (for Whatnot auto-scraper)
#
# Build:
#   docker build -t vortex-ops:latest .
#
# Build args:
#   ERPNEXT_VERSION   frappe/erpnext tag  (default: v15)
#   VORTEX_REPO       Git URL of the vortex_ops repo
#   VORTEX_BRANCH     Branch to use       (default: main)
# ─────────────────────────────────────────────────────────────────────────────

ARG ERPNEXT_VERSION=v15
FROM frappe/erpnext:${ERPNEXT_VERSION}

ARG VORTEX_REPO=https://github.com/damell01/erpnext.git
ARG VORTEX_BRANCH=main

USER root

# ── Install vortex_ops Python package ────────────────────────────────────────
RUN pip install --no-cache-dir \
    "git+${VORTEX_REPO}@${VORTEX_BRANCH}#egg=vortex_ops"

# ── Install Playwright + Chromium for Whatnot scraper ────────────────────────
# --with-deps installs all required system libraries automatically.
# This adds ~400 MB but makes the Whatnot auto-scrape work out of the box.
RUN pip install --no-cache-dir playwright \
 && playwright install chromium --with-deps \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER frappe
