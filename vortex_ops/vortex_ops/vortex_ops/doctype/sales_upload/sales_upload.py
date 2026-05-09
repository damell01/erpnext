import frappe
import csv
import io
from frappe.model.document import Document
from frappe.utils import now, today
from vortex_ops.utils import log_automation, safe_float


def validate_doc(doc, method=None):
    if not doc.upload_date:
        doc.upload_date = today()
    if not doc.upload_status:
        doc.upload_status = "Pending"

    # Auto-fill streamer from stream event's primary streamer if blank
    if doc.stream_event and not doc.streamer:
        doc.streamer = frappe.db.get_value(
            "Stream Event", doc.stream_event, "primary_streamer"
        )

    # Auto-fill warehouse on each line from streamer if blank
    if doc.streamer:
        wh = frappe.db.get_value("Streamer", doc.streamer, "warehouse") or ""
        for line in doc.sales_lines:
            if not line.warehouse and wh:
                line.warehouse = wh

    total   = len(doc.sales_lines)
    matched = sum(1 for l in doc.sales_lines if l.item_code)
    doc.total_lines     = total
    doc.matched_lines   = matched
    doc.unmatched_lines = total - matched

    # Compute sale totals and COGS estimate
    total_sale = 0.0
    total_cogs = 0.0
    for line in doc.sales_lines:
        qty = safe_float(line.qty_sold)
        total_sale += safe_float(line.sale_amount)
        if line.item_code:
            val_rate = safe_float(
                frappe.db.get_value("Item", line.item_code, "valuation_rate") or 0
            )
            total_cogs += qty * val_rate
    doc.total_sale_amount  = round(total_sale, 2)
    doc.total_cogs_estimate = round(total_cogs, 2)


def on_submit(doc, method=None):
    if doc.upload_status != "Approved":
        frappe.throw("Upload must be Approved before submitting.")
    _deduct_inventory(doc)


class SalesUpload(Document):

    @frappe.whitelist()
    def parse_csv(self):
        """
        Parse the uploaded file into sales_lines.
        Attempts to auto-detect column names from the header row.
        Falls back gracefully when columns don't match expected names.
        """
        if not self.uploaded_file:
            frappe.throw("Attach a CSV file first")

        file_doc = frappe.get_doc("File", {"file_url": self.uploaded_file})
        content  = file_doc.get_content()

        # Handle bytes vs string
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        reader  = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames or []

        # Flexible column detection — case-insensitive prefix matching
        def find_col(candidates):
            for c in candidates:
                for h in headers:
                    if h.strip().lower().startswith(c.lower()):
                        return h
            return None

        desc_col = find_col(["description", "item", "product", "title", "name"])
        qty_col  = find_col(["qty", "quantity", "count", "units"])
        amt_col  = find_col(["amount", "sale", "price", "revenue", "total"])

        # Default warehouse: primary streamer's warehouse for this stream
        streamer = frappe.db.get_value(
            "Stream Event", self.stream_event, "primary_streamer"
        )
        default_wh = frappe.db.get_value("Streamer", streamer, "warehouse") or ""

        self.sales_lines = []
        row_num = 0
        for row in reader:
            row_num += 1
            desc = (row.get(desc_col, "") if desc_col else "").strip()
            if not desc:
                continue  # skip blank rows
            qty_raw = row.get(qty_col, "1") if qty_col else "1"
            amt_raw = row.get(amt_col, "0") if amt_col else "0"
            self.append("sales_lines", {
                "row_number":      row_num,
                "raw_description": desc,
                "qty_sold":        safe_float(qty_raw, 1.0),
                "sale_amount":     safe_float(
                    str(amt_raw).replace("$", "").replace(",", "")
                ),
                "warehouse":       default_wh,
                "match_status":    "Unmatched",
            })

        self.save()
        undetected = []
        if not desc_col: undetected.append("description")
        if not qty_col:  undetected.append("qty")
        if not amt_col:  undetected.append("amount")

        msg = f"Parsed {len(self.sales_lines)} lines."
        if undetected:
            msg += (
                f" Could not auto-detect columns: {', '.join(undetected)}. "
                "Check the lines table and map manually if needed."
            )
        frappe.msgprint(
            msg,
            indicator="green" if not undetected else "orange",
        )

    @frappe.whitelist()
    def run_ai_match(self):
        from vortex_ops.ai.product_matcher import ai_match_upload
        ai_match_upload(self.name)

    @frappe.whitelist()
    def approve(self):
        if not frappe.user.has_role("Vortex Operations"):
            frappe.throw("Only Vortex Operations can approve uploads")
        self.db_set("upload_status", "Approved")
        self.db_set("reviewed_by",   frappe.session.user)
        self.db_set("reviewed_on",   now())
        frappe.msgprint(
            "Upload approved. Submit the document to deduct inventory.",
            indicator="green",
        )


def _deduct_inventory(doc):
    """
    Create a Material Issue Stock Entry from all matched, approved lines.
    Inventory is deducted from each line's assigned warehouse (streamer-specific).
    COGS is then written back to the linked Stream Event.
    """
    lines = [
        l for l in doc.sales_lines
        if l.item_code and (l.qty_sold or 0) > 0 and l.warehouse
    ]
    if not lines:
        frappe.throw(
            "No matched lines with a warehouse assigned. "
            "Match items and set a warehouse for each line before submitting."
        )

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Issue"
    se.company          = frappe.defaults.get_global_default("company")
    se.remarks          = f"Inventory deduction for Sales Upload {doc.name}"

    for l in lines:
        se.append("items", {
            "item_code":   l.item_code,
            "qty":         l.qty_sold,
            "s_warehouse": l.warehouse,
        })

    se.insert(ignore_permissions=True)
    se.submit()

    total_cogs = sum(i.basic_amount for i in se.items)
    doc.db_set("inventory_processed", 1)
    doc.db_set("upload_status",   "Processed")
    doc.db_set("stock_entry_ref", se.name)

    stream = frappe.get_doc("Stream Event", doc.stream_event)
    stream.update_cogs(total_cogs)

    log_automation(
        "Inventory Deduction", "Sales Upload", doc.name, "Success",
        output_text=f"Stock Entry {se.name} | COGS ${total_cogs:,.2f}",
    )
    frappe.msgprint(
        f"Inventory deducted from streamer warehouse(s). "
        f"Entry: {se.name}. COGS: ${total_cogs:,.2f}",
        indicator="green",
    )
