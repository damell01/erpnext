#!/usr/bin/env bash
# setup-nginx-ssl.sh
# Configures nginx + Let's Encrypt SSL for a Frappe/ERPNext site on a subdomain.
#
# Usage (run as root or with sudo):
#   sudo bash setup-nginx-ssl.sh <domain> <email> [bench-user] [bench-dir]
#
# Examples:
#   sudo bash setup-nginx-ssl.sh app.vortexbreaks.com admin@vortexbreaks.com
#   sudo bash setup-nginx-ssl.sh app.vortexbreaks.com admin@vortexbreaks.com frappe /home/frappe/frappe-bench
#
# What this script does:
#   1. Validates DNS resolves to this server's public IP
#   2. Installs certbot + nginx plugin if missing
#   3. Opens firewall ports 80 and 443
#   4. Runs bench setup nginx to generate the nginx config for your site
#   5. Tests the nginx config
#   6. Obtains a Let's Encrypt certificate via certbot --nginx
#   7. Reloads nginx
#   8. Verifies the certificate and tests auto-renewal
#   9. Prints final confirmation

set -euo pipefail

# ── Arguments ────────────────────────────────────────────────────────────────
DOMAIN="${1:-}"
EMAIL="${2:-}"
BENCH_USER="${3:-frappe}"
BENCH_DIR="${4:-/home/${BENCH_USER}/frappe-bench}"

if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
  echo "Usage: sudo bash $0 <domain> <email> [bench-user] [bench-dir]"
  echo "  domain     e.g.  app.vortexbreaks.com"
  echo "  email      e.g.  admin@vortexbreaks.com  (used for cert expiry alerts)"
  echo "  bench-user default: frappe"
  echo "  bench-dir  default: /home/<bench-user>/frappe-bench"
  exit 1
fi

# ── Must run as root ──────────────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: Run this script with sudo or as root."
  exit 1
fi

BENCH_CMD="sudo -u ${BENCH_USER} bash -c 'cd ${BENCH_DIR} && bench"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Vortex Ops — nginx + SSL setup"
echo "  Domain : $DOMAIN"
echo "  Email  : $EMAIL"
echo "  Bench  : $BENCH_DIR (user: $BENCH_USER)"
echo "══════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Verify DNS ────────────────────────────────────────────────────────
echo "▶ Step 1/8 — Checking DNS for $DOMAIN ..."

