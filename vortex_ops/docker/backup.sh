#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Vortex Ops — Backup Script
#
# Creates a full site backup (database + private files) and optionally
# uploads to an S3-compatible bucket (AWS S3, Backblaze B2, Cloudflare R2).
#
# Bare metal — add to cron (runs daily at 2am):
#   0 2 * * * /home/frappe/frappe-bench/apps/vortex_ops/docker/backup.sh >> /var/log/vortex-backup.log 2>&1
#
# Docker — called by the backup service in docker-compose.prod.yml.
#
# Required env:
#   SITE_NAME          Frappe site name (e.g. vortexbreaks.local)
#
# Optional env (for cloud upload):
#   BACKUP_S3_BUCKET   S3 bucket name  (e.g. my-vortex-backups)
#   BACKUP_S3_PREFIX   Path prefix     (default: vortex-backups)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
#   For Backblaze B2:  set AWS_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SITE="${SITE_NAME:?Set SITE_NAME}"
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"
PREFIX="${BACKUP_S3_PREFIX:-vortex-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[${TIMESTAMP}] ▶ Backing up site: ${SITE}"

cd "${BENCH_DIR}"

# Create compressed backup — stored in sites/<site>/private/backups/
bench --site "${SITE}" backup --with-files --compress

echo "[${TIMESTAMP}] ✓ Backup created in ${BENCH_DIR}/sites/${SITE}/private/backups/"

# ── Optional: upload to S3-compatible storage ─────────────────────────────────
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    BACKUP_DIR="${BENCH_DIR}/sites/${SITE}/private/backups"

    echo "[${TIMESTAMP}] ▶ Uploading to s3://${BACKUP_S3_BUCKET}/${PREFIX}/${SITE}/"

    # Requires awscli — installed in the container or available on the host
    aws s3 sync "${BACKUP_DIR}/" \
        "s3://${BACKUP_S3_BUCKET}/${PREFIX}/${SITE}/" \
        --storage-class STANDARD_IA \
        --exclude "*" \
        --include "*${TIMESTAMP:0:8}*"

    echo "[${TIMESTAMP}] ✓ Uploaded to cloud"

    # Keep only last 30 days locally to save disk space
    find "${BACKUP_DIR}" -name "*.gz" -mtime +30 -delete
    echo "[${TIMESTAMP}] ✓ Pruned local backups older than 30 days"
fi

echo "[${TIMESTAMP}] ✅ Done"
