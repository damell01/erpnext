"""
Central business context for all Ollama AI prompts in Vortex Ops.

Imported by product_matcher, anomaly_detection, stream_summary, and
low_stock_predictor so every AI call shares the same understanding of
how this business actually works.
"""

BUSINESS_CONTEXT = """
BUSINESS OVERVIEW — VORTEX BREAKS
==================================

Vortex Breaks is a Whatnot-based sports card and trading card break business.
Understanding this context is critical for every task you perform.

CHANNEL & STREAMER RELATIONSHIP
--------------------------------
- The business streams primarily from ONE shared main Whatnot channel, not
  separate channels per streamer.
- Multiple streamers work for the business, but they all go live under the
  same channel.
- A single stream (show) may involve ONE streamer or MULTIPLE streamers at
  the same time (co-hosted shows).
- The team currently identifies which streamer(s) were involved by reading
  the Whatnot show title. A show title might say "Jordan Pack Breaks" or
  "Taylor & Morgan TCG Night" — both are on the same main channel.
- You must never assume one channel = one streamer.

CURRENT WORKFLOW (BEING REPLACED BY THIS SYSTEM)
-------------------------------------------------
1. Stream happens on the main Whatnot channel.
2. Team reads the show title to identify which streamer(s) were involved.
3. After the show, Whatnot displays sales totals, amounts earned, and
   other recap data. The team manually records this into spreadsheets.
4. The streamer fills out a paper report sheet after the show with show
   details, sales info, product cost notes, and payout-related information.
5. Data from the paper report and Whatnot recap are entered into multiple
   separate spreadsheets — one or more per streamer.
6. Inventory and product costs are manually updated in spreadsheets.
7. Payouts are manually calculated each week based on each streamer's
   payout type, tips, loans, and any adjustments.

TARGET WORKFLOW (WHAT THIS SYSTEM BUILDS)
-----------------------------------------
1. A Stream Event record is created for each show.
2. Streamer(s) are assigned to the stream (one or more per show).
3. The sales recap sheet from Whatnot (CSV/Excel) is uploaded OR data is
   entered manually into the system.
4. The operations team reviews the uploaded sales line items.
5. After approval, the system automatically deducts inventory from the
   correct streamer's warehouse location.
6. Payout summaries are generated for each streamer based on their
   payout type, tips, loans, and adjustments.
7. The payout summary is reviewed and sent to payroll — the system does
   NOT replace payroll (e.g. ADP), it prepares the numbers for it.

INVENTORY STRUCTURE
--------------------
Inventory is tracked per streamer or per physical location, not as a single
shared pool. Example warehouse structure:
  - Main Storage          (general incoming stock)
  - Jordan Inventory      (stock assigned to Jordan)
  - Taylor Inventory      (stock assigned to Taylor)
  - Morgan Inventory      (stock assigned to Morgan)
  - Returned Inventory    (customer returns)
  - Damaged Inventory     (damaged / write-off stock)

When a streamer sells items during a show, inventory is deducted from THEIR
specific warehouse, not from Main Storage. This is critical for accurate
per-streamer inventory and COGS tracking.

PAYOUT TYPES
-------------
Streamers are NOT all paid the same way. The system must handle all of:
  - Profit Share: streamer earns a % of net sales (e.g. 15% of net earned)
  - Per Package: streamer earns a flat dollar amount per package sold
  - Hourly: streamer earns a set hourly rate (time-tracked separately)
  - Flat Rate: fixed amount per stream regardless of sales volume
  - Tips: tips may be added on top of base payout (toggle per streamer)
  - Loan Deductions: outstanding loans are deducted from payout
  - Owner Platform Fee: the business owner takes a percentage from each
    streamer's gross sales as a platform/overhead fee
  - Adjustments: one-off manual additions or deductions with a reason

WHAT THIS SYSTEM IS AND IS NOT
--------------------------------
IS:   A central operations database replacing spreadsheets and paper reports.
IS:   An inventory tracker per streamer/location.
IS:   A payout summary generator (review-before-send, not auto-pay).
IS:   A sales upload processor with AI-assisted item matching.
IS NOT: A replacement for Whatnot (the streaming/selling platform).
IS NOT: A payroll system (ADP or similar handles final payroll).
IS NOT: An accounting system (ERPNext handles general ledger separately).

PRODUCT CATALOG
----------------
Products are sports cards, trading card game (TCG) packs, sealed wax boxes,
cases, memorabilia, and mystery lots. Descriptions from Whatnot recap sheets
are often abbreviated, informal, or incomplete. Examples:
  "2024 Prizm Blaster" → 2024 Panini Prizm Basketball Blaster Box
  "Optic hobby" → 2024 Panini Donruss Optic Hobby Box
  "1/1 Jordan auto" → Michael Jordan 1/1 Autograph Card
Use common sports card industry knowledge when matching descriptions.
"""


def get_context():
    """Return the full business context string for use in AI system prompts."""
    return BUSINESS_CONTEXT


def get_context_brief():
    """Return a short version for prompts where token count matters."""
    return (
        "Context: Vortex Breaks is a Whatnot card break business. "
        "Multiple streamers share one main channel. A show may have 1+ streamers, "
        "identified from the show title. Inventory is tracked per streamer warehouse "
        "(e.g. 'Jordan Inventory'). Payout types vary: profit share, per package, "
        "hourly, flat rate, tips, loan deductions, owner platform fee. "
        "This system replaces spreadsheets and paper reports — it does NOT replace "
        "Whatnot or payroll."
    )
