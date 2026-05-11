# Vortex Ops — Installation Guide

## How it works

Vortex Ops is a **Frappe custom app** — essentially a plugin for the ERPNext platform. The app lives in this git repo and installs like any other plugin:

```bash
bench get-app vortex_ops https://github.com/damell01/vortex-ops  # download
bench --site mysite install-app vortex_ops                        # activate
```

Frappe handles creating all database tables, loading hooks, and serving assets. You can install it on any ERPNext v15 instance, uninstall it, or reinstall it without touching the platform itself.

---

## Two deployment paths

| | Bare Metal | Docker |
|---|---|---|
| **Best for** | Full control, production | Quick test, staging |
| **OS** | Ubuntu 22.04 LTS | Any OS with Docker |
| **Effort** | ~45 min | ~15 min |
| **SSL** | certbot (free) | Let's Encrypt via certbot container |
| **Backups** | host cron | backup service in compose |

> **Recommendation:** Do bare metal for your first install — logs are visible directly and bench commands work exactly as documented. Move to Docker when you're ready to deploy to a production VPS.

---

## Option A — Bare Metal (Ubuntu 22.04)

### 1. Server requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 40 GB SSD | 100 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 2. System dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git curl wget python3-dev python3-pip python3-venv \
  build-essential libssl-dev libffi-dev \
  mariadb-server mariadb-client \
  redis-server nginx supervisor \
  wkhtmltopdf dnsutils
```

### 3. Configure MariaDB

```bash
sudo mysql_secure_installation
# Answer the prompts:
#   Set root password?        → Yes, choose a strong password
#   Remove anonymous users?   → Yes
#   Disallow remote root?     → Yes
#   Remove test database?     → Yes
#   Reload privilege tables?  → Yes
```

Add to `/etc/mysql/mariadb.conf.d/50-server.cnf` under the `[mysqld]` section:

```ini
[mysqld]
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci
```

```bash
sudo systemctl restart mariadb
```

### 4. Create a Linux user

```bash
sudo useradd -m -s /bin/bash frappe
sudo passwd frappe              # choose a strong password
sudo usermod -aG sudo frappe
su - frappe                     # all remaining steps run as 'frappe'
```

### 5. Install bench and initialize

```bash
pip3 install frappe-bench
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench
```

### 6. Add apps

```bash
bench get-app --branch version-15 erpnext
bench get-app vortex_ops https://github.com/damell01/vortex-ops
# Private repo: bench get-app vortex_ops git@github.com:damell01/vortex-ops.git
```

### 7. Create site and install

Replace `app.vortexbreaks.com` with your actual subdomain throughout:

```bash
bench new-site app.vortexbreaks.com \
  --mariadb-root-password YOUR_DB_ROOT_PW \
  --admin-password YOUR_ADMIN_PW

bench --site app.vortexbreaks.com install-app erpnext
bench --site app.vortexbreaks.com install-app vortex_ops
bench --site app.vortexbreaks.com migrate
bench use app.vortexbreaks.com
```

### 8. Run setup scripts

```bash
bench execute vortex_ops.vortex_ops.setup.brand_setup.run
```

### 9. Enable production mode

This switches bench from the development server to Supervisor-managed gunicorn workers:

```bash
sudo bench setup production frappe
# Creates /etc/supervisor/conf.d/frappe-bench.conf and starts gunicorn + workers
```

Verify services are running:

```bash
sudo supervisorctl status
# Should show: frappe-bench-web, frappe-bench-worker-*, frappe-bench-schedule — all RUNNING
```

---

## Subdomain + nginx + SSL (full walkthrough)

This section covers everything from DNS through a live HTTPS site. All commands run on the server as root (or with sudo) unless noted.

### Step A — Point your DNS to the server

In your domain registrar's DNS settings (Cloudflare, Namecheap, GoDaddy, etc.), add one A record:

| Field | Value |
|---|---|
| **Type** | A |
| **Name** | `app` (or whatever subdomain you want) |
| **Value** | Your server's public IP address |
| **TTL** | 300 (5 minutes — you can raise it later) |

To find your server's public IP:
```bash
curl -s https://api.ipify.org && echo
```

Wait 1–5 minutes, then confirm DNS is propagated:
```bash
# Run this from your laptop or the server
dig app.vortexbreaks.com A +short
# Should return your server IP
```

If `dig` isn't installed: `sudo apt install dnsutils -y`

> **Cloudflare users:** Keep the orange proxy cloud **off** (grey cloud / DNS only) until the certificate is issued. Certbot needs a direct HTTP connection to verify your domain. You can re-enable the Cloudflare proxy after the cert is obtained.

### Step B — Open firewall ports

```bash
sudo apt install ufw -y
sudo ufw allow 22/tcp   comment 'SSH'
sudo ufw allow 80/tcp   comment 'HTTP (certbot verification + redirect)'
sudo ufw allow 443/tcp  comment 'HTTPS'
sudo ufw --force enable
sudo ufw status numbered
```

Expected output:
```
     To                         Action      From
