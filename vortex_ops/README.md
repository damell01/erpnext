# Vortex Ops

A Frappe/ERPNext custom app that replaces the spreadsheets and paper reports used by **Vortex Breaks** — a Whatnot-based sports card and trading card break business — with a central operations platform covering inventory, payroll, and show management.

---

## What It Does

| Problem | Solution |
|---|---|
| Multiple spreadsheets tracking per-streamer data | Single ERPNext database with per-streamer records |
| Manual payout calculations each week | Automated payout generation with configurable pay types |
| Paper sheets for show sales data | Sales Upload DocType with manual entry or Whatnot auto-scrape |
| Inventory tracked manually per box type | Per-streamer ERPNext warehouses with stock entries |
| Loan deductions tracked separately | Loan records auto-deduct on payout approval |
| Post-show CSV matching done by hand | Ollama AI matches product descriptions to inventory items |

---

## Architecture

```
ERPNext v15 (Frappe)
└── vortex_ops (custom app)
    ├── vortex_ops/          # main module
    │   ├── doctype/         # all custom DocTypes
    │   ├── report/          # script reports
    │   ├── page/            # custom pages (Inventory dashboard)
    │   ├── ai/              # Ollama AI integrations
    │   └── automation/      # scheduled tasks + Whatnot scraper
    ├── setup/               # one-time setup helpers
    └── utils.py             # shared helpers (safe_float, ollama_chat, etc.)
```

Two businesses run on the same ERPNext instance. Every stream, payout period, and inventory location is scoped to a **Company** (business) via the `Whatnot Channel → Business` link.

---

## Full Workflow

### 1 — Stream happens

1. Create a **Stream Event** — link the Whatnot Channel, set the primary streamer, add any co-hosts in the Additional Streamers table.
2. After the show ends, enter (or scrape) the financials: Gross Sales, Platform Fees, Tips, Packages.
3. Submit the Stream Event → status moves to **Completed**, notifications sent.

### 2 — Sales Upload & inventory deduction

**Option A — Manual entry (paper sheet):**
1. Open the Stream Event → create a **Sales Upload**.
2. Streamer and warehouse auto-fill from the event.
3. Add line items: box type, qty sold, sale price.
4. Approve → Submit → inventory deducted automatically (Material Issue in ERPNext).

**Option B — Whatnot auto-scrape:**
1. Paste the Whatnot show URL into the `Whatnot Show URL` field on the Stream Event.
2. Click **"Fetch from Whatnot"** → Playwright logs in and grabs the recap page.
3. Ollama AI parses the raw page text into structured item lines (falls back to regex if Ollama is down).
4. Review the pre-populated Sales Upload, run **Run AI Match** to map descriptions to inventory items, approve, and submit.

### 3 — Weekly payroll

1. Create a **Payout Period** — set the date range and business. The period name auto-suggests from the dates ("Week of Jun 2–8, 2025").
2. **1 · Pull Streams** — fetches all submitted streams for that business in the date range.
3. **2 · Generate Payouts** — creates one **Streamer Payout** per streamer, pulls their stream data automatically.
4. Review each payout — the form shows a live net total and warns on negative payouts. Adjust tips, adjustments, or deductions as needed.
5. **3 · Approve All Reviewed** (or approve individually) — marks payouts Approved and records any loan deductions.
6. **Payroll Export** report → export to ADP CSV per streamer.

---

## DocTypes

### Core

| DocType | Purpose |
|---|---|
| **Stream Event** | One record per Whatnot show — financials, streamers, status |
| **Whatnot Channel** | Channel config — Whatnot username/password, linked business |
| **Streamer** | Per-streamer config — pay type, rates, fees, ADP ID, warehouse |
| **Payout Period** | Weekly/monthly pay cycle — contains linked streams |
| **Streamer Payout** | Calculated payout per streamer per period |
| **Loan Record** | Tracks outstanding loans; repayments auto-deduct from payouts |
| **Sales Upload** | Post-show sales entry — populates inventory deductions |

### Child Tables

| DocType | Parent | Purpose |
|---|---|---|
| **Stream Streamer** | Stream Event | Additional streamers / co-hosts |
| **Payout Period Stream** | Payout Period | Streams linked to a period |
| **Loan Repayment** | Loan Record | Per-period repayment schedule |
| **Sales Upload Line** | Sales Upload | One row per box/product sold |

---

## Payout Types

Every streamer can be configured independently:

