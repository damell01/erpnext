# Vortex Ops — Installation Guide

Two paths: **Bare Metal** (recommended for production) or **Docker** (easier for testing / staging).

---

## Option A — Bare Metal (Ubuntu 22.04)

### 1. Server requirements

| Resource | Minimum | Recommended |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disk | 40 GB | 100 GB |
| Python | 3.10+ | 3.11 |
| Node | 18 LTS | 20 LTS |

### 2. Install system dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git curl wget python3-dev python3-pip python3-venv \
  build-essential libssl-dev libffi-dev \
  mariadb-server mariadb-client \
  redis-server \
  nginx \
  supervisor \
  wkhtmltopdf
```

### 3. Configure MariaDB

```bash
sudo mysql_secure_installation
# When prompted:
#   Set root password: yes → choose a strong password
#   Remove anonymous users: yes
#   Disallow root login remotely: yes
#   Remove test database: yes
#   Reload privilege tables: yes
```

Add required settings to `/etc/mysql/mariadb.conf.d/50-server.cnf` under `[mysqld]`:

```ini
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci
```

```bash
sudo systemctl restart mariadb
```

### 4. Create a Linux user for Frappe

```bash
sudo useradd -m -s /bin/bash frappe
sudo passwd frappe
sudo usermod -aG sudo frappe
# Log in as the frappe user for all remaining steps
su - frappe
```

### 5. Install bench CLI

```bash
pip3 install frappe-bench
```

### 6. Initialize a bench (installs Frappe framework)

```bash
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench
```

### 7. Add ERPNext

```bash
bench get-app --branch version-15 erpnext
```

### 8. Add Vortex Ops

```bash
bench get-app vortex_ops https://github.com/damell01/erpnext
# If the repo is private, use SSH:
# bench get-app vortex_ops git@github.com:damell01/erpnext.git
```

### 9. Create a site

```bash
bench new-site vortexbreaks.local \
  --mariadb-root-password YOUR_MARIADB_ROOT_PW \
  --admin-password YOUR_ADMIN_PW
```

### 10. Install apps on the site

```bash
bench --site vortexbreaks.local install-app erpnext
bench --site vortexbreaks.local install-app vortex_ops
bench --site vortexbreaks.local migrate
bench use vortexbreaks.local
```

### 11. Run setup scripts

```bash
# Create base inventory structure (UOMs, item groups, warehouses)
bench execute vortex_ops.vortex_ops.setup.inventory_setup.run

# Seed brand defaults (sets system name to "VortexBreaks")
bench execute vortex_ops.vortex_ops.setup.brand_setup.run
```

### 12. Start for development / testing

```bash
bench start
# Open http://localhost:8000  →  login as Administrator
```

### 13. Production mode (nginx + supervisor)

```bash
sudo bench setup production frappe
sudo bench setup nginx
sudo supervisorctl reload
```

---

## Optional: Ollama (local AI)

Ollama powers the Whatnot page parser, product matcher, anomaly detection, and stream summaries. All processing runs on your server — no data leaves.

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (llama3.1:8b is a good balance of speed and quality)
ollama pull llama3.1:8b

# Verify it's running
curl http://localhost:11434/api/tags
```

Vortex Ops auto-detects Ollama. If it's not running, AI features fall back to regex extraction — everything still works.

---

## Optional: Playwright (Whatnot auto-scraper)

Playwright is only needed if you want the "Fetch from Whatnot" button to auto-scrape post-show data.

```bash
pip install playwright
playwright install chromium
```

Then set `Whatnot Username` and `Whatnot Password` on your **Whatnot Channel** record.

---

## Option B — Docker

### Requirements

- Docker Engine 24+ and Docker Compose v2
- 4 GB RAM minimum

### 1. Clone the repo

```bash
git clone https://github.com/damell01/erpnext vortex-ops
cd vortex-ops
```

### 2. Configure

```bash
cp docker/.env.example docker/.env
# Edit docker/.env — set DB_ROOT_PASSWORD, ADMIN_PASSWORD, SITE_NAME
```

### 3. Build and start

```bash
cd docker
docker compose up -d --build
```

This starts: MariaDB, Redis ×2, Nginx, Gunicorn backend, 3 background workers, scheduler, and WebSocket.

The first build takes 5–10 minutes (downloads ERPNext + Vortex Ops).

### 4. Initialize the site (run once)

```bash
docker compose exec backend bash /setup-site.sh
```

This creates the site, installs all apps, runs migrations, and seeds the brand defaults.

### 5. Open in browser

```
http://localhost   (or your server's IP)
Login: Administrator / <ADMIN_PASSWORD from .env>
```

### Rebuilding after a Vortex Ops update

```bash
docker compose build backend
docker compose up -d
docker compose exec backend bash -c "cd /home/frappe/frappe-bench && bench --site \$SITE_NAME migrate"
```

---

## First Login Checklist

After install, complete these steps in the Vortex Ops desk:

- [ ] **Settings → Vortex Settings** — upload your logo, confirm brand name and color
- [ ] **Accounting → Company** — create one Company per brand (e.g. "Vortex Breaks", "Vortex 2")
- [ ] **Vortex Ops → Whatnot Channel** — create one record per Whatnot account, set credentials
- [ ] **Vortex Ops → Streamer** — create a record per streamer, set pay type and rates
- [ ] **Inventory page** — click "Setup Inventory" if warehouses aren't pre-created
- [ ] **System Settings** — configure your outbound email (SMTP) so password resets and notifications work

---

## Roles

| Role | Who gets it |
|---|---|
| `Vortex Admin` | Owner / manager — full access including settings, AI, anomaly checks |
| `Vortex Operations` | Day-to-day staff — streams, payouts, sales uploads, approvals |
| `Vortex Accounting` | Bookkeeper — payroll export, ADP CSV, read-only financials |

Assign roles at **Settings → User** for each team member.

---

## Upgrading Vortex Ops

**Bare metal:**
```bash
cd frappe-bench
bench get-app vortex_ops https://github.com/damell01/erpnext   # pulls latest
bench --site vortexbreaks.local migrate
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

**App not found after install**
```bash
bench --site <site> list-apps    # confirm vortex_ops is listed
bench --site <site> migrate      # run if DocTypes are missing
```

**Ollama not connecting**
```bash
systemctl status ollama
curl http://localhost:11434/api/tags   # should return model list
```

**Playwright login fails**
Open the Error Log in the Frappe desk (`Settings → Error Log`) — it includes a page snippet to help identify selector changes.

**Brand name still shows ERPNext**
```bash
bench execute vortex_ops.vortex_ops.setup.brand_setup.run
bench --site <site> clear-cache
```
