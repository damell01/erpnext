#!/usr/bin/env bash
# ==============================================================================
# install.sh — One-shot Vortex Ops installer for a fresh Ubuntu 22.04 VPS
#
# Usage:
#   sudo bash install.sh
#
# Or run directly from GitHub:
#   curl -fsSL https://raw.githubusercontent.com/damell01/erpnext/main/scripts/install.sh | sudo bash
#
# What it installs:
#   MariaDB · Redis · nginx · Supervisor · Python env · frappe-bench
#   ERPNext v15 · Vortex Ops · Let's Encrypt SSL (optional)
# ==============================================================================

set -euo pipefail
SECONDS=0

# ── Colours ───────────────────────────────────────────────────────────────
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' BOLD='\033[1m' NC='\033[0m'
info()   { echo -e "${B}▶${NC}  $*"; }
ok()     { echo -e "${G}✓${NC}  $*"; }
warn()   { echo -e "${Y}⚠${NC}  $*"; }
die()    { echo -e "${R}✗${NC}  $*" >&2; exit 1; }
phase()  { echo -e "\n${BOLD}━━━  $*  ━━━${NC}"; }
banner() {
  echo ""
  echo -e "${BOLD}╔═════════════════════════════════════════════════════╗${NC}"
  echo -e "${BOLD}║  $*${NC}"
  echo -e "${BOLD}╚═════════════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Defaults ──────────────────────────────────────────────────────────────
VORTEX_REPO="${VORTEX_REPO:-https://github.com/damell01/erpnext}"
VORTEX_BRANCH="${VORTEX_BRANCH:-main}"
ERPNEXT_BRANCH="version-15"
BENCH_USER="frappe"
BENCH_DIR="/home/${BENCH_USER}/frappe-bench"

# ── Pre-flight ───────────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && die "Run with sudo:  sudo bash $0"

OS_ID=$(. /etc/os-release && echo "$ID")
OS_VER=$(. /etc/os-release && echo "$VERSION_ID")
[[ "$OS_ID" != "ubuntu" ]] && warn "Tested on Ubuntu 22.04. You are on ${OS_ID} ${OS_VER}."

command -v curl &>/dev/null || apt-get install -y -qq curl
command -v dig  &>/dev/null || apt-get install -y -qq dnsutils

# ── Input wizard ────────────────────────────────────────────────────────
banner "Vortex Ops — Installation Wizard"
echo "  Answer the prompts below. Press Enter to accept [defaults]."
echo "  All values stay on this server — nothing is sent anywhere."
echo ""

# Domain
while true; do
  read -rp "  $(echo -e "${BOLD}Site domain${NC}") (e.g. app.vortexbreaks.com): " SITE_NAME
  [[ -n "$SITE_NAME" ]] && break
  warn "Domain is required."
done

# Admin password
while true; do
  read -rsp "  $(echo -e "${BOLD}Admin password${NC}") for the desk login (min 8 chars): " ADMIN_PW; echo
  [[ ${#ADMIN_PW} -ge 8 ]] && break
  warn "Must be at least 8 characters."
done

# DB root password
while true; do
  read -rsp "  $(echo -e "${BOLD}MariaDB root password${NC}") (new password for this server): " DB_ROOT_PW; echo
  [[ ${#DB_ROOT_PW} -ge 8 ]] && break
  warn "Must be at least 8 characters."
done

# Brand name
read -rp "  $(echo -e "${BOLD}Brand name${NC}") [VortexBreaks]: " BRAND_NAME
BRAND_NAME="${BRAND_NAME:-VortexBreaks}"

# SSL
echo ""
echo "  SSL requires your domain's DNS A record to already point to this server."
SERVER_IP=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || echo "unknown")
echo "  This server's public IP: ${SERVER_IP}"
read -rp "  $(echo -e "${BOLD}Set up SSL now?${NC}") (y/N): " DO_SSL
DO_SSL="${DO_SSL,,}"
SSL_EMAIL=""
if [[ "$DO_SSL" == "y" ]]; then
  read -rp "  Email for SSL cert expiry alerts: " SSL_EMAIL
  [[ -z "$SSL_EMAIL" ]] && die "Email is required for SSL."
fi

# ── Confirm ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Summary of what will be installed:${NC}"
echo ""
echo "    Domain      :  ${SITE_NAME}"
echo "    Brand name  :  ${BRAND_NAME}"
echo "    Bench dir   :  ${BENCH_DIR}"
echo "    ERPNext     :  v15"
echo "    Vortex Ops  :  ${VORTEX_REPO} @ ${VORTEX_BRANCH}"
echo "    SSL         :  $( [[ "$DO_SSL" == "y" ]] && echo "Yes — ${SSL_EMAIL}" || echo "No (run later with: sudo bash scripts/setup-nginx-ssl.sh)" )"
echo ""
read -rp "  $(echo -e "${BOLD}Proceed?${NC}") (y/N): " CONFIRM
[[ "${CONFIRM,,}" != "y" ]] && { echo "Aborted."; exit 0; }

# ── Logging ───────────────────────────────────────────────────────────────
LOG_FILE="/var/log/vortex-install-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
info "Full log at: ${LOG_FILE}"

# ── Helper: run bench as frappe user ────────────────────────────────────────────
bench_as_frappe() {
  sudo -H -u "$BENCH_USER" bash -c "cd ${BENCH_DIR} && $*"
}

# ══════════════════════════════════════════════════════════════════════════════
phase "1/9 — System packages"
# ══════════════════════════════════════════════════════════════════════════════

info "Updating package lists..."
apt-get update -qq

info "Installing dependencies (MariaDB, Redis, nginx, Python, etc.)..."
DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
  git curl wget gnupg2 \
  python3-dev python3-pip python3-venv python3-setuptools \
  build-essential libssl-dev libffi-dev \
  mariadb-server mariadb-client \
  redis-server \
  nginx supervisor \
  wkhtmltopdf \
  dnsutils ufw \
  xvfb libfontconfig

ok "System packages installed."

# ══════════════════════════════════════════════════════════════════════════════
phase "2/9 — MariaDB"
# ══════════════════════════════════════════════════════════════════════════════

info "Starting MariaDB..."
systemctl enable --now mariadb

info "Securing MariaDB and setting root password..."
# Uses unix_socket auth (available as OS root) for initial setup
mysql -u root << EOSQL
SET PASSWORD FOR 'root'@'localhost' = PASSWORD('${DB_ROOT_PW}');
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
EOSQL

info "Setting utf8mb4 character set..."
# Append only if not already present
grep -q "character-set-server = utf8mb4" /etc/mysql/mariadb.conf.d/50-server.cnf 2>/dev/null || \
cat >> /etc/mysql/mariadb.conf.d/50-server.cnf << 'EOCNF'

[mysqld]
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci
EOCNF

systemctl restart mariadb
ok "MariaDB ready."

# ══════════════════════════════════════════════════════════════════════════════
phase "3/9 — frappe system user"
# ══════════════════════════════════════════════════════════════════════════════

if id "$BENCH_USER" &>/dev/null; then
  ok "User '${BENCH_USER}' already exists."
else
  info "Creating user '${BENCH_USER}'..."
  useradd -m -s /bin/bash "$BENCH_USER"
  echo "${BENCH_USER}:$(openssl rand -base64 18)" | chpasswd
  usermod -aG sudo "$BENCH_USER"
  # Passwordless sudo needed for bench setup production / nginx
  echo "${BENCH_USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/frappe-bench
  ok "User '${BENCH_USER}' created."
fi

# ══════════════════════════════════════════════════════════════════════════════
phase "4/9 — bench init"
# ══════════════════════════════════════════════════════════════════════════════

info "Installing frappe-bench..."
pip3 install -q frappe-bench

if [[ -d "$BENCH_DIR" ]]; then
  ok "Bench already exists at ${BENCH_DIR}."
else
  info "Initialising bench — clones Frappe v15 (3–5 min)..."
  sudo -H -u "$BENCH_USER" \
    bench init --frappe-branch version-15 --verbose "$BENCH_DIR"
  ok "Bench initialised."
fi

# ══════════════════════════════════════════════════════════════════════════════
phase "5/9 — Download apps"
# ══════════════════════════════════════════════════════════════════════════════

if [[ -d "${BENCH_DIR}/apps/erpnext" ]]; then
  ok "ERPNext already downloaded."
else
  info "Downloading ERPNext v15 (2–4 min)..."
  bench_as_frappe "bench get-app --branch ${ERPNEXT_BRANCH} erpnext"
  ok "ERPNext downloaded."
fi

if [[ -d "${BENCH_DIR}/apps/vortex_ops" ]]; then
  ok "Vortex Ops already downloaded."
else
  info "Downloading Vortex Ops..."
  bench_as_frappe "bench get-app vortex_ops ${VORTEX_REPO} --branch ${VORTEX_BRANCH}"
  ok "Vortex Ops downloaded."
fi

# ══════════════════════════════════════════════════════════════════════════════
phase "6/9 — Create site & install apps"
# ══════════════════════════════════════════════════════════════════════════════

if [[ -d "${BENCH_DIR}/sites/${SITE_NAME}" ]]; then
  ok "Site '${SITE_NAME}' already exists."
else
  info "Creating site '${SITE_NAME}'..."
  bench_as_frappe "bench new-site '${SITE_NAME}' \
    --mariadb-root-password '${DB_ROOT_PW}' \
    --admin-password '${ADMIN_PW}' \
    --no-mariadb-socket"
  ok "Site created."
fi

info "Installing ERPNext on site..."
bench_as_frappe "bench --site '${SITE_NAME}' install-app erpnext 2>&1 | tail -5" \
  || warn "ERPNext may already be installed — continuing."

info "Installing Vortex Ops on site..."
bench_as_frappe "bench --site '${SITE_NAME}' install-app vortex_ops 2>&1 | tail -5" \
  || warn "vortex_ops may already be installed — continuing."

info "Running database migrations..."
bench_as_frappe "bench --site '${SITE_NAME}' migrate"

info "Setting brand name to '${BRAND_NAME}'..."
bench_as_frappe "bench --site '${SITE_NAME}' execute vortex_ops.setup.brand_setup.run \
  --args '[\"${BRAND_NAME}\"]'" 2>/dev/null \
  || warn "Brand setup skipped (will use default — change in Vortex Settings)."

bench_as_frappe "bench use '${SITE_NAME}'"
ok "Apps installed and site ready."

# ══════════════════════════════════════════════════════════════════════════════
phase "7/9 — Production mode + nginx"
# ══════════════════════════════════════════════════════════════════════════════

info "Enabling production mode (Supervisor + gunicorn workers)..."
cd "$BENCH_DIR" && bench setup production "$BENCH_USER" --yes 2>&1 | tail -5

info "Generating nginx config..."
cd "$BENCH_DIR" && bench setup nginx --yes 2>&1 | tail -3

info "Opening firewall ports..."
ufw allow 22/tcp  comment 'SSH'   2>/dev/null || true
ufw allow 80/tcp  comment 'HTTP'  2>/dev/null || true
ufw allow 443/tcp comment 'HTTPS' 2>/dev/null || true
ufw --force enable 2>/dev/null || true

nginx -t && systemctl reload nginx
ok "nginx is live on port 80."

# ══════════════════════════════════════════════════════════════════════════════
phase "8/9 — SSL (Let's Encrypt)"
# ══════════════════════════════════════════════════════════════════════════════

DNS_IP=""
if [[ "$DO_SSL" == "y" ]]; then
  info "Installing certbot..."
  apt-get install -y -q certbot python3-certbot-nginx

  DNS_IP=$(dig +short "$SITE_NAME" A | tail -1)
  if [[ -z "$DNS_IP" || "$DNS_IP" != "$SERVER_IP" ]]; then
    warn "DNS for ${SITE_NAME} resolves to '${DNS_IP:-none}' — this server is '${SERVER_IP}'."
    warn "SSL skipped. Once DNS propagates, run:"
    warn "  sudo certbot --nginx --non-interactive --agree-tos --email ${SSL_EMAIL} --redirect -d ${SITE_NAME}"
  else
    info "Obtaining certificate for ${SITE_NAME}..."
    certbot --nginx \
      --non-interactive --agree-tos \
      --email "$SSL_EMAIL" \
      --redirect \
      -d "$SITE_NAME"
    nginx -t && systemctl reload nginx
    ok "SSL live — site accessible at https://${SITE_NAME}"
  fi
else
  echo "  Skipped. Run when DNS is ready:"
  echo "    sudo bash ${BENCH_DIR}/apps/vortex_ops/scripts/setup-nginx-ssl.sh ${SITE_NAME} YOUR_EMAIL"
fi

# ══════════════════════════════════════════════════════════════════════════════
phase "9/9 — Verify"
# ══════════════════════════════════════════════════════════════════════════════

info "Checking services..."
supervisorctl status 2>/dev/null | grep -E "frappe|RUNNING|STOPPED" || true

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://${SITE_NAME}" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" =~ ^(200|301|302)$ ]]; then
  ok "Site responding (HTTP ${HTTP_CODE})."
else
  warn "Site returned HTTP ${HTTP_CODE}. Check: tail -50 ${BENCH_DIR}/logs/web.error.log"
fi

ELAPSED=$(( SECONDS / 60 ))

# ── Final summary ─────────────────────────────────────────────────────────────────
PROTO=$( [[ "$DO_SSL" == "y" && "$DNS_IP" == "$SERVER_IP" ]] && echo "https" || echo "http" )

banner "✅  Vortex Ops installed in ~${ELAPSED} minutes"
echo -e "  ${BOLD}URL        :${NC}  ${PROTO}://${SITE_NAME}"
echo -e "  ${BOLD}Username   :${NC}  Administrator"
echo -e "  ${BOLD}Password   :${NC}  ${ADMIN_PW}"
echo -e "  ${BOLD}Log file   :${NC}  ${LOG_FILE}"
echo ""
echo "  First steps in the desk:"
echo "    1.  Settings → Vortex Settings    — upload logo, check brand name/color"
echo "    2.  Settings → Email Account      — configure SMTP for outbound mail"
echo "    3.  Settings → AI Settings        — enter Ollama URL / model (or install Ollama below)"
echo "    4.  Vortex Ops → Whatnot Channel  — add Whatnot credentials"
echo "    5.  Vortex Ops → Streamer         — add your streamers"
echo ""
echo "  Optional extras:"
echo "    # Install Ollama for AI features:"
echo "    curl -fsSL https://ollama.com/install.sh | sh && ollama pull llama3.1:8b"
echo ""
echo "    # Install Playwright for Whatnot auto-scraping:"
echo "    pip install playwright && playwright install chromium"
echo ""
if [[ "$DO_SSL" != "y" || "$DNS_IP" != "$SERVER_IP" ]]; then
echo "    # Add SSL once DNS is pointed at this server (${SERVER_IP}):"
echo "    sudo bash ${BENCH_DIR}/apps/vortex_ops/scripts/setup-nginx-ssl.sh ${SITE_NAME} YOUR_EMAIL"
echo ""
fi
echo "  Useful bench commands (run from ${BENCH_DIR} as user ${BENCH_USER}):"
echo "    bench restart                           restart all services"
echo "    bench --site ${SITE_NAME} migrate        run after app updates"
echo "    bench --site ${SITE_NAME} clear-cache    clear if desk looks stale"
echo "    bench logs                              tail live logs"
echo ""
echo -e "  ${G}Full docs:${NC} ${VORTEX_REPO}/blob/${VORTEX_BRANCH}/INSTALL.md"
echo "══════════════════════════════════════════════════════════════"
