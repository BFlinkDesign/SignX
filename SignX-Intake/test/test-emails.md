# Test Emails for BID-INTAKE-PROOF Flow

Send each email to yourself at brady@eaglesign.net, then manually move it to `Inbox/BID REQUEST/Jeff Fye` (or set up an Outlook rule to route it).

Wait for the PA flow to trigger (~1-5 minutes), then run `validate-notion-rows.py` to verify the Notion rows.

---

## Test Email 1: EMC Monument (complex, high-value)

**To:** brady@eaglesign.net
**Subject:** First National Bank - New EMC Monument Sign

```
Jeff,

First National Bank in Ankeny wants to replace their existing monument sign with a new illuminated monument with EMC. Cabinet is 6' x 10' double-face. They want a 10mm Watchfire display, roughly 3' x 6' on one face. Monument base is existing brick, needs new internal structure.

Budget target is $85,000. Need quote by March 1st. Drawings attached (pretend).

Thanks,
Mark Johnson
First National Bank Facilities
```

**Expected extraction:**
| Field | Expected Value |
|-------|---------------|
| quote_name | First National Bank EMC Monument |
| customer | First National Bank |
| location | Ankeny, IA |
| sign_type | EMC_MONUMENT |
| estimated_value | 85000 |
| cabinet_dims | 6' x 10' |
| pixel_pitch | 10 |
| faces | 2 |
| sq_ft | 60 |
| delivery_date | 2026-03-01 |
| is_redo | false |
| has_drawings | true |
| blocking | ["watchfire_pricing"] |

---

## Test Email 2: Channel Letters (straightforward)

**To:** brady@eaglesign.net
**Subject:** Pancheros Ames - Channel Letter Set

```
Jeff - new Pancheros location in Ames needs front-lit channel letters.
24" tall, "PANCHEROS MEXICAN GRILL" - red returns, white faces.
Standard raceway mount on stucco wall.
Need by March 15.

-Dave, Pancheros Facilities
```

**Expected extraction:**
| Field | Expected Value |
|-------|---------------|
| quote_name | Pancheros Ames Channel Letters |
| customer | Pancheros |
| location | Ames, IA |
| sign_type | CHANNEL_LETTERS |
| estimated_value | null |
| cabinet_dims | null |
| pixel_pitch | null |
| faces | null |
| sq_ft | null |
| delivery_date | 2026-03-15 |
| is_redo | false |
| has_drawings | false |
| blocking | [] |

---

## Test Email 3: Removal (edge case)

**To:** brady@eaglesign.net
**Subject:** RE: Old Kum & Go removal - 4th & Grand

```
Jeff, the old Kum & Go at 4th & Grand in DSM needs the pole sign removed completely.
Pole is maybe 20' with a double-face cabinet on top, roughly 4x8.
They want pole cut flush, base capped.
This is a redo of the quote we did last fall.

-Chris
```

**Expected extraction:**
| Field | Expected Value |
|-------|---------------|
| quote_name | Kum & Go Removal 4th & Grand |
| customer | Kum & Go |
| location | Des Moines, IA |
| sign_type | REMOVAL |
| estimated_value | null |
| cabinet_dims | 4' x 8' |
| pixel_pitch | null |
| faces | 2 |
| sq_ft | 32 |
| delivery_date | null |
| is_redo | true |
| has_drawings | false |
| blocking | [] |

---

## After Sending

1. Move each email to `Inbox/BID REQUEST/Jeff Fye`
2. Wait 5 minutes for PA flow to trigger
3. Check PA flow run history for success/failure
4. Run: `python test/validate-notion-rows.py`
5. Review results — all 3 should pass field validation
6. Delete test rows from Notion after validation