# Get the server's public IP (tries two services)
SERVER_IP=$(curl -s --max-time 5 https://api.ipify.org || curl -s --max-time 5 https://ifconfig.me || echo "")
DNS_IP=$(dig +short "$DOMAIN" A | tail -1)

echo "  Server public IP : ${SERVER_IP:-unknown}"
echo "  DNS A record     : ${DNS_IP:-not found}"

if [[ -z "$DNS_IP" ]]; then
  echo ""
  echo "  WARNING: No A record found for $DOMAIN."
  echo "  Make sure you've added an A record:"
  echo "    Type: A"
  echo "    Name: $(echo "$DOMAIN" | cut -d. -f1)"
  echo "    Value: <your server IP>"
  echo "    TTL: 300"
  echo ""
  read -rp "  DNS not confirmed — continue anyway? (y/N): " CONTINUE_DNS
  [[ "$CONTINUE_DNS" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
elif [[ -n "$SERVER_IP" && "$DNS_IP" != "$SERVER_IP" ]]; then
  echo ""
  echo "  WARNING: DNS resolves to $DNS_IP but this server's IP is $SERVER_IP."
  echo "  Certbot will FAIL if DNS does not point to this server."
  echo ""
  read -rp "  IPs don't match — continue anyway? (y/N): " CONTINUE_IP
  [[ "$CONTINUE_IP" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
else
  echo "  ✓ DNS resolves correctly."
fi

# ── Step 2: Install certbot ───────────────────────────────────────────────────
echo ""
echo "▶ Step 2/8 — Installing certbot + nginx plugin ..."
apt-get install -y -q certbot python3-certbot-nginx
echo "  ✓ certbot installed."

# ── Step 3: Firewall ──────────────────────────────────────────────────────────
echo ""
echo "▶ Step 3/8 — Configuring UFW firewall ..."
if command -v ufw &>/dev/null; then
  ufw allow 22/tcp   comment 'SSH'   2>/dev/null || true
  ufw allow 80/tcp   comment 'HTTP'  2>/dev/null || true
  ufw allow 443/tcp  comment 'HTTPS' 2>/dev/null || true
  ufw --force enable 2>/dev/null || true
  ufw status numbered
  echo "  ✓ Ports 22, 80, 443 open."
else
  echo "  ufw not found — skipping firewall step (ensure ports 80/443 are open)."
fi

# ── Step 4: bench setup nginx ─────────────────────────────────────────────────
echo ""
echo "▶ Step 4/8 — Generating nginx config via bench ..."

# Confirm the site is set as the default
CURRENT_SITE=$(cat "${BENCH_DIR}/sites/currentsite.txt" 2>/dev/null || echo "")
if [[ -z "$CURRENT_SITE" ]]; then
  echo "  ERROR: No current site set. Run:"
  echo "    bench use $DOMAIN"
  echo "  (from inside $BENCH_DIR as user $BENCH_USER)"
  exit 1
fi

if [[ "$CURRENT_SITE" != "$DOMAIN" ]]; then
  echo "  WARNING: Current site is '$CURRENT_SITE', expected '$DOMAIN'."
  echo "  Run:  cd $BENCH_DIR && bench use $DOMAIN"
  read -rp "  Continue with '$CURRENT_SITE' anyway? (y/N): " CONTINUE_SITE
  [[ "$CONTINUE_SITE" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
  DOMAIN="$CURRENT_SITE"
fi

cd "$BENCH_DIR"
sudo -u "$BENCH_USER" bench setup nginx
echo "  ✓ nginx config generated."

NGINX_CONF=$(find /etc/nginx /etc/nginx/conf.d -name "*.conf" 2>/dev/null | xargs grep -l "$DOMAIN" 2>/dev/null | head -1)
if [[ -n "$NGINX_CONF" ]]; then
  echo "  Config file: $NGINX_CONF"
else
  echo "  (Config location: /etc/nginx/conf.d/frappe-bench.conf or similar)"
fi

# ── Step 5: Test nginx config ─────────────────────────────────────────────────
echo ""
echo "▶ Step 5/8 — Testing nginx configuration ..."
nginx -t
echo "  ✓ nginx config syntax OK."
systemctl reload nginx
echo "  ✓ nginx reloaded."

# ── Step 6: Obtain SSL certificate ───────────────────────────────────────────
echo ""
echo "▶ Step 6/8 — Obtaining Let's Encrypt certificate for $DOMAIN ..."
echo "  (This requires port 80 to be publicly accessible)"
echo ""

certbot --nginx \
  --non-interactive \
  --agree-tos \
  --email "$EMAIL" \
  --redirect \
  -d "$DOMAIN"

echo ""
echo "  ✓ Certificate obtained and nginx updated for HTTPS."

# ── Step 7: Reload nginx with HTTPS config ────────────────────────────────────
echo ""
echo "▶ Step 7/8 — Reloading nginx with HTTPS config ..."
nginx -t
systemctl reload nginx
echo "  ✓ nginx reloaded with SSL."

# ── Step 8: Verify auto-renewal ───────────────────────────────────────────────
echo ""
echo "▶ Step 8/8 — Testing auto-renewal (dry run) ..."
certbot renew --dry-run
echo "  ✓ Auto-renewal dry run passed."

# Ensure certbot renewal timer/cron is active
if systemctl list-units --type=timer | grep -q certbot; then
  systemctl enable --now certbot.timer 2>/dev/null || true
  echo "  ✓ certbot.timer systemd service is active."
else
  # Fallback: add a cron job
  CRON_LINE="0 3,15 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'"
  CRON_FILE="/etc/cron.d/certbot-renew"
  if [[ ! -f "$CRON_FILE" ]]; then
    echo "$CRON_LINE" > "$CRON_FILE"
    echo "  ✓ Renewal cron job written to $CRON_FILE"
  fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✅  Setup complete!"
echo ""
echo "  Your site is live at: https://$DOMAIN"
echo ""
echo "  Certificate details:"
certbot certificates --domain "$DOMAIN" 2>/dev/null | grep -E "Domains|Expiry|Certificate Path" | sed 's/^/    /'
echo ""
echo "  What was configured:"
echo "    • nginx serves $DOMAIN on ports 80 (redirect) and 443 (HTTPS)"
echo "    • Let's Encrypt certificate valid for 90 days, auto-renews"
echo "    • HTTP → HTTPS redirect enabled"
echo ""
echo "  Next steps:"
echo "    1. Open https://$DOMAIN in your browser"
echo "    2. Login with Administrator / <your admin password>"
echo "    3. Go to Settings → Vortex Settings to set your logo + brand"
echo "══════════════════════════════════════════════════════════"
