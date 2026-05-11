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
| **Best for** | Production (full control) | Staging, testing, quick setup |
| **OS** | Ubuntu 22.04 LTS | Any OS with Docker |
| **Effort** | ~45 min | ~15 min |
| **SSL** | certbot (free) | Let's Encrypt via certbot container |
| **Backups** | host cron | backup service in compose |

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
  wkhtmltopdf
```

### 3. Configure MariaDB

```bash
sudo mysql_secure_installation
# Set root password, remove anonymous users, disallow remote root, remove test DB
```

Add to `/etc/mysql/mariadb.conf.d/50-server.cnf` under `[mysqld]`:
```ini
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci
```

```bash
sudo systemctl restart mariadb
```

### 4. Create a Linux user

```bash
sudo useradd -m -s /bin/bash frappe
sudo passwd frappe
sudo usermod -aG sudo frappe
su - frappe          # all remaining steps run as 'frappe'
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
bench execute vortex_ops.vortex_ops.setup.inventory_setup.run
bench execute vortex_ops.vortex_ops.setup.brand_setup.run
```

### 9. Enable production mode

```bash
sudo bench setup production frappe
sudo bench setup nginx
sudo supervisorctl reload
```

### 10. SSL (Let's Encrypt — free)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d app.vortexbreaks.com --email admin@vortexbreaks.com --agree-tos
# Certbot auto-configures nginx and sets up auto-renewal
```

Verify auto-renewal works:
```bash
sudo certbot renew --dry-run
```

### 11. Automated backups (bare metal)

Add a daily cron job as the `frappe` user:

```bash
crontab -e
# Add this line:
0 2 * * * /home/frappe/frappe-bench/apps/vortex_ops/docker/backup.sh >> /var/log/vortex-backup.log 2>&1
```

The script creates a compressed backup in `sites/<site>/private/backups/` and optionally uploads to cloud storage. Set these environment variables in `/home/frappe/.bashrc` (or in the cron environment) for cloud upload:

```bash
export SITE_NAME=app.vortexbreaks.com
export BACKUP_S3_BUCKET=my-vortex-backups
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
# For Backblaze B2:
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
#   SITE_NAME (use your domain name)
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

Make sure your domain's DNS A record points to your server, then:

```bash
# Set DOMAIN and CERTBOT_EMAIL in .env first

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

Then restart the backup service:
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

**Ollama not responding**
```bash
systemctl status ollama
curl http://localhost:11434/api/tags     # should return model list
# If not running: systemctl start ollama
```

**Playwright / Whatnot scraper fails**
Check **Settings → Error Log** in the desk — it shows a page snippet so you can identify what changed on the Whatnot page.

**Emails not sending**
Go to **Settings → Email Account**, open the account, and click **Send Test Email**. Check the error message — usually it's an SMTP port/auth issue.

**Backup script: permission denied**
```bash
chmod +x /home/frappe/frappe-bench/apps/vortex_ops/docker/backup.sh
```