--   --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 80/tcp                     ALLOW IN    Anywhere
[ 3] 443/tcp                    ALLOW IN    Anywhere
```

> If your VPS provider has a separate firewall panel (AWS Security Groups, DigitalOcean Firewall, Hetzner Firewall), also open ports 80 and 443 there.

### Step C — Generate the nginx config

Frappe's `bench setup nginx` reads your site name and generates a complete nginx config file:

```bash
cd ~/frappe-bench

# Make sure the site you want to serve is set as the current site
bench use app.vortexbreaks.com

# Generate the nginx config (will create /etc/nginx/conf.d/frappe-bench.conf)
sudo bench setup nginx
```

Verify the config was created and contains your domain:
```bash
grep -l "app.vortexbreaks.com" /etc/nginx/conf.d/*.conf
# Should print: /etc/nginx/conf.d/frappe-bench.conf  (or similar)
```

What the generated config does:
- Listens on port 80 for `app.vortexbreaks.com`
- Proxies `/` to gunicorn on `127.0.0.1:8000`
- Proxies `/socket.io` to the WebSocket server on `127.0.0.1:9000`
- Serves static files from `sites/assets/` directly (no Python overhead)
- Sets security headers (X-Frame-Options, X-Content-Type-Options, etc.)

Test the config syntax before reloading:
```bash
sudo nginx -t
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Reload nginx:
```bash
sudo systemctl reload nginx
```

At this point your site should be accessible over HTTP (port 80). Test it:
```bash
curl -I http://app.vortexbreaks.com
# HTTP/1.1 200 OK  ← success
# HTTP/1.1 301     ← also fine, just a redirect
```

### Step D — Install certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Step E — Obtain the SSL certificate

```bash
sudo certbot --nginx \
  --non-interactive \
  --agree-tos \
  --email admin@vortexbreaks.com \
  --redirect \
  -d app.vortexbreaks.com
```

Flag breakdown:
- `--nginx` — certbot reads and rewrites your nginx config automatically
- `--redirect` — adds a permanent HTTP→HTTPS redirect to the nginx config
- `--non-interactive --agree-tos` — no prompts, auto-accept terms
- `--email` — where expiry warnings are sent (use a real address)

Successful output looks like:
```
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/app.vortexbreaks.com/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/app.vortexbreaks.com/privkey.pem
This certificate expires on 2026-08-09.

Deploying certificate to VirtualHost /etc/nginx/conf.d/frappe-bench.conf
Redirecting all traffic on port 80 to ssl in /etc/nginx/conf.d/frappe-bench.conf

Congratulations! You have successfully enabled HTTPS on https://app.vortexbreaks.com
```

Reload nginx one final time:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Step F — Verify the certificate

```bash
# Check cert details
sudo certbot certificates
# Should show:
#   Domains: app.vortexbreaks.com
#   Expiry Date: 2026-08-09 (VALID: 89 days)

# Test HTTPS from the server
curl -I https://app.vortexbreaks.com
# HTTP/2 200

# Check the cert from outside (uses openssl)
echo | openssl s_client -connect app.vortexbreaks.com:443 -servername app.vortexbreaks.com 2>/dev/null \
  | openssl x509 -noout -subject -dates
# subject=CN = app.vortexbreaks.com
# notBefore=May 11 ...
# notAfter=Aug  9 ...
```

### Step G — Test auto-renewal

Let's Encrypt certificates expire after 90 days. Certbot auto-renews them. Test that the renewal logic works:

```bash
sudo certbot renew --dry-run
# Should end with: "Congratulations, all simulated renewals succeeded."
```

Confirm the renewal timer is active (Ubuntu 22.04 uses systemd):
```bash
sudo systemctl status certbot.timer
# Active: active (waiting)
# Trigger: Mon 2026-05-12 00:00:00 UTC  (roughly)
```

If you prefer a cron job instead:
```bash
# Edit root's crontab
sudo crontab -e
# Add this line (runs twice daily, standard certbot recommendation):
0 3,15 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### Automated script (does all of the above in one command)

A script is included at `scripts/setup-nginx-ssl.sh` that runs Steps A–G automatically with safety checks:

```bash
# Run on your server as root (after DNS is pointed and bench is set up):
cd ~/frappe-bench/apps/vortex_ops
sudo bash scripts/setup-nginx-ssl.sh app.vortexbreaks.com admin@vortexbreaks.com frappe
```

Arguments: `<domain> <email> [bench-user=frappe] [bench-dir=/home/frappe/frappe-bench]`

The script checks DNS resolution, opens UFW ports, runs `bench setup nginx`, obtains the certificate, and verifies renewal — printing a confirmation summary at the end.

---

### Nginx config reference (what bench generates)

After running `bench setup nginx`, the file `/etc/nginx/conf.d/frappe-bench.conf` contains roughly:

```nginx
# Generated by bench setup nginx — do not hand-edit (re-run bench setup nginx to regenerate)

upstream frappe-bench-frappe {
    server 127.0.0.1:8000 fail_timeout=0;
}

upstream frappe-bench-socketio-server {
    server 127.0.0.1:9000 fail_timeout=0;
}

server {
    listen 80;
    server_name app.vortexbreaks.com;

    root /home/frappe/frappe-bench/sites;

    # Static assets served directly — no Python overhead
    location /assets {
        try_files $uri =404;
    }

    # Protected files (served via X-Accel-Redirect)
    location ~ ^/protected/(.*) {
        internal;
        try_files /$1 =404;
    }

    # WebSocket for real-time desk updates
    location /socket.io {
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Frappe-Site-Name app.vortexbreaks.com;
        proxy_set_header Host $host;
        proxy_pass http://frappe-bench-socketio-server;
    }

    # Everything else → gunicorn
    location / {
        try_files $uri @webserver;
    }

    location @webserver {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Frappe-Site-Name app.vortexbreaks.com;
        proxy_set_header Host $host;
        proxy_read_timeout 120;
        proxy_pass http://frappe-bench-frappe;
    }
}
```

After certbot runs (`--nginx` flag), it adds an SSL server block and rewrites the HTTP block to redirect:

```nginx
server {
    listen 80;
    server_name app.vortexbreaks.com;
    return 301 https://$host$request_uri;  # ← added by certbot
}

server {
    listen 443 ssl http2;
    server_name app.vortexbreaks.com;

    ssl_certificate     /etc/letsencrypt/live/app.vortexbreaks.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.vortexbreaks.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # ... rest of the location blocks from above ...
}
```

You should not hand-edit this file. If you need to change the site name, re-run `bench setup nginx`.

---

### Multiple subdomains / sites

Frappe supports multiple sites on one bench instance. Each site needs its own nginx server block and its own certificate:

```bash
# Create second site
bench new-site ops2.vortexbreaks.com \
  --mariadb-root-password YOUR_DB_ROOT_PW \
  --admin-password YOUR_ADMIN_PW
bench --site ops2.vortexbreaks.com install-app erpnext
bench --site ops2.vortexbreaks.com install-app vortex_ops

# Regenerate nginx config (now covers both sites)
sudo bench setup nginx
sudo nginx -t && sudo systemctl reload nginx

# Obtain cert for the second subdomain
sudo certbot --nginx --non-interactive --agree-tos \
  --email admin@vortexbreaks.com --redirect \
  -d ops2.vortexbreaks.com
```

---

## Automated backups (bare metal)

Add a daily cron job as the `frappe` user:

```bash
crontab -e
# Add this line (runs at 2am daily):
0 2 * * * /home/frappe/frappe-bench/apps/vortex_ops/docker/backup.sh >> /var/log/vortex-backup.log 2>&1
```

The script creates a compressed backup in `sites/<site>/private/backups/` and optionally uploads to cloud storage. Set these environment variables in `/home/frappe/.bashrc` for cloud upload:

```bash
export SITE_NAME=app.vortexbreaks.com
export BACKUP_S3_BUCKET=my-vortex-backups
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
# For Backblaze B2 (cheaper than S3):
# export AWS_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

---

## Option B — Docker

### Requirements
- Docker Engine 24+ and Docker Compose v2
- 4 GB RAM minimum

### 1. Clone the repo

```bash
git clone https://github.com/damell01/vortex-ops
cd vortex-ops/docker
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set:
#   DB_ROOT_PASSWORD
#   ADMIN_PASSWORD
#   SITE_NAME (your domain name, e.g. app.vortexbreaks.com)
#   DOMAIN    (same value)
#   CERTBOT_EMAIL
```

### 3. Start (development / no SSL)

```bash
docker compose up -d --build
# First build takes 5–10 minutes
```

### 4. Initialize the site (run once)

```bash
docker compose exec backend bash /setup-site.sh
```

### 5. Open in browser

```
http://localhost   (or your server IP)
Login: Administrator / <ADMIN_PASSWORD>
```

### 6. Production with SSL + backups

Make sure your domain's DNS A record points to your server (same Step A as bare metal above), then:

```bash
# Get your SSL certificate (run once):
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email ${CERTBOT_EMAIL} --agree-tos --no-eff-email \
  -d ${DOMAIN}

# Start everything with SSL + auto-renewal + daily backups:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Certbot renews certificates automatically every 12 hours (only actually renews within 30 days of expiry). Backups run daily at 2am.

### 7. Cloud backups for Docker

Add to `.env`:

```bash
BACKUP_S3_BUCKET=my-vortex-backups
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
# Backblaze B2: AWS_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

Restart the backup service:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backup
```

### 8. Rebuilding after a Vortex Ops update

```bash
docker compose build backend
docker compose up -d
docker compose exec backend bash -c "bench --site \$SITE_NAME migrate"
```

---

## Email / SMTP configuration

System emails (password resets, payout notifications) won't send until you configure an outbound mail server. Do this inside the ERPNext desk:

1. Go to **Settings → Email Account**
2. Click **New**
3. Fill in your SMTP settings:

| Provider | SMTP Host | Port | Auth |
|---|---|---|---|
| Gmail (App Password) | smtp.gmail.com | 587 | TLS |
| SendGrid | smtp.sendgrid.net | 587 | TLS |
| Mailgun | smtp.mailgun.org | 587 | TLS |
| AWS SES | email-smtp.us-east-1.amazonaws.com | 587 | TLS |

4. Check **Default Outgoing** and **Enable Outgoing**
5. Save and click **Send Test Email**

> **Recommended:** Use a transactional email service (SendGrid free tier = 100 emails/day, Mailgun free tier = 1,000/month) rather than a personal Gmail account to avoid deliverability issues.

---

## Optional: Ollama (local AI)

Powers the Whatnot page parser, product matcher, anomaly detection, and stream summaries. All processing runs on your server — no data ever leaves.

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# Verify
curl http://localhost:11434/api/tags
```

Vortex Ops auto-detects Ollama. If it's not running, AI features fall back to regex — everything still works.

**Recommended models by hardware:**

| RAM | Model | Notes |
|---|---|---|
| 8 GB | llama3.1:8b | Good default |
| 16 GB | llama3.1:8b or mistral | Faster |
| 32 GB+ | llama3.1:70b | Best quality |

---

## Optional: Playwright (Whatnot auto-scraper)

Lets the "Fetch from Whatnot" button auto-scrape post-show data. Already included in the Docker image. For bare metal:

```bash
pip install playwright
playwright install chromium
```

Then add Whatnot credentials to your **Whatnot Channel** record.

---

## First Login Checklist

After install, complete these steps in the Vortex Ops desk:

- [ ] **Settings → Vortex Settings** — upload your logo, confirm brand name/color
- [ ] **Settings → Email Account** — configure outbound SMTP
- [ ] **Accounting → Company** — create one Company per brand
- [ ] **Vortex Ops → Whatnot Channel** — one record per Whatnot account with credentials
- [ ] **Vortex Ops → Streamer** — one record per streamer with pay type and rates
- [ ] **Inventory page** — click "Setup Inventory" if warehouses aren't pre-created
- [ ] **Settings → User** — invite team members and assign Vortex roles

---

## Roles

| Role | Who | Access |
|---|---|---|
| `Vortex Admin` | Owner / manager | Full access — settings, AI, anomaly checks |
| `Vortex Operations` | Day-to-day staff | Streams, payouts, sales uploads, approvals |
| `Vortex Accounting` | Bookkeeper | Payroll export, ADP CSV, read-only financials |

---

## Upgrading Vortex Ops

**Bare metal:**
```bash
cd ~/frappe-bench
bench get-app vortex_ops https://github.com/damell01/vortex-ops  # pull latest
bench --site app.vortexbreaks.com migrate
bench restart
```

**Docker:**
```bash
cd docker
docker compose build backend
docker compose up -d
docker compose exec backend bash -c "bench --site \$SITE_NAME migrate"
```

---

## Troubleshooting

**App missing from desk after install**
```bash
bench --site <site> list-apps      # confirm vortex_ops is listed
bench --site <site> migrate        # run if DocTypes are missing
bench --site <site> clear-cache
```

**Brand name still shows "ERPNext" after install**
```bash
bench execute vortex_ops.vortex_ops.setup.brand_setup.run
bench --site <site> clear-cache
```

**Certbot fails: "Could not bind to 0.0.0.0:80"**
```bash
# Something else is on port 80 — usually nginx or apache
sudo systemctl stop nginx
sudo certbot certonly --standalone -d app.vortexbreaks.com --email admin@vortexbreaks.com --agree-tos
sudo systemctl start nginx
# Then re-install cert into nginx:
sudo certbot install --nginx -d app.vortexbreaks.com
```

**Certbot fails: "DNS problem: NXDOMAIN / no A record"**

DNS hasn't propagated yet or is pointed at the wrong IP.
```bash
dig app.vortexbreaks.com A +short   # should return your server IP
# If blank or wrong: fix the A record and wait 5–10 min, then retry
```

**nginx 502 Bad Gateway**
```bash
# Gunicorn isn't running
sudo supervisorctl status
sudo supervisorctl restart frappe-bench-web
# Check gunicorn logs:
tail -50 ~/frappe-bench/logs/web.error.log
```

**nginx 403 or blank page**
```bash
# Permissions on the bench directory
chmod o+x /home/frappe /home/frappe/frappe-bench
```

**Site shows "404 No Such Site"**
```bash
# The site name in bench must match the Host header nginx sends
bench use app.vortexbreaks.com
sudo bench setup nginx
sudo systemctl reload nginx
```

**Ollama not responding**
```bash
systemctl status ollama
curl http://localhost:11434/api/tags     # should return model list
# If not running: systemctl start ollama
```

**Emails not sending**
Go to **Settings → Email Account**, open the account, and click **Send Test Email**. Check the error message — usually it's an SMTP port/auth issue.

**Backup script: permission denied**
```bash
chmod +x /home/frappe/frappe-bench/apps/vortex_ops/docker/backup.sh
```