| Type | Calculation |
|---|---|
| **Profit Share** | `gross_sales × profit_share_pct` |
| **Package** | `package_count × package_rate` |
| **Hourly** | Manual entry |
| **Flat Rate** | Fixed amount per period |

Plus: tips (toggleable per streamer), adjustments (manual +/−), owner platform fee (% taken from gross), and loan deductions (from Loan Record schedule).

---

## Inventory

Inventory is tracked **by box** (not individual cards) using ERPNext's native stock system.

- Each streamer gets a personal **Warehouse** (e.g. "Jordan Inventory - VB").
- Shared locations: Main Storage, Returned Inventory, Damaged Inventory, Fulfillment Area.
- Stock operations: Add (receipt), Remove, Transfer between locations, Adjust (correction/damage).
- The **Vortex Inventory** page (`/vortex-inventory`) gives a card-grid overview of all locations with SKU count, total units, stock value, and low-stock alerts.
- When a Sales Upload is submitted, a **Material Issue** stock entry deducts exactly what was sold from the streamer's warehouse. COGS and gross profit update on the Stream Event.

### Inventory reports

- **Inventory by Streamer** — per-location breakdown with unit cost, total value, reorder alerts, and subtotals.
- ERPNext Stock Ledger — full audit trail for all stock movements.

---

## AI Features (Ollama)

All AI runs locally via [Ollama](https://ollama.com). No data leaves the server.

| Feature | Where | What it does |
|---|---|---|
| **Whatnot Page Parser** | Whatnot scraper | Reads raw page text, extracts totals + item list as JSON |
| **Product Matcher** | Sales Upload | Matches informal box descriptions to ERPNext item codes |
| **Anomaly Detection** | Payout Period | Flags unusual payout amounts before approval |
| **Stream Summary** | Stream Event (on submit) | Auto-generates a text summary of the show |
| **Low Stock Predictor** | Automation | Predicts reorder needs based on sales velocity |

### Setup

```bash
# Install Ollama on the server
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b   # or any model you prefer

# Optional: set model in site config
# frappe.conf.ollama_model = "llama3.1:8b"
```

---

## Whatnot Scraper

Automates post-show data collection via Playwright + Ollama.

### Install

```bash
pip install playwright
playwright install chromium
```

### Configure

1. Open the **Whatnot Channel** record for your channel.
2. Set `Whatnot Username` and `Whatnot Password` (stored encrypted).

### Use

1. After a show ends, find the show URL in your Whatnot seller dashboard.
2. Paste it into `Whatnot Show URL` on the **Stream Event**.
3. Click **"Fetch from Whatnot"** — the scraper logs in, grabs the recap, and Ollama extracts the data into a Sales Upload.
4. If Ollama is unavailable, regex extraction runs as a fallback.
5. If the page structure has changed and nothing is extracted, check the **Error Log** for a page snippet — adjust selectors in `automation/whatnot_scraper.py`.

---

## Reports

| Report | DocType | Notes |
|---|---|---|
| **Payroll Export** | Streamer Payout | Full per-streamer breakdown; filters by period and draft/submitted |
| **Inventory by Streamer** | Bin / Warehouse | Stock by location with cost, value, reorder alerts |
| **Loan Balance Ledger** | Loan Record | Outstanding balances with status colors; filter by streamer |

---

## Setup

### First-time inventory setup

```python
# From the Frappe console or via bench execute:
from vortex_ops.setup.inventory_setup import run
run()
```

This creates UOMs (Box, Case, Pack, etc.), item groups (Sports Cards, TCG, Sealed Wax, etc.), and base warehouses (Main Storage, Returned Inventory, etc.).

Or click **Setup Inventory** on the Vortex Ops workspace.

### Roles

| Role | Access |
|---|---|
| `Vortex Admin` | Full access — all DocTypes, AI features, anomaly checks |
| `Vortex Operations` | Day-to-day — streams, payouts, sales uploads, approvals |
| `Vortex Accounting` | Payroll export, ADP CSV download |

---

## Requirements

```
frappe/erpnext v15
requests >= 2.31.0
playwright          (optional — for Whatnot auto-scrape)
ollama              (optional — local AI, recommended)
```

---

## Two-Business Setup

Both businesses run on the same ERPNext instance. Separation is handled by:
- **Company** field on Payout Period, Stream Event, and Whatnot Channel.
- `pull_streams()` filters streams by the period's company.
- Separate Whatnot Channels with separate credentials.
- Streamer records are shared if a streamer works for both businesses.
