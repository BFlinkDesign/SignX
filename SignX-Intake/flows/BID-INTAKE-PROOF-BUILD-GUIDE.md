# BID-INTAKE-PROOF — Power Automate Build Guide

**Flow name:** `BID-INTAKE-PROOF`
**Scope:** Jeff Fye subfolder ONLY (Phase 1 proof of concept)
**Created:** 2026-02-15

---

## Prerequisites

- [ ] Phase 0 manual checklist items 0.A through 0.E completed
- [ ] Anthropic API key available (from `.env` or password manager)
- [ ] Notion integration token available (from `.env` — `NOTION_TOKEN`)
- [ ] Notion DB ID: `304c1e58d2dd814aae63c6a0d44e6679`

---

## Flow Architecture

```
TRIGGER: When a new email arrives (V3) [Office 365 Outlook]
  |
  v
STEP 1: Html to text [Content Conversion]
  |
  v
STEP 2: Compose [Data Operations] — Build API request body
  |
  v
STEP 3: HTTP [HTTP connector] — POST to Anthropic API
  |
  v
STEP 4: Parse JSON — Extract Claude text response from API envelope
  |
  v
STEP 5: Parse JSON — Parse extraction fields from Claude's JSON
  |
  v
STEP 6: Create a Page [Notion] — Write row to Bid Pipeline DB
  |
  v
STEP 7: (Optional) Mark as read / move to processed subfolder
```

---

## Step-by-Step Build Instructions

### TRIGGER: When a new email arrives (V3)

1. In Power Automate, click **+ Create** → **Automated cloud flow**
2. Flow name: `BID-INTAKE-PROOF`
3. Trigger: search **"When a new email arrives (V3)"** → select **Office 365 Outlook**
4. Configure trigger:

| Field | Value |
|-------|-------|
| Folder | `Inbox/BID REQUEST/Jeff Fye` |
| Include Attachments | Yes |
| Subject Filter | *(leave blank — catch all)* |
| Importance | Any |
| Only with Attachments | No |
| From | *(leave blank)* |

5. Click **New step**

---

### STEP 1: Html to text (Content Conversion)

1. Search for **"Html to text"** → select **Content Conversion** connector
2. Configure:

| Field | Value |
|-------|-------|
| Content | Click "Add dynamic content" → select **Body** (from trigger) |

This converts the HTML email body to plain text for Claude to parse.

---

### STEP 2: Compose (Build API Request Body)

1. Search for **"Compose"** → select **Data Operations - Compose**
2. Click **Inputs** field, then switch to **Expression** mode (click the `fx` button)
3. Paste this expression EXACTLY:

```
json(concat('{"model":"claude-sonnet-4-5-20250929","max_tokens":500,"temperature":0,"system":"You are a bid request parser for Eagle Sign Co., a commercial sign manufacturer.\\nExtract project details from this bid request email. Return ONLY valid JSON, no markdown, no backticks.\\n\\n{\\n  \\"quote_name\\": \\"short descriptive project name\\",\\n  \\"customer\\": \\"company or person name requesting the sign\\",\\n  \\"location\\": \\"city, state if mentioned, else null\\",\\n  \\"sign_type\\": \\"one of: EMC_MONUMENT, EMC_POLE, EMC_RETROFIT, EMC, CHANNEL_LETTERS, CHANNEL_LOGO, MONUMENT_BASE, MONUMENT_MANUAL_READER, CABINET_ILLUMINATED, INFO_PANEL, MASONRY_SUB, REMOVAL, STRUCTURAL_BASE, or null\\",\\n  \\"estimated_value\\": \\"dollar amount as number if mentioned, else null\\",\\n  \\"description\\": \\"1-3 sentence summary of what they need\\",\\n  \\"sq_ft\\": \\"number if sign dimensions mentioned (calculate from WxH), else null\\",\\n  \\"faces\\": \\"number of sign faces if mentioned (typically 1 or 2), else null\\",\\n  \\"cabinet_dims\\": \\"W x H format if cabinet dimensions mentioned, else null\\",\\n  \\"pixel_pitch\\": \\"number in mm if EMC pixel pitch mentioned, else null\\",\\n  \\"delivery_date\\": \\"YYYY-MM-DD if deadline mentioned, else null\\",\\n  \\"is_redo\\": \\"true if re-bid or revision of previous quote, else false\\",\\n  \\"has_drawings\\": \\"true if email mentions attached drawings/plans/specs\\",\\n  \\"has_specs\\": \\"true if email mentions specifications document\\",\\n  \\"blocking\\": \\"list from [watchfire_pricing, needs_drawings, needs_specs, masonry_sub_quote] or []\\"\\n}\\n\\nRules:\\n- If sign_type is unclear, use null.\\n- For EMC projects, extract pixel pitch from specs.\\n- is_redo = true ONLY if email explicitly references a previous quote or says re-bid/revise.\\n- estimated_value: only if email states a budget. Do not fabricate.\\n- MASONRY_SUB = primarily masonry/brick/stone work for a sign base.\\n- REMOVAL = sign removal, demolition, or decommission job.\\n- STRUCTURAL_BASE = structural foundation, pole, or mounting structure only.","messages":[{"role":"user","content":"SALESPERSON: Jeff Fye\\nSUBJECT: ',replace(replace(triggerOutputs()?['body/subject'],'"','\\"'),decodeUriComponent('%0A'),'\\n'),'\\nFROM: ',replace(replace(triggerOutputs()?['body/from'],'"','\\"'),decodeUriComponent('%0A'),'\\n'),'\\nDATE: ',triggerOutputs()?['body/receivedDateTime'],'\\n\\nEMAIL BODY:\\n',replace(replace(body(''Html_to_text'')?[''body''],'"','\\"'),decodeUriComponent('%0A'),'\\n'),'"}]}'))
```

