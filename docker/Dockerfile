# ─────────────────────────────────────────────────────────────────────────────
# Vortex Ops — Custom ERPNext Image
#
# Extends the official frappe/erpnext image with the vortex_ops app
# pre-installed as a Python package.  Site creation and bench install-app
# happen at runtime via setup-site.sh (or your own orchestration).
#
# Build:
#   docker build -t vortex-ops:latest .
#
# Variables:
#   ERPNEXT_VERSION   frappe/erpnext tag to build on (default: v15.latest)
#   VORTEX_REPO       Git URL for the vortex_ops repo
#   VORTEX_BRANCH     Branch to pull (default: main)
# ─────────────────────────────────────────────────────────────────────────────

ARG ERPNEXT_VERSION=v15
FROM frappe/erpnext:${ERPNEXT_VERSION}

ARG VORTEX_REPO=https://github.com/damell01/erpnext.git
ARG VORTEX_BRANCH=main

# Install the vortex_ops Python package directly into the image.
# No bench commands here — bench is per-site; pip installs app code globally.
USER root
RUN pip install --no-cache-dir \
    "git+${VORTEX_REPO}@${VORTEX_BRANCH}#egg=vortex_ops"

# Drop back to the frappe user for all runtime operations
USER frappe
