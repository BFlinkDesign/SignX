"""
Mail Classifier — Dual email classification for Eagle Sign Co.

Flow 1 (BID-INTAKE): Regex parser for KeyedIn system emails with
    subject pattern "Quote #NNNNN - BID REQUEST".
Flow 2 (CORRESPONDENCE): Claude Haiku classifier for all other emails.

Both flows route to Notion databases:
  - Bid Pipeline: 304c1e58d2dd814aae63c6a0d44e6679
  - Correspondence Log: 309c1e58d2dd81ef9871d22f0e82a6f1
  - Variation Register: 309c1e58d2dd815a9a44edd9442c2a77
"""

import json
import os
import re
from datetime import date
from pathlib import Path

import anthropic
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_API_VERSION = "2022-06-28"

BID_PIPELINE_DB = "304c1e58d2dd814aae63c6a0d44e6679"
CORR_LOG_DB = "309c1e58d2dd81ef9871d22f0e82a6f1"
VAR_REG_DB = "309c1e58d2dd815a9a44edd9442c2a77"

# ---------------------------------------------------------------------------
# Flow 1 — Regex-based bid intake parser
# ---------------------------------------------------------------------------

BID_INTAKE_PATTERN = re.compile(
    r"Quote\s*#\s*(\d{5})\s*[-\u2013\u2014]\s*(BID REQUEST|REDO BID|ON HOLD)",
    re.IGNORECASE,
)

# Sign type keywords → Notion select values
_SIGN_TYPE_KEYWORDS = {
    "emc": {
        "monument": "EMC_MONUMENT",
        "pole": "EMC_POLE",
        "retrofit": "EMC_RETROFIT",
    },
    "channel letter": "CHANNEL_LETTERS",
    "channel logo": "CHANNEL_LOGO",
    "monument": "MONUMENT_BASE",
    "manual reader": "MONUMENT_MANUAL_READER",
    "cabinet": "CABINET_ILLUMINATED",
    "info panel": "INFO_PANEL",
    "masonry": "MASONRY_SUB",
    "removal": "REMOVAL",
    "structural": "STRUCTURAL_BASE",
}

# Salesman name normalization
_SALESMAN_ALIASES = {
    "jeff": "Jeff Fye",
    "jeff fye": "Jeff Fye",
    "joe": "Joe Phillips",
    "joe phillips": "Joe Phillips",
    "rich": "Rich Thompson",
    "rich thompson": "Rich Thompson",
    "chris": "Chris Erickson",
    "chris erickson": "Chris Erickson",
    "house": "House",
}

# Blocking item keywords
_BLOCKING_KEYWORDS = {
    "watchfire": "watchfire_pricing",
    "daktronics": "watchfire_pricing",
    "drawing": "needs_drawings",
    "plan": "needs_drawings",
    "spec": "needs_specs",
    "specification": "needs_specs",
    "masonry": "masonry_sub_quote",
    "brick": "masonry_sub_quote",
    "stone": "masonry_sub_quote",
}


def _detect_sign_type(text: str) -> str | None:
    """Detect sign type from text using keyword matching."""
    lower = text.lower()
    # EMC subtypes first (more specific)
    if "emc" in lower or "electronic message" in lower or "led display" in lower:
        for kw, st in _SIGN_TYPE_KEYWORDS["emc"].items():
            if kw in lower:
                return st
        return "EMC"
    for kw, st in _SIGN_TYPE_KEYWORDS.items():
        if kw == "emc":
            continue
        if isinstance(st, str) and kw in lower:
            return st
    return None


def _detect_salesman(text: str) -> str | None:
    """Detect salesman from email body or sender."""
    lower = text.lower()
    for alias, name in _SALESMAN_ALIASES.items():
        if alias in lower:
            return name
    return None


def _detect_blocking(text: str) -> list[str]:
    """Detect blocking items from text."""
    lower = text.lower()
    found = set()
    for kw, block in _BLOCKING_KEYWORDS.items():
        if kw in lower:
            found.add(block)
    return sorted(found)


def _extract_dollar_amount(text: str) -> float | None:
    """Extract the first significant dollar amount from text."""
    amounts = re.findall(r"\$\s*([\d,]+(?:\.\d{2})?)", text)
    for raw in amounts:
        val = float(raw.replace(",", ""))
        if val > 1.0:  # Skip $1.00 KeyedIn placeholders
            return val
    return None