**IMPORTANT NOTES on the Compose expression:**
- The expression builds a complete Anthropic API request as JSON
- `replace(..., '"', '\\"')` escapes quotes in the email content
- `replace(..., decodeUriComponent('%0A'), '\\n')` escapes newlines
- `body('Html_to_text')?['body']` references Step 1's output
- If PA shows a syntax error, check that single quotes around action names match exactly (e.g., `'Html_to_text'`)

**ALTERNATIVE (simpler but longer):** If the expression is too complex, split into multiple Compose steps:
1. **Compose_Subject**: `replace(replace(triggerOutputs()?['body/subject'],'"','\\"'),decodeUriComponent('%0A'),'\\n')`
2. **Compose_From**: `replace(replace(triggerOutputs()?['body/from'],'"','\\"'),decodeUriComponent('%0A'),'\\n')`
3. **Compose_Body**: `replace(replace(body('Html_to_text')?['body'],'"','\\"'),decodeUriComponent('%0A'),'\\n')`
4. **Compose_Request**: Build the final JSON referencing `outputs('Compose_Subject')`, etc.

---

### STEP 3: HTTP — Call Anthropic API

1. Search for **"HTTP"** → select **HTTP** (Premium connector)
2. Configure:

| Field | Value |
|-------|-------|
| Method | `POST` |
| URI | `https://api.anthropic.com/v1/messages` |
| Headers | *(see below)* |
| Body | Click "Add dynamic content" → select **Outputs** from Step 2 (Compose) |

**Headers** (click "Add new parameter" → Headers → click "+ Add new item" for each):

| Header Key | Header Value |
|------------|-------------|
| `x-api-key` | `YOUR_ANTHROPIC_API_KEY_HERE` |
| `anthropic-version` | `2023-06-01` |
| `Content-Type` | `application/json` |

**API Key Security Note:**
- For proof phase: paste the key directly (acceptable for testing)
- For production: use PA Environment Variables → `@parameters('ANTHROPIC_API_KEY')`
- NEVER commit the API key to git or share the flow definition with the key visible

---

### STEP 4: Parse JSON — Extract Claude's Text Response

The Anthropic API returns a response envelope like:
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "{\"quote_name\": \"...\", ...}"
    }
  ],
  "model": "claude-sonnet-4-5-20250929",
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 500, "output_tokens": 200}
}
```

We need to extract `content[0].text` which contains Claude's raw JSON string.

1. Search for **"Parse JSON"** → select **Data Operations - Parse JSON**
2. Rename this action to **Parse_Claude_Response**
3. Configure:

| Field | Value |
|-------|-------|
| Content | `body('HTTP')` (dynamic content from Step 3) |
| Schema | *(paste below)* |

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "id": { "type": "string" },
    "type": { "type": "string" },
    "role": { "type": "string" },
    "content": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": { "type": "string" },
          "text": { "type": "string" }
        }
      }
    },
    "model": { "type": "string" },
    "stop_reason": { "type": "string" },
    "usage": {
      "type": "object",
      "properties": {
        "input_tokens": { "type": "integer" },
        "output_tokens": { "type": "integer" }
      }
    }
  }
}
```

---

### STEP 5: Parse JSON — Extract Bid Fields

1. Add another **Parse JSON** action
2. Rename to **Parse_Extraction**
3. Configure:

