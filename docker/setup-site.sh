#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Vortex Ops — First-Time Site Setup
#
# Run this ONCE inside the backend container after `docker compose up -d`.
#
#   docker compose exec backend bash /setup-site.sh
#
# Required env vars (set in .env):
#   SITE_NAME          e.g. vortexbreaks.local
#   ADMIN_PASSWORD     ERPNext Administrator password
#   DB_ROOT_PASSWORD   MariaDB root password
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SITE="${SITE_NAME:?Set SITE_NAME in .env}"
ADMIN_PW="${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in .env}"
DB_PW="${DB_ROOT_PASSWORD:?Set DB_ROOT_PASSWORD in .env}"

cd /home/frappe/frappe-bench

echo "▶ Creating site: $SITE"
bench new-site "$SITE" \
  --mariadb-root-password "$DB_PW" \
  --admin-password "$ADMIN_PW" \
  --no-mariadb-socket

echo "▶ Installing ERPNext"
bench --site "$SITE" install-app erpnext

echo "▶ Installing Vortex Ops"
bench --site "$SITE" install-app vortex_ops

echo "▶ Running migrations"
bench --site "$SITE" migrate

echo "▶ Seeding brand defaults (VortexBreaks)"
bench --site "$SITE" execute vortex_ops.vortex_ops.setup.brand_setup.run

echo "▶ Setting up inventory (UOMs, item groups, warehouses)"
bench --site "$SITE" execute vortex_ops.vortex_ops.setup.inventory_setup.run

echo "▶ Setting default site"
bench use "$SITE"

echo ""
echo "✅ Done. Open http://$SITE in your browser."
echo "   Login: Administrator / $ADMIN_PW"
echo ""
echo "   Next steps:"
echo "   1. Go to Settings → Vortex Settings and upload your logo"
echo "   2. Create your Company records (one per brand)"
echo "   3. Create Streamer records with pay configs"
echo "   4. Create Whatnot Channel records with credentials"