def _extract_date(text: str) -> str | None:
    """Extract a date from text in various formats."""
    # YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    # MM/DD/YYYY or MM-DD-YYYY
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _extract_location(text: str) -> str | None:
    """Extract city, state from text."""
    # Common patterns: "City, ST" or "City, State"
    m = re.search(
        r"(?:location|city|site|project)\s*[:\-]?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # Standalone "City, ST" pattern
    m = re.search(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*(?:IA|IL|MN|NE|SD|WI|MO|KS))\b", text)
    if m:
        return m.group(1).strip()
    return None


def _extract_customer(text: str) -> str | None:
    """Extract customer name from text."""
    m = re.search(
        r"(?:customer|company|client|for)\s*[:\-]?\s*([A-Z][A-Za-z0-9\s&'.,-]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        name = m.group(1).strip().rstrip(",.-")
        # Stop at common terminators
        for stop in ["location", "salesman", "description", "sign type", "\n"]:
            idx = name.lower().find(stop)
            if idx > 0:
                name = name[:idx].strip().rstrip(",.-")
        if len(name) > 2:
            return name
    return None


def _extract_crm_id(text: str) -> str | None:
    """Extract CRM ID (e.g., 'CRM-12345' or similar)."""
    m = re.search(r"(?:CRM|crm)[\s#-]*(\w+)", text)
    if m:
        return m.group(1)
    return None


def parse_bid_intake(
    subject: str, body: str, sender: str, received: str
) -> dict:
    """
    Flow 1: Parse a KeyedIn bid request email via regex.
    Returns a dict matching the Notion Bid Pipeline schema.
    """
    m = BID_INTAKE_PATTERN.search(subject)
    if not m:
        raise ValueError(f"Subject does not match BID_INTAKE_PATTERN: {subject!r}")

    quote_number = m.group(1)
    action = m.group(2).upper()
    is_redo = action == "REDO BID"

    combined = f"{subject}\n{body}\n{sender}"

    customer = _extract_customer(body)
    location = _extract_location(body)
    salesman = _detect_salesman(combined) or _detect_salesman(sender)
    sign_type = _detect_sign_type(body)
    est_value = _extract_dollar_amount(body)
    delivery_date = _extract_date(body)
    crm_id = _extract_crm_id(body)
    blocking = _detect_blocking(body)
    has_drawings = bool(
        re.search(r"\b(drawing|plan|blueprint|spec|specification)\b", body, re.IGNORECASE)
    )

    # Build description from body (first meaningful paragraph)
    desc_lines = [
        ln.strip()
        for ln in body.split("\n")
        if ln.strip() and not ln.strip().startswith(("From:", "To:", "Sent:", "Subject:", "Date:"))
    ]
    description = " ".join(desc_lines[:3])[:500] if desc_lines else ""

    return {
        "flow": "bid_intake",
        "quote_number": quote_number,
        "quote_name": f"Q{quote_number} - {customer or 'New Bid'}",
        "customer": customer,
        "location": location,
        "salesman": salesman,
        "crm_id": crm_id,
        "sign_type": sign_type,
        "estimated_value": est_value,
        "description": description,
        "delivery_date": delivery_date,
        "is_redo": is_redo,
        "has_drawings": has_drawings,
        "blocking": blocking,
        "email_received": received or str(date.today()),
        "pipeline_stage": "INTAKE",
        "status": "REDO BID REQUEST" if is_redo else "BID REQUEST",
        "blocking_owner": "brady",
        "value_source": "estimated" if est_value else None,
        "sq_ft": None,
        "faces": None,
        "pixel_pitch": None,
        "cabinet_dims": None,
        "takeoff_done": False,
        "quoted": False,
        "job_complete": False,
    }


# ---------------------------------------------------------------------------
# Flow 2 — Claude Haiku correspondence classifier
# ---------------------------------------------------------------------------

CLASSIFIER_SYSTEM_PROMPT = """\
You are a correspondence classifier for Eagle Sign Co., a commercial sign fabrication and installation company in Des Moines, Iowa. You classify inbound emails into structured fields for a Notion database.

## SIGN INDUSTRY CONTEXT
Eagle Sign designs, manufactures, installs, and services commercial signage. Their work involves:
- Channel letters, monument signs, cabinet signs, LED displays, plaques
- General contractors (GCs) subcontract sign installation to Eagle Sign
- Vendors supply raw materials (aluminum, acrylic, LEDs) and fabricated components
- Customers are end clients (restaurants, hospitals, churches, retail chains)
- National sign companies (Silicon Signs, Vixxo) subcontract local install/permit work to Eagle Sign
- Projects go through: bid → design → permit → fabrication → install → service

## CLASSIFICATION FIELDS

### Type (pick ONE — classify by the PRIMARY purpose of the email thread):
- RFI: Questions asking for info, status updates, "what are we waiting on", follow-up inquiries. The core action is ASKING a question.
- Quote: Pricing proposals, bid responses, vendor material quotes, cost breakdowns, quoting threads. If the email subject contains "Quote" and the thread is fundamentally about quoting/pricing materials (ordering, pricing sheets, lead times), classify as Quote even if the latest message is a follow-up question.
- Instruction: Proceed orders, approvals to move forward, install dates/schedules, scope directives from GCs, construction schedule distributions to subcontractors. A GC or customer TELLING Eagle Sign what to do or when. If a GC is awarding work, providing detailed scope, AND negotiating price down in the same message, classify as Instruction (the award/scope is the primary purpose; the price negotiation is secondary).
- Variation: Price disputes on EXISTING quoted scope, "why did price increase" on unchanged specs. Use ONLY when the primary purpose is disputing or challenging a price change on previously-agreed scope. Do NOT use for initial price negotiation on new bids.
- Delay: Schedule slips, backorders, "behind schedule", "ship later than anticipated", site not ready
- Info: FYI messages, general status updates, correspondence that doesn't fit other categories
- Invoice: Billing documents, PO references, payment requests, "amount due"
- Service: Warranty claims, repair requests, maintenance, "incorrect colors", product defect reports
- Permit: City/municipal feedback, permit approvals/denials, inspection results, approved documents from government agencies

### Sender Type (pick ONE):
- customer: End client who commissioned the signage (e.g., Shannon Krauss/Pancheros, restaurant owners)
- gc: General contractor or national sign company managing the project (e.g., Silicon Signs, Team DeNovo, Vixxo)
- vendor: Material supplier or fabrication subcontractor (e.g., OSH Cut, Direct Sign Wholesale, Gemini, Ryerson)
- internal: Eagle Sign staff (Jeff Fye, Brady Flink, Jessie Fasselius, Rich Thompson, Matt Reis, Chad, Jessica Wilmot)
- government: City/municipal/state agency staff (e.g., Emani Brinkman/City of WDM, Andy Kass/City of Waukee)
- unknown: Cannot determine sender affiliation

### FORWARD DETECTION RULE (CRITICAL):
If the email subject contains "FW:" or "Fw:", the email was forwarded by an Eagle Sign employee. You MUST identify the ORIGINAL sender — the deepest/earliest message in the thread — NOT the Eagle Sign forwarder.
- Jeff Fye forwarding a city email → sender_type = "government", from = original city sender
- Jeff Fye forwarding a GC email → sender_type = "gc", from = original GC sender
- Rich Thompson forwarding a vendor email → sender_type = "vendor", from = original vendor
- ONLY classify as "internal" if the original author (deepest in thread) is Eagle Sign staff AND the email is addressed to other Eagle Sign staff as the primary content

However: If an internal Eagle Sign person authored the TOPMOST message with substantial original content (not just "see below" or "FYI"), AND the email is primarily about their own request/instructions to another Eagle Sign employee, then sender_type = "internal" and from = that Eagle Sign person. The key test: who wrote the substantive content that defines the email's purpose?

### Urgency:
- high: Explicit deadline mentioned, "urgent", "ASAP", grand opening date, "!!!" in subject, install date within 2 weeks, GC schedule update with specific install dates for subcontractors
- medium: Timeline referenced but not critical, "tomorrow or Friday", general schedule discussion
- low: No time pressure, routine correspondence, standard invoices without same-day urgency, permit approvals sent as FYI (no action deadline), routine vendor account inquiries

### Special Rules:
1. Type=Delay → ALWAYS set requires_action=true
2. Type=Variation → ALWAYS set flagged=true
3. Type=Instruction → ALWAYS set flagged=true
4. Price negotiation language ("lower by", "budget is $X", "above the others", "why did price increase", "what is driving the price") → set scope_change=true. ANY challenge to pricing on existing or previously-quoted scope = scope_change=true.
5. Adding/removing/changing work scope after initial bid → set scope_change=true
6. When a party offers to supply materials themselves ("we can supply the faces") or modify who does what work, that IS a scope change → set scope_change=true
7. If someone is waiting on Eagle Sign to respond, provide info, or take action → requires_action=true

### Prices Mentioned:
Extract SIGNIFICANT dollar amounts — prices, totals, line item costs. Include the $ sign.
EXCLUDE per-unit rates under $50 from product spec sheets (e.g., "$9", "$23.5", "$12.89" are unit rates, not prices).
Focus on: total amounts, quoted prices, negotiation figures, invoice totals, budget figures.
Return as a JSON array of strings. If no prices, return [].

### Quote Numbers:
Look for 5-digit numbers in the 40xxx series (e.g., 40592, 40639). List them in the summary.

### Scope Creep Detection:
Detect scope creep — when someone tries to add work beyond the original scope.
Trigger phrases: "while you're out there", "can you also", "slight change", "add to the scope",
"just one more thing", "it should only take", "while we're at it", "quick addition", "small enhancement"

### Confidence:
0.0 to 1.0 — how confident you are in the Type classification.
- 0.95+: Clear-cut, unambiguous classification
- 0.80-0.94: Strong classification with minor ambiguity
- 0.60-0.79: Could reasonably be another type
- Below 0.60: Very uncertain

## DISAMBIGUATION RULES (apply these in order when classification is ambiguous):

1. RFI vs Quote: If the MOST RECENT message is someone ASKING for a cost breakdown, requesting pricing details, or asking questions about a quote — that is an RFI, not a Quote. A Quote is when someone is PROVIDING pricing. Exception: if the subject contains "Quote" and the thread is fundamentally a material ordering/pricing thread with a vendor, classify as Quote.

2. Instruction vs Variation: When a GC simultaneously awards work AND negotiates price, classify as Instruction. The award/scope directive is the primary action; price negotiation is a condition of the award, not a dispute on existing scope. Variation requires a PREVIOUSLY AGREED price being challenged after the fact ("why did the price increase on unchanged specs").

3. Invoice urgency: Standard invoices with payment terms (net-30, 50% down) are urgency=low unless the email explicitly uses words like "urgent", "overdue", or "past due". Having a due date on an invoice is normal business, not urgency.

4. Permit urgency: Permit approvals sent as informational documents are urgency=low unless there's a specific action deadline mentioned.

## OUTPUT FORMAT
Return ONLY valid JSON with these exact keys:
{
  "subject": "email subject line exactly as given",
  "from_name": "Original sender full name",
  "from_email": "original sender email address",
  "date": "YYYY-MM-DD of the most recent message in thread",
  "type": "one of: RFI|Quote|Instruction|Variation|Delay|Info|Invoice|Service|Permit",
  "sender_type": "one of: customer|gc|vendor|internal|government|unknown",
  "urgency": "one of: low|medium|high",
  "summary": "1-sentence summary including any quote numbers found",
  "confidence": 0.95,
  "flagged": false,
  "scope_change": false,
  "requires_action": false,
  "prices_mentioned": ["$100.00"],
  "scope_creep_detected": false,
  "scope_creep_summary": null,
  "related_quote_number": null
}
"""

# Scope creep trigger phrases
SCOPE_CREEP_PHRASES = [
    "while you're out there",
    "can you also",
    "slight change",
    "add to the scope",
    "just one more thing",
    "it should only take",
    "while we're at it",
    "quick addition",
    "small enhancement",
]


def classify_email(email_text: str) -> dict:
    """Classify a single email using Claude Haiku. Returns structured dict."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Classify this email:\n\n{email_text}"}],
    )
    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # Extract first JSON object via brace matching
    start = text.index("{")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                text = text[start : i + 1]
                break

    return json.loads(text)


# ---------------------------------------------------------------------------
# Notion integration
# ---------------------------------------------------------------------------

def _notion_headers() -> dict:
    """Standard Notion API headers."""
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def create_bid_pipeline_entry(fields: dict) -> str:
    """
    Create a Notion page in the Bid Pipeline DB.
    Accepts the dict returned by parse_bid_intake().
    Returns the Notion page ID.
    """
    properties: dict = {
        "Quote #": {"title": [{"text": {"content": fields.get("quote_name", "New Bid")}}]},
        "Customer": {"rich_text": [{"text": {"content": fields.get("customer", "") or ""}}]},
        "Description": {"rich_text": [{"text": {"content": (fields.get("description", "") or "")[:2000]}}]},
        "Pipeline Stage": {"select": {"name": fields.get("pipeline_stage", "INTAKE")}},
        "Status": {"select": {"name": fields.get("status", "BID REQUEST")}},
        "Blocking Owner": {"select": {"name": fields.get("blocking_owner", "brady")}},
        "Is Redo": {"checkbox": fields.get("is_redo", False)},
        "\u2705 Takeoff Done": {"checkbox": fields.get("takeoff_done", False)},
        "\u2705 Quoted": {"checkbox": fields.get("quoted", False)},
        "\u2705 Job Complete": {"checkbox": fields.get("job_complete", False)},
    }

    # Optional text fields
    if fields.get("location"):
        properties["Location"] = {"rich_text": [{"text": {"content": fields["location"]}}]}
    if fields.get("cabinet_dims"):
        properties["Cabinet Dims"] = {"rich_text": [{"text": {"content": fields["cabinet_dims"]}}]}
    if fields.get("crm_id"):
        properties["CRM ID"] = {"rich_text": [{"text": {"content": fields["crm_id"]}}]}

    # Optional select fields
    if fields.get("salesman"):
        properties["Salesman"] = {"select": {"name": fields["salesman"]}}
    if fields.get("sign_type"):
        properties["Sign Type"] = {"select": {"name": fields["sign_type"]}}
    if fields.get("value_source"):
        properties["Value Source"] = {"select": {"name": fields["value_source"]}}

    # Optional multi-select
    if fields.get("blocking"):
        properties["Blocking"] = {
            "multi_select": [{"name": b} for b in fields["blocking"]]
        }

    # Optional number fields
    if fields.get("estimated_value") is not None:
        properties["Est. Value"] = {"number": fields["estimated_value"]}
    if fields.get("sq_ft") is not None:
        properties["Sq Ft"] = {"number": fields["sq_ft"]}
    if fields.get("faces") is not None:
        properties["Faces"] = {"number": fields["faces"]}
    if fields.get("pixel_pitch") is not None:
        properties["Pixel Pitch (mm)"] = {"number": fields["pixel_pitch"]}

    # Optional date fields
    if fields.get("email_received"):
        properties["Email Received"] = {"date": {"start": fields["email_received"]}}
    if fields.get("delivery_date"):
        properties["Delivery Date"] = {"date": {"start": fields["delivery_date"]}}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_notion_headers(),
        json={"parent": {"database_id": BID_PIPELINE_DB}, "properties": properties},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def create_correspondence_entry(classification: dict) -> str:
    """
    Create a Correspondence Log page in Notion.
    Accepts the dict returned by classify_email().
    Returns the Notion page ID.
    """
    from_str = classification.get("from_name", "")
    from_email = classification.get("from_email", "")
    if from_email:
        from_str = f"{from_str} <{from_email}>"

    prices = classification.get("prices_mentioned", [])
    prices_json = json.dumps(prices) if prices else "[]"

    properties = {
        "Subject": {"title": [{"text": {"content": classification.get("subject", "")}}]},
        "Date": {"date": {"start": classification.get("date", str(date.today()))}},
        "From": {"rich_text": [{"text": {"content": from_str}}]},
        "Type": {"select": {"name": classification["type"]}},
        "Summary": {"rich_text": [{"text": {"content": classification.get("summary", "")}}]},
        "Confidence": {"number": classification.get("confidence", 0.0)},
        "Flagged": {"checkbox": classification.get("flagged", False)},
        "Status": {"select": {"name": "New"}},
        "Sender Type": {"select": {"name": classification["sender_type"]}},
        "Urgency": {"select": {"name": classification["urgency"]}},
        "Prices Mentioned": {"rich_text": [{"text": {"content": prices_json}}]},
        "Scope Change": {"checkbox": classification.get("scope_change", False)},
        "Requires Action": {"checkbox": classification.get("requires_action", False)},
    }

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_notion_headers(),
        json={"parent": {"database_id": CORR_LOG_DB}, "properties": properties},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def create_variation_entry(
    description: str,
    date_identified: str,
    status: str,
    value: float,
    source_corr_id: str | None = None,
) -> str:
    """Create a Variation Register page. Returns page ID."""
    properties: dict = {
        "Description": {"title": [{"text": {"content": description}}]},
        "Date Identified": {"date": {"start": date_identified}},
        "Status": {"select": {"name": status}},
        "Value": {"number": value},
    }
    if source_corr_id:
        properties["Source Correspondence"] = {"relation": [{"id": source_corr_id}]}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=_notion_headers(),
        json={"parent": {"database_id": VAR_REG_DB}, "properties": properties},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def link_to_bid_pipeline(quote_number: str, corr_page_id: str) -> str | None:
    """
    Query the Bid Pipeline for a matching quote number, then add a relation
    from the correspondence page to the bid pipeline page.
    Returns the bid pipeline page ID if found, else None.
    """
    # Query Bid Pipeline for pages whose title contains the quote number
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{BID_PIPELINE_DB}/query",
        headers=_notion_headers(),
        json={
            "filter": {
                "property": "Quote #",
                "title": {"contains": quote_number},
            },
            "page_size": 5,
        },
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        return None

    bid_page_id = results[0]["id"]

    # Update the correspondence page to link to the bid pipeline page
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{corr_page_id}",
        headers=_notion_headers(),
        json={
            "properties": {
                "Related Bid": {"relation": [{"id": bid_page_id}]},
            }
        },
        timeout=30,
    )
    # Don't raise on relation errors — the property may not exist yet
    if resp.status_code == 200:
        return bid_page_id
    return bid_page_id  # Still return ID even if relation update fails


# ---------------------------------------------------------------------------
# Router — classify_and_route()
# ---------------------------------------------------------------------------

def classify_and_route(
    subject: str,
    body: str,
    sender: str,
    received: str,
    folder: str = "",
    attachments: list | None = None,
) -> dict:
    """
    Main entry point. Routes email to Flow 1 (bid intake) or Flow 2 (correspondence).

    Returns a dict with:
      - flow: "bid_intake" or "correspondence"
      - classification or parsed fields
      - notion_page_id (if Notion write succeeds)
      - Any additional metadata
    """
    attachments = attachments or []

    # ── Flow 1: Check for bid intake pattern ──
    m = BID_INTAKE_PATTERN.search(subject)
    if m:
        fields = parse_bid_intake(subject, body, sender, received)

        # Enrich with attachment info
        attachment_names = [a if isinstance(a, str) else a.get("name", "") for a in attachments]
        if any(
            re.search(r"\b(drawing|plan|blueprint|spec)\b", name, re.IGNORECASE)
            for name in attachment_names
        ):
            fields["has_drawings"] = True

        # Write to Notion (skip if no token configured)
        notion_page_id = None
        if NOTION_TOKEN:
            try:
                notion_page_id = create_bid_pipeline_entry(fields)
            except Exception as exc:
                fields["notion_error"] = str(exc)

        fields["notion_page_id"] = notion_page_id
        return fields

    # ── Flow 2: Claude Haiku correspondence classifier ──
    email_text = f"SUBJECT: {subject}\nFROM: {sender}\nDATE: {received}\nFOLDER: {folder}\n\n{body}"
    classification = classify_email(email_text)

    # Ensure new fields exist with defaults
    classification.setdefault("scope_creep_detected", False)
    classification.setdefault("scope_creep_summary", None)
    classification.setdefault("related_quote_number", None)

    # Fallback scope creep detection if Haiku missed it
    lower_body = body.lower()
    if not classification["scope_creep_detected"]:
        for phrase in SCOPE_CREEP_PHRASES:
            if phrase in lower_body:
                classification["scope_creep_detected"] = True
                classification["scope_creep_summary"] = (
                    f"Scope creep detected: '{phrase}' found in email body."
                )
                break

    # Fallback quote number extraction
    if not classification.get("related_quote_number"):
        qn_match = re.search(r"\b(4\d{4})\b", body)
        if qn_match:
            classification["related_quote_number"] = qn_match.group(1)

    result = {
        "flow": "correspondence",
        "classification": classification,
        "notion_page_id": None,
        "variation_page_id": None,
    }

    # Write to Notion
    if NOTION_TOKEN:
        try:
            corr_page_id = create_correspondence_entry(classification)
            result["notion_page_id"] = corr_page_id

            # If variation detected, create variation register entry
            if classification.get("type") == "Variation":
                prices = classification.get("prices_mentioned", [])
                value = 0.0
                if prices:
                    # Try to parse first price as value
                    raw = prices[0].replace("$", "").replace(",", "")
                    try:
                        value = float(raw)
                    except ValueError:
                        pass
                var_id = create_variation_entry(
                    description=classification.get("summary", "Variation detected"),
                    date_identified=classification.get("date", str(date.today())),
                    status="Proposed",
                    value=value,
                    source_corr_id=corr_page_id,
                )
                result["variation_page_id"] = var_id

            # If related quote number found, link to bid pipeline
            if classification.get("related_quote_number") and result["notion_page_id"]:
                link_to_bid_pipeline(
                    classification["related_quote_number"],
                    result["notion_page_id"],
                )

        except Exception as exc:
            result["notion_error"] = str(exc)

    return result