| Field | Value |
|-------|-------|
| Content | Expression: `body('Parse_Claude_Response')?['content'][0]?['text']` |
| Schema | *(paste below)* |

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "quote_name": { "type": ["string", "null"] },
    "customer": { "type": ["string", "null"] },
    "location": { "type": ["string", "null"] },
    "sign_type": {
      "type": ["string", "null"],
      "enum": ["EMC_MONUMENT", "EMC_POLE", "EMC_RETROFIT", "EMC", "CHANNEL_LETTERS", "CHANNEL_LOGO", "MONUMENT_BASE", "MONUMENT_MANUAL_READER", "CABINET_ILLUMINATED", "INFO_PANEL", "MASONRY_SUB", "REMOVAL", "STRUCTURAL_BASE", null]
    },
    "estimated_value": { "type": ["number", "null"] },
    "description": { "type": ["string", "null"] },
    "sq_ft": { "type": ["number", "null"] },
    "faces": { "type": ["number", "null"] },
    "cabinet_dims": { "type": ["string", "null"] },
    "pixel_pitch": { "type": ["number", "null"] },
    "delivery_date": { "type": ["string", "null"] },
    "is_redo": { "type": "boolean" },
    "has_drawings": { "type": "boolean" },
    "has_specs": { "type": "boolean" },
    "blocking": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["watchfire_pricing", "needs_drawings", "needs_specs", "masonry_sub_quote"]
      }
    }
  },
  "required": ["quote_name", "customer", "sign_type", "estimated_value", "description", "is_redo", "blocking"]
}
```

---

### STEP 6: Create a Page (Notion)

1. Search for **"Notion"** → select **Notion (Independent Publisher)**
2. Select action: **Create a Page**
3. If prompted, create a connection using:
   - Integration Token: *(from `.env` file — `NOTION_TOKEN`)*
4. Configure:

| Field | Value / Expression |
|-------|-------------------|
| Database ID | `304c1e58d2dd814aae63c6a0d44e6679` |

**Property Mappings:**

For each property below, you'll need to build the Notion API request body. The Notion "Create a Page" action in the IP connector may have a simplified interface, or it may require raw JSON. If it uses the raw JSON body format, paste this as the **Properties** field:

```
{
  "Quote #": {
    "title": [{ "text": { "content": "@{body('Parse_Extraction')?['quote_name']}" } }]
  },
  "Customer": {
    "rich_text": [{ "text": { "content": "@{body('Parse_Extraction')?['customer']}" } }]
  },
  "Location": {
    "rich_text": [{ "text": { "content": "@{if(empty(body('Parse_Extraction')?['location']), '', body('Parse_Extraction')?['location'])}" } }]
  },
  "Description": {
    "rich_text": [{ "text": { "content": "@{body('Parse_Extraction')?['description']}" } }]
  },
  "Cabinet Dims": {
    "rich_text": [{ "text": { "content": "@{if(empty(body('Parse_Extraction')?['cabinet_dims']), '', body('Parse_Extraction')?['cabinet_dims'])}" } }]
  },
  "Salesman": {
    "select": { "name": "Jeff Fye" }
  },
  "Sign Type": {
    "select": { "name": "@{body('Parse_Extraction')?['sign_type']}" }
  },
  "Pipeline Stage": {
    "select": { "name": "INTAKE" }
  },
  "Status": {
    "select": { "name": "@{if(body('Parse_Extraction')?['is_redo'], 'REDO BID REQUEST', 'BID REQUEST')}" }
  },
  "Blocking Owner": {
    "select": { "name": "brady" }
  },
  "Blocking": {
    "multi_select": "@{body('Parse_Extraction')?['blocking']}"
  },
  "Est. Value": {
    "number": "@{body('Parse_Extraction')?['estimated_value']}"
  },
  "Sq Ft": {
    "number": "@{body('Parse_Extraction')?['sq_ft']}"
  },
  "Faces": {
    "number": "@{body('Parse_Extraction')?['faces']}"
  },
  "Pixel Pitch (mm)": {
    "number": "@{body('Parse_Extraction')?['pixel_pitch']}"
  },
  "Email Received": {
    "date": { "start": "@{triggerOutputs()?['body/receivedDateTime']}" }
  },
  "Delivery Date": {
    "date": { "start": "@{body('Parse_Extraction')?['delivery_date']}" }
  },
  "Is Redo": {
    "checkbox": "@{body('Parse_Extraction')?['is_redo']}"
  },
  "Value Source": {
    "select": { "name": "@{if(not(empty(body('Parse_Extraction')?['estimated_value'])), 'estimated', '')}" }
  }
}
```

**IMPORTANT — Null handling:**
- If the Notion connector rejects null values for select/date fields, wrap each nullable field in a condition:
  - `if(empty(body('Parse_Extraction')?['sign_type']), '', body('Parse_Extraction')?['sign_type'])`
- For `Delivery Date`: only include the property if `delivery_date` is not null — you may need a **Condition** step before the Notion action
- For `Blocking` multi_select: the value must be an array of `{"name": "..."}` objects. Use an **Apply to each** or a **Select** action to transform `["watchfire_pricing"]` into `[{"name": "watchfire_pricing"}]`

**Multi-select transformation (if needed):**
Add a **Select** action before Step 6:
- From: `body('Parse_Extraction')?['blocking']`
- Map: `{"name": "@{item()}"}`
- Reference result in Notion as: `body('Select')`

---

### STEP 7: Error Handling (Recommended)

Add error handling to catch failures at any step:

1. Click the **...** menu on Steps 3, 4, 5, and 6
2. Select **Configure run after**
3. Check **has failed** and **has timed out**
4. For each failure path, add a **Send an email (V2)** action:

| Field | Value |
|-------|-------|
| To | `brady@eaglesign.net` |
| Subject | `BID-INTAKE-PROOF FAILED: @{triggerOutputs()?['body/subject']}` |
| Body | `Flow failed at step: [step name]. Error: @{result('[step name]')?['error']?['message']}. Original email subject: @{triggerOutputs()?['body/subject']}` |

---

### STEP 8: Mark Email as Read (Optional)

1. Search for **"Mark as read"** → select **Office 365 Outlook - Mark as read or unread (V3)**
2. Configure:

| Field | Value |
|-------|-------|
| Message Id | `triggerOutputs()?['body/id']` |
| Mark as | Read |

---

## Testing Checklist

After building the flow:

- [ ] Save the flow (it should auto-enable)
- [ ] Send Test Email 1 (EMC Monument) to `Inbox/BID REQUEST/Jeff Fye`
- [ ] Wait 1-5 minutes for trigger
- [ ] Check PA flow run history — did it succeed?
- [ ] Check Notion Bid Pipeline DB — did the row appear?
- [ ] Verify extracted fields match expected values (see `test/test-emails.md`)
- [ ] Send Test Email 2 (Channel Letters) — repeat checks
- [ ] Send Test Email 3 (Removal) — repeat checks
- [ ] Run `python test/validate-notion-rows.py` to auto-validate
- [ ] If all 3 pass: Phase 1 is PROVEN. Proceed to Phase 2.
- [ ] If any fail: check PA run history for the error step, fix, re-test

## Cost per Run

| Component | Cost |
|-----------|------|
| PA flow run | $0 (included in M365 license) |
| HTTP connector call | $0 (Premium, included) |
| Anthropic API (Sonnet, ~500 input + ~200 output tokens) | ~$0.003 |
| Notion API call | $0 |
| **Total per email** | **~$0.003** |
| **Monthly estimate (20 emails/day)** | **~$1.80** |

## Troubleshooting

### HTTP step returns 401
- API key is wrong or expired. Generate a new one at console.anthropic.com.

### HTTP step returns 400
- Malformed JSON in the Compose step. Test the JSON string in a JSON validator.
- Common issue: unescaped quotes or newlines in the email body broke the JSON.

### HTTP step returns 429
- Rate limited. Add a **Delay** action (10 seconds) before retry. Unlikely at Eagle's volume.

### Parse JSON fails
- Claude returned non-JSON output (markdown, error message, etc.)
- **KNOWN ISSUE:** Sonnet sometimes wraps JSON in `` ```json ``` `` code fences despite the prompt saying not to. Add a **Compose** step between Steps 4 and 5 to strip fences:
  - Expression: `replace(replace(body('Parse_Claude_Response')?['content'][0]?['text'], '```json', ''), '```', '')`
  - Then use this cleaned output as input to Step 5 instead
- Add a **Condition** step before Parse JSON: check if `body('HTTP')?['stop_reason']` equals `end_turn`

### Notion returns 400
- Property name mismatch. Notion property names are case-sensitive.
- Check that `Quote #` has the `#` symbol, `Est. Value` has the period, etc.
- Null values in select fields may cause errors. Wrap in condition checks.

### Notion returns 401
- Integration token expired or doesn't have access to the database.
- In Notion: open the Bid Pipeline DB → **...** → **Connections** → verify integration is connected.

### Flow doesn't trigger
- Email not in the correct folder (`Inbox/BID REQUEST/Jeff Fye`).
- Flow is turned off. Check flow status in PA.
- Trigger condition issue. Remove any filters and test with a blank trigger.
