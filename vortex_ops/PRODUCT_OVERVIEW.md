# Vortex Breaks — Operations Platform
### Product Overview & Roadmap

**Prepared for:** Vortex Breaks  
**Platform:** Vortex Ops  
**Date:** May 2025  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State — Before This System](#2-current-state--before-this-system)
3. [Operational Workflows](#3-operational-workflows)
4. [Phases & Priorities](#4-phases--priorities)
5. [Reporting Requirements](#5-reporting-requirements)
6. [System Architecture](#6-system-architecture)
7. [Future Expansion Ideas](#7-future-expansion-ideas)
8. [Roadmap](#8-roadmap)

---

## 1. Executive Summary

Vortex Breaks is a sports card and trading card game (TCG) break business operating on the Whatnot live-streaming platform. The business runs 75+ streams per week across two separate brands, employs multiple streamers with different pay structures, manages per-streamer physical inventory, and processes weekly payroll through ADP.

**The core problem:** Every operational function — inventory counts, sales tracking, streamer payouts, loan balances, and tip reconciliation — is currently managed across disconnected spreadsheets and paper forms. As the business scales, this creates:
- Payroll errors from manual calculations
- No real-time visibility into inventory levels
- Time spent reconciling data across multiple sheets
- No audit trail for deductions, loans, or adjustments

**The solution:** A centralized operations platform — Vortex Ops — that replaces every spreadsheet with a structured database, automates repetitive calculations, and provides a single source of truth for the entire operation — while keeping the workflows familiar and easy to use.

---

## 2. Current State — Before This System

### How payroll works today

```
Show happens on Whatnot
       ↓
Streamer fills out paper recap sheet
(sales, packages, tips, notes)
       ↓
Admin manually reads Whatnot summary page
       ↓
Numbers entered into individual spreadsheets
(one or more per streamer)
       ↓
Payout calculated manually per streamer
(different formulas per pay type)
       ↓
Loan deductions applied manually
       ↓
ADP entry done by hand
```

**Pain points:**
- A single data entry error cascades through the whole week's payroll
- No history of what changed or why (no audit trail)
- Loan balances tracked informally — easy to miss or double-deduct
- Multi-streamer shows require splitting numbers by hand
- Two businesses require separate tracking with no shared infrastructure

### How inventory works today

- Inventory counts tracked per streamer in spreadsheets
- No automatic deduction when items sell
- Product cost not formally tracked → COGS unknown
- No reorder alerts → stock-outs discovered too late
- No way to see total business-wide inventory value at a glance

---

## 3. Operational Workflows

### 3.1 — Show Lifecycle

```
1. PRE-SHOW
   Create Stream Event
   └── Assign channel, date, primary streamer
   └── Add co-hosts if it's a multi-streamer show

2. DURING SHOW
   (No system interaction required — streamer streams on Whatnot)

3. POST-SHOW (same day / next morning)
   Option A — Manual entry:
     Open Stream Event → enter gross sales, packages, tips from Whatnot recap
   Option B — Auto-scrape (when Playwright installed):
     Paste Whatnot show URL → click "Fetch from Whatnot"
     → Ollama AI extracts totals + item list automatically
   Submit Stream Event → status = Completed

4. SALES UPLOAD
   Open/create Sales Upload linked to the stream
   Enter what boxes were sold (item, qty, sale price)
   OR let the scraper pre-populate from Whatnot
   Run AI Match → Ollama maps descriptions to your inventory items
   Approve → Submit → inventory deducted automatically
```

### 3.2 — Weekly Payroll Cycle

```
MONDAY (or start of pay period)
  Create Payout Period
  └── Set date range (name auto-suggests: "Week of Jun 2–8, 2025")
  └── Select business (Company)

  "1 · Pull Streams"
  └── Fetches all submitted shows in the date range for that business

  "2 · Generate Payouts"
  └── Creates one Streamer Payout per streamer automatically
  └── Pulls their gross sales, packages, and tips from streams

REVIEW
  Open each Streamer Payout
  └── Verify gross sales, tips, adjustments
  └── Loan deductions shown automatically from scheduled repayments
  └── Net payout updates live as you edit
  Submit → status = Reviewed

APPROVE
  "3 · Approve All Reviewed" (one click)
  └── Marks all Reviewed payouts as Approved
  └── Records loan deductions — loan balances update automatically

EXPORT
  Open Payroll Export report
  └── Shows every streamer: gross, share, packages, tips, fees, deductions, net
  Download ADP CSV per streamer → enter into ADP
```

### 3.3 — Inventory Management

```
RECEIVING STOCK
  Inventory page → "+ Add Stock" on any location
  └── Select item (box type), qty, cost per unit
  └── Creates Material Receipt → stock increases

TRANSFERRING TO STREAMERS
  "Transfer" button → move from Main Storage to streamer's warehouse
  └── Typical flow: bulk shipment arrives in Main Storage,
      then split to each streamer before their shows

AFTER A SHOW
  Sales Upload submission auto-creates Material Issue
  └── Deducts exactly what sold from the streamer's warehouse
  └── COGS updates on the Stream Event record

MONITORING
  Inventory page — card grid of all locations
  └── SKU count, total units, stock value, low-stock badges
  Inventory by Streamer report — full item-level detail with cost
```

### 3.4 — Loan Management

```
CREATING A LOAN
  Loan Record → set streamer, amount, date
  Add repayment schedule rows (amount per period, status = Scheduled)
  Submit → status = Active

AUTOMATIC DEDUCTION
  When payouts are generated, _get_loans() finds all Scheduled
  repayments for the streamer's active loans
  Deducted from net payout automatically
  On Approve → repayment rows marked Deducted, loan balance updates

TRACKING
  Loan Balance Ledger report
  └── All active loans by streamer with remaining balance
  └── Filter by streamer or status
  Dashboard indicator on each Streamer record shows active loan balance
```

---

## 4. Phases & Priorities

### Phase 1 — Core Infrastructure ✅ Complete

**Goal:** Replace the paper + spreadsheet workflow with a structured database.

| ✅ | Feature |
|---|---|
| ✅ | Streamer records with per-streamer pay config |
| ✅ | Stream Event DocType with financials |
| ✅ | Per-streamer warehouse (inventory location) |
| ✅ | Payout Period with auto-generate payouts |
| ✅ | Streamer Payout with all pay type calculations |
| ✅ | Loan Record + auto-deduction on payout approve |
| ✅ | Two-business support (separate companies) |
| ✅ | ADP payroll export (CSV + report) |

---

### Phase 2 — Inventory Foundation ✅ Complete

**Goal:** Get per-streamer inventory tracking live, replacing spreadsheet counts.

| ✅ | Feature |
|---|---|
| ✅ | Inventory page (card grid overview) |
| ✅ | Per-streamer warehouses with tracked stock entries |
| ✅ | Add Stock, Remove, Transfer, Adjust from the UI |
| ✅ | Product cost (valuation rate) per item |
| ✅ | Low-stock reorder alerts |
| ✅ | Inventory by Streamer report |
| ✅ | COGS auto-calculation on stream submit |

---

### Phase 3 — Sales Upload & Auto Deduction ✅ Complete

**Goal:** Close the loop between what sells on stream and what leaves inventory.

| ✅ | Feature |
|---|---|
| ✅ | Sales Upload DocType (manual entry path) |
| ✅ | Streamer + warehouse auto-fill |
| ✅ | Submit → auto Material Issue → inventory deducted |
| ✅ | COGS + gross profit written back to Stream Event |
| ✅ | AI product matching (Ollama) for CSV/recap descriptions |
| ✅ | Whatnot auto-scrape (Playwright + Ollama) |

---

### Phase 4 — Reporting & Visibility 🔄 In Progress

**Goal:** Give management real-time visibility without opening spreadsheets.

| Status | Feature |
|---|---|
| ✅ | Payroll Export report (per-period, per-streamer) |
| ✅ | Loan Balance Ledger report |
| ✅ | Inventory by Streamer report |
| ✅ | Payout Period dashboard (status breakdown, total amounts) |
| ✅ | Stream Event financial KPIs (dashboard indicators) |
| 🔲 | Business-level weekly P&L summary |
| 🔲 | Streamer performance comparison report |
| 🔲 | Inventory turnover / velocity report |

---

### Phase 5 — Automation & Scale 🔲 Planned

**Goal:** Reduce manual steps to near-zero for routine operations.

| Status | Feature |
|---|---|
| 🔲 | Playwright Whatnot scraper (production-ready, fully tested) |
| 🔲 | Scheduled scrape — auto-fetch recaps X hours after show ends |
| 🔲 | Automated Sales Upload approval for high-confidence AI matches |
| 🔲 | Whatnot API integration (when API becomes publicly available) |
| 🔲 | Automated low-stock purchase order suggestions |
| 🔲 | Slack/Discord notifications for payout approvals, low stock, anomalies |

---

## 5. Reporting Requirements

### 5.1 — Payroll Reports

| Report | Audience | Frequency | Status |
|---|---|---|---|
| **Payroll Export** | Accounting | Weekly | ✅ Live |
| ADP CSV per streamer | Accounting | Weekly | ✅ Live |
| Payout summary by period | Management | Weekly | ✅ Live (dashboard) |
| Streamer earnings YTD | Management | Monthly | 🔲 Planned |
| Loan deduction history | Management | On demand | ✅ Loan Balance Ledger |

**Key fields on Payroll Export:**
Streamer, Legal Name, ADP ID, Payout Type, Gross Sales, Share %, Share $, Package Count, Package Rate, Package Pay, Tips, Adjustments, Platform Fee %, Platform Fee $, Loan Deductions, Net Payout, Status

### 5.2 — Inventory Reports

| Report | Audience | Frequency | Status |
|---|---|---|---|
| **Inventory by Streamer** | Operations | Daily/on demand | ✅ Live |
| Stock value by location | Management | Weekly | ✅ (via Inventory page) |
| Low stock items | Operations | Daily | ✅ (badge + report) |
| COGS by stream | Management | Per stream | ✅ (on Stream Event) |
| Inventory turnover | Management | Monthly | 🔲 Planned |

### 5.3 — Business Performance Reports

| Report | Audience | Frequency | Status |
|---|---|---|---|
| Gross sales by streamer | Management | Weekly | 🔲 Planned |
| Net profit per show | Management | Per stream | 🔲 Planned |
| Weekly P&L summary | Owner | Weekly | 🔲 Planned |
| Streamer performance ranking | Management | Monthly | 🔲 Planned |
| Tips trend by streamer | Management | Monthly | 🔲 Planned |

### 5.4 — Operational Reports

| Report | Audience | Frequency | Status |
|---|---|---|---|
| Shows by period | Operations | Weekly | ✅ (Payout Period stream list) |
| AI anomaly flags | Management | Per payout period | ✅ (AI feature) |
| Loan Balance Ledger | Management | On demand | ✅ Live |
| Automation log | Admin | On demand | ✅ (Automation Log DocType) |

---

## 6. System Architecture

### How it all connects

```
                    ┌─────────────────────────────────────────────┐
                    │              Whatnot Platform               │
                    │    (live streaming, sales, show recap)      │
                    └────────────────────┬────────────────────────┘
                              Manual or auto-scrape
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │              Stream Event                   │
                    │   gross_sales · packages · tips · COGS      │
                    └────┬──────────────────────────┬────────────┘
                         │                          │
           ┌─────────────▼──────────┐  ┌────────────▼──────────────┐
           │      Sales Upload      │  │      Payout Period         │
           │  item lines · approval │  │  date range · business     │
           └─────────────┬──────────┘  └────────────┬──────────────┘
                         │                          │
           ┌─────────────▼──────────┐  ┌────────────▼──────────────┐
           │   Material Issue       │  │    Streamer Payout          │
           │  (auto stock entry)    │  │  calc · approve · export   │
           └─────────────┬──────────┘  └────────────┬──────────────┘
                         │                          │
           ┌─────────────▼──────────┐  ┌────────────▼──────────────┐
           │  Streamer Warehouse    │  │       ADP Payroll          │
           │  per-streamer stock    │  │   (external — CSV export)  │
           └────────────────────────┘  └───────────────────────────┘
```

### Two-Business Setup

Both brands operate on the same Vortex Ops instance. Data is separated by:
- **Company** field on Payout Period, Stream Event, and Whatnot Channel
- Streams only appear in payroll for the correct business
- Separate Whatnot Channels with separate login credentials
- Shared streamer records if a person works for both businesses

### AI Integration (Ollama — runs locally, no data leaves the server)

| AI Feature | Trigger | What it does |
|---|---|---|
| **Whatnot Page Parser** | "Fetch from Whatnot" button | Reads page text → extracts totals + item list |
| **Product Matcher** | "Run AI Match" on Sales Upload | Maps informal descriptions to inventory items |
| **Anomaly Detection** | "Run Anomaly Check" on Payout Period | Flags unusual payouts before approval |
| **Stream Summary** | Auto on Stream Event submit | Generates text summary of the show |
| **Low Stock Predictor** | Daily scheduled task | Predicts reorder needs from sales velocity |

---

## 7. Future Expansion Ideas

### Near-term (3–6 months)

**Whatnot API Integration**
When Whatnot opens their API publicly, replace the Playwright scraper with a direct API call. Cleaner, faster, no browser automation required. The Sales Upload workflow stays identical — only the data source changes.

**Seller & Fulfillment Reports**
Currently referenced in the codebase but not fully built. A Seller Report captures what each streamer sold from their personal stock. A Fulfillment Report tracks order packing and shipping. Together they close the loop on inventory accuracy.

**Automated Sales Upload Approval**
When Ollama matches all lines with high confidence, skip the manual approval step and auto-submit. Suitable for experienced streamers with clean product names. Low-confidence or partial matches would still require human review.

**Scheduled Whatnot Scraping**
Set a timer — X hours after a stream ends, the system automatically fetches the Whatnot recap, creates a Sales Upload, runs AI matching, and notifies the operations team that it's ready for approval. Zero manual steps for post-show data entry.

**Slack / Discord Notifications**
Push alerts to the team's communication channel when:
- A payout is ready to approve
- A streamer's inventory hits reorder level
- An AI anomaly is detected in a payout
- A show closes without a Sales Upload after 24 hours

### Medium-term (6–12 months)

**Business Intelligence Dashboard**
An executive-level dashboard showing at a glance:
- Total weekly revenue across both businesses
- Per-streamer performance comparison (gross, net, packages)
- Inventory value trend over time
- Payroll cost as % of revenue
- Top-selling products by category

**Customer Returns Tracking**
Whatnot has buyer disputes and return requests. A returns workflow would:
- Log the return against the original stream and streamer
- Reverse the inventory deduction
- Create an adjustment on the streamer's payout

**Multi-Channel Support**
As the business grows, streamers may stream on additional platforms (TikTok Shop, YouTube Live, etc.). The architecture is designed to accommodate additional channel types alongside Whatnot.

**Purchase Order Workflow**
When a low-stock alert fires, generate a suggested purchase order for the supplier. Track incoming shipments against expected inventory. Auto-receive into Main Storage when the order arrives.

### Long-term

**Streamer Self-Service Portal**
Give each streamer a limited login to ERPNext where they can:
- View their own payout history
- See their current loan balance and repayment schedule
- Check their inventory levels before a show
- Submit their post-show recap directly (replacing the paper form)

**Full Accounting Integration**
Connect the operational data to the platform's accounting module:
- Stream revenue → journal entries
- Payroll → expense entries
- Inventory → balance sheet updates
Eliminates duplicate data entry between operations and bookkeeping.

**Predictive Inventory Ordering**
Use sales velocity data (boxes sold per show, per streamer, per category) to predict inventory needs 2–4 weeks out. Automatically generate reorder suggestions before stock runs out.

---

## 8. Roadmap

```
Q2 2025 ──────────────────────────────────────────────────────────────────
  ✅ Phase 1: Core payroll infrastructure
  ✅ Phase 2: Per-streamer inventory foundation
  ✅ Phase 3: Sales Upload + auto inventory deduction
  ✅ Whatnot scraper (Playwright + Ollama AI extraction)

Q3 2025 ──────────────────────────────────────────────────────────────────
  🔲 Phase 4 (complete): Remaining reports
     - Business P&L summary
     - Streamer performance comparison
     - Inventory turnover
  🔲 Production testing + data migration from spreadsheets
  🔲 Staff training (operations team)
  🔲 Whatnot scraper production hardening + scheduled scraping

Q4 2025 ──────────────────────────────────────────────────────────────────
  🔲 Phase 5: Automation
     - Scheduled scraping (auto-fetch recaps)
     - Auto-approve high-confidence AI matches
     - Slack/Discord notification integration
  🔲 Seller Report + Fulfillment Report DocTypes
  🔲 Whatnot API (if released — replace Playwright scraper)
  🔲 Business intelligence dashboard

Q1 2026 ──────────────────────────────────────────────────────────────────
  🔲 Streamer self-service portal
  🔲 Customer returns workflow
  🔲 Purchase order workflow
  🔲 Multi-channel support (TikTok Shop, etc.)

Q2 2026+ ─────────────────────────────────────────────────────────────────
  🔲 Full accounting integration
  🔲 Predictive inventory ordering
  🔲 Mobile-optimized UI for streamers on the floor
```

---

## Key Decisions & Design Principles

**Why a structured platform instead of custom-built tools?**
The platform provides a battle-tested inventory system (warehouses, stock entries, valuation), a solid permission model, and a web-based UI that works on any device. Building on it means audit trails, user management, and accounting integration are available out of the box — rather than reinventing them.

**Why Ollama (local AI)?**
All AI runs on the server — no data is sent to OpenAI or any cloud service. Product descriptions, sales amounts, and streamer data stay private. The model can be swapped out as better options become available without any code changes.

**Why not replace ADP?**
ADP handles tax calculations, direct deposit, and legal payroll compliance. This system prepares the numbers (calculates net payout per streamer) and exports them in a format ADP can consume. Replacing ADP would require building payroll tax logic for every state — not worth it.

**Two businesses, one system**
Running both brands on one Vortex Ops instance keeps infrastructure costs low and allows shared streamers. Every record is scoped to a Company (business), so data never crosses between the two brands.

---

## Glossary

| Term | Meaning |
|---|---|
| **Stream Event** | One Whatnot live show — can involve 1 or more streamers |
| **Payout Period** | A weekly (or monthly) pay cycle with a start/end date |
| **Streamer Payout** | The calculated payout amount for one streamer in one period |
| **Sales Upload** | Post-show record of what was sold — triggers inventory deduction |
| **Material Issue** | System stock entry that reduces inventory (used for sales deductions) |
| **Material Receipt** | System stock entry that increases inventory (used for receiving stock) |
| **Valuation Rate** | The cost per unit of an item, used to calculate COGS |
| **Owner Platform Fee** | Percentage the business owner takes from each streamer's gross sales |
| **Profit Share** | Payout type: streamer earns X% of their net sales |
| **Package Rate** | Payout type: streamer earns $X per package sold |
| **Ollama** | Local AI model server (runs on-premise, no cloud dependency) |
| **Playwright** | Browser automation tool used to scrape Whatnot show recap pages |
| **ADP** | Third-party payroll processor — receives export from this system |
| **COGS** | Cost of Goods Sold — the inventory cost of items sold in a show |
