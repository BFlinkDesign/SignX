# G: Drive Discovery Report

**Date:** 2026-02-15
**Drive:** G:\ = \\ES-FS02\customers2
**Purpose:** Map folder structure to KeyedIn WO/Quote numbers for instant file lookup

---

## 1. Folder Structure Overview

### Top-Level Layout
- **50 top-level folders**: A-Z letter folders + numbered folders (0-9) + special folders
- **6,861 total customer folders** across all letters
- Special folders: `DIGITAL PRINTS`, `DNC_BACKUP`, `EMC-SO`, `Section Detail Templates`, `_Temp_Delete_After_Use`

### Customer Count by Letter (top 10)
| Letter | Count | Letter | Count |
|--------|-------|--------|-------|
| C | 684 | S | 618 |
| A | 493 | B | 445 |
| M | 443 | P | 363 |
| T | 343 | D | 315 |
| W | 307 | F | 289 |

### Folder Hierarchy
```
G:\
  [Letter]/
    [Customer Name]/
      [Location or Project or Year]/
        [Files: CDR, PDF, AI, DXF, JPG, etc.]
```

---

## 2. Folder Naming Convention

### Pattern Analysis (56 subfolders sampled across 9 letters)
| Pattern | Count | Percentage |
|---------|-------|-----------|
| Plain name (location/project) | 48 | 85.7% |
| Contains year (20xx) | 8 | 14.3% |
| Contains 5-digit number | 0 | 0.0% |

### Key Finding: NO WO/quote numbers appear in folder names

Folders are organized by:
- **Customer name** (top level under letter): `CAT Scale`, `Pancheros`, `Mercy One (Rebrand)`
- **Location** (sub-level): `Osceola`, `Ankeny`, `Des Moines, IA - N.E. 14th`
- **Year** (sub-level): `2024`, `2025`, `2026`
- **Project type** (sub-level): `Survey Pictures`, `Completion Photos`, `ROUTER`, `Customer Artwork`
- **Multi-location brands use nested folders**: `Pancheros/Pancheros LOCATIONS/Altoona 2013`

### Examples
```
G:\C\CAT Scale\
  - Audit -/
  - Burn Parts -/
  - CAD FILES -/
  3x5 Sign/
  4x6 Sign/
  Des Moines, IA - N.E. 14th/

G:\P\Pancheros\
  2025/
  CHANNEL LETTERS/
  Marketing/
  Pancheros LOCATIONS/
    Altoona 2013/
    Ames, IA 2012/
    Ankeny IA 2012/

G:\H\H & R Block\
  7007 DOUGLAS AVE/
  GRIMES, IA/
  Osceola/
  Lamoni, IA/
```

---

## 3. How WO/Quote Numbers Appear

### In filenames (NOT folder names)

Eagle Sign uses an internal job numbering system in filenames:

**Format:** `[Description] MMYY-NNNNN-RR.ext`

| Component | Meaning | Example |
|-----------|---------|---------|
| MMYY | Month/Year created | `0126` = January 2026 |
| NNNNN | ESC internal job/quote number | `40654` |
| RR | Revision number | `00` = original, `01` = rev 1 |

### Real Examples
| Filename | Date | ESC# | Rev |
|----------|------|------|-----|
| `Pancheros Waukee West Elev 33'' Set 0126-40654-00.pdf` | Jan 2026 | 40654 | 00 |
| `Pancheros Waukee S Elev Logo 0126-40655-00.pdf` | Jan 2026 | 40655 | 00 |
| `Pancheros Waukee East Elev 29'' Set 0126-40660-00.pdf` | Jan 2026 | 40660 | 00 |
| `St Anthony Mon 6x10 10mm EMC 1025-40239-00.pdf` | Oct 2025 | 40239 | 00 |
| `Mercy One Euclid Monument 0319-27135-00.pdf` | Mar 2019 | 27135 | 00 |
| `H & R Block0114-15454-00.ai` | Jan 2014 | 15454 | 00 |
| `Ankeny SummerFest 18x24 0711-9445-00.pdf` | Jul 2011 | 9445 | 00 |
| `Bankers Trust 1st Flr 1110-8398-00.pdf` | Nov 2010 | 8398 | 00 |

### ESC numbers are sequential and time-correlated
- ~8000s: 2010-2011 era
- ~15000s: 2014 era
- ~21000s: 2016 era
- ~27000s: 2019 era
- ~37000s: 2024 era
- ~40000s: 2025-2026 era

### Proposal/Quote Files (alternate format)
| Format | Example |
|--------|---------|
| `ESC Proposal NNNNN.pdf` | `ESC Proposal 15958.pdf`, `ESC Proposal 16480.pdf` |
| `Proposal #NNNNN.pdf` | `Panchero's Waukee Proposal #30416.pdf` |
| `JFye_Proposal_*.pdf` | `JFye_Proposal_SignPackage.pdf` (no number) |
| `QNNNNNN-N.PDF` | `Q114401-1.PDF` (separate quote numbering) |
| `MIKEE_EST.QUOTE.PRINT_Single_*` | Automated quote prints from KeyedIn |

---

## 4. Relationship Between Numbering Systems

### Three distinct numbering systems identified:

| System | Format | Range | Location |
|--------|--------|-------|----------|
| **SignX-Warehouse WO** | `NNNNN.N` | 1000.1 - 62206.1 | `so_contracts_parsed.csv` |
| **SignX-Warehouse Quote** | 4-5 digit or `TOTAL` | 1000 - 11191 | `so_contracts_parsed.csv` |
| **ESC Job Number** | `MMYY-NNNNN-RR` | 8000 - 40660+ | G: drive filenames |

### These systems do NOT directly map to each other
- SignX-Warehouse WO `62200.2` for CAT Scale ≠ ESC job `30115` in filenames
- Pancheros has WO `2214.1` with Quote `5209` in warehouse, but ESC `40654` in filenames
- The ESC numbers (in filenames) appear to come from KeyedIn's quoting/estimating module
- The warehouse WO numbers come from the production/billing module

### Cross-reference path: Customer Name
The only reliable link between systems is the **customer name**. To find files for a warehouse WO:
1. Look up customer name from WO
2. Find the customer folder on G: drive
3. Browse subfolders for the relevant location/project

---

## 5. Known Job Locations

| Customer | G: Drive Path | Subfolders |
|----------|--------------|------------|
| **Mercy (all)** | `G:\M\Mercy Clinic Locations\` | Carlisle, Grimes, Pleasant Hill, WDM, Ottumwa |
| | `G:\M\Mercy One (Rebrand)\` | E Euclid DSM, Grand Ave WDM, Norwalk |
| | `G:\M\Mercy One - REBRAND (AGI)\` | 30+ numbered locations via FARRAH/MACKENZIE |
| **St. Anthony** | `G:\S\St. Anthony Hospital\` | 1524 E US Hwy 30, 311 S. Clark St |
| | `G:\S\St. Anthony Catholic Church\` | Quotes |
| | `G:\S\St. Anthony Child Care Center\` | GEMINI, Survey Photos |
| **Ankeny** | `G:\A\Ankeny *` (36+ folders) | Each business/org is its own folder |
| **DSM Parks** | `G:\D\DSM PARKS-RICH\` | |
| | `G:\D\Des Moines Partnership Jobs\Des Moines Parks and Rec\` | |
| **CAT Scale** | `G:\C\CAT Scale\` | Audit, CAD FILES, Burn Parts, 3x5/4x5/4x6 Sign types |
| **Pancheros** | `G:\P\Pancheros\` | 2025, CHANNEL LETTERS, Pancheros LOCATIONS (10+ cities) |

---

## 6. Customer Name Matching (Warehouse -> G: Drive)

### Match Rate: **85.6%** (2,775 of 3,241 unique customers)

| Match Type | Count | Notes |
|-----------|-------|-------|
| Exact match | 1,208 (37.3%) | Customer name identical |
| First-word match | 1,488 (45.9%) | First word of name matches folder |
| Contains match | 79 (2.4%) | Substring matching |
| Unmatched | 466 (14.4%) | Mostly numeric-prefix names (1ST, 2/90, etc.) |

### Why 14.4% don't match
- **Numeric-prefix customers** (1st Choice, 2/90 Sign Systems, 3 Son's Car Wash) stored in `G:\1\`, `G:\2\`, `G:\3\` etc. — script only checked A-Z
- **Abbreviations/name changes** (e.g., warehouse "AAFES ACCOUNTS PAYABLE" vs. folder "Acco")
- **Defunct/one-time customers** who never got a G: drive folder

### First-word matching caveats
Some first-word matches are false positives:
- `A-1 MECHANICAL SERVICES` matched to `A-1 Staffing` (wrong business)
- `ACCENT GRAPHICS` matched to `Action Accents` (wrong)

**Recommended:** Use first 2 words minimum, or full fuzzy matching with Levenshtein distance.

---

## 7. File Type Inventory

### CAT Scale (8,798 files) — representative large customer
| Extension | Count | Type |
|-----------|-------|------|
| .rtf | 2,864 | Rich text (correspondence, quotes) |
| .jpg | 2,091 | Photos (survey, completion, products) |
| .pdf | 1,392 | Proposals, art approvals, permits |
| .doc | 400 | Word documents |
| .cdr | 398 | CorelDRAW design files |
| .xls | 325 | Spreadsheets |
| .fs | 191 | FlexiSign files |
| .eps | 150 | Encapsulated PostScript |
| .dwg | 146 | AutoCAD drawings |
| .dxf | 89 | DXF exchange format |

### Pancheros (1,240 files) — representative medium customer
| Extension | Count | Type |
|-----------|-------|------|
| .jpg | 550 | Photos |
| .pdf | 297 | Proposals, art |
| .ai | 79 | Adobe Illustrator |
| .rou | 73 | Router cut files |
| .cdr | 53 | CorelDRAW |
| .dxf | 44 | DXF |
| .fs | 22 | FlexiSign |
| .eps | 17 | EPS |

### Common file types across all customers
| Category | Extensions | Purpose |
|----------|-----------|---------|
| **Design** | .cdr, .ai, .eps, .fs | Source artwork |
| **Production** | .dxf, .dwg, .rou, .enr | CNC/router/fabrication |
| **Documents** | .pdf, .doc, .docx, .rtf, .xls, .xlsx | Proposals, contracts, specs |
| **Photos** | .jpg, .jpeg, .png | Survey, completion, product |
| **Signage** | .scv, .pcd | SignCAD, proprietary |

---

## 8. Recommended Mapping Strategy

### Strategy: **Hybrid (Customer Name Lookup + Filename Number Index)**

#### Phase 1: Customer Name Lookup Table (immediate)
Already generated: `g_drive_customer_map.csv` (6,861 rows)
- Use for navigation: Warehouse customer name -> G: drive path
- Improve matching: add numeric-prefix folders, implement fuzzy matching
- Match rate with improvements: estimated **90-95%**

#### Phase 2: ESC Number Index (build a filename scanner)
```python
# Scan all files on G: drive for MMYY-NNNNN pattern
# Build index: ESC_number -> [list of file paths]
# Enables: "Find all files for ESC job 40654"
import re
pattern = re.compile(r'(\d{4})-(\d{4,5})(?:-(\d{2}))?')
```

Estimated scan time: 30-60 minutes for full G: drive (8,000+ customers)
Output: `g_drive_esc_number_index.csv` with columns: `esc_number, date_code, customer, filepath`

#### Phase 3: Cross-Reference Table (requires KeyedIn data)
To link Warehouse WO numbers to G: drive files:
1. Need a KeyedIn export that maps WO numbers to ESC job numbers
2. OR build the bridge via customer name + date range matching
3. Warehouse WO `2214.1` (Pancheros) from 2007 era -> G: files from that era in Pancheros folder

#### Regex for filename extraction
```regex
# Match the MMYY-NNNNN-RR pattern in filenames
(\d{2})(\d{2})-(\d{4,5})(?:-(\d{2}))?
# Groups: Month, Year, ESC Number, Revision
```

---

## 9. Key Insights & Caveats

1. **G: drive is the art/production archive, not a WO database.** It's organized for designers to find customer files by name, not for accounting to find files by WO number.

2. **The ESC job number is the Rosetta Stone.** It appears in filenames and likely exists in KeyedIn's quoting module. If we can export ESC numbers from KeyedIn, we can build a complete cross-reference.

3. **Some customers have 20+ years of history** (CAT Scale has 8,798 files spanning 2010-2026+).

4. **Folder naming is inconsistent at the customer level.** Some use year subfolders, some use location subfolders, some dump everything in one folder. No standard enforced.

5. **Mercy is the most complex customer.** At least 8 top-level Mercy folders, 30+ sub-locations, spanning multiple rebranding campaigns (Mercy -> MercyOne, managed by AGI).

6. **The `- Audit -` folders under CAT Scale contain 2026 quote automation** (Python scripts, quote masters in XLSX format using `Quote_NNN-NNNN` format).

---

## Files Generated

| File | Description |
|------|-------------|
| `C:\Scripts\g_drive_customer_map.csv` | 6,861 rows: Letter, Customer, SubfolderCount, SampleSubfolders, Path |
| `C:\Scripts\signx-warehouse\g_drive_matched_customers.csv` | 2,775 rows: warehouse customers matched to G: folders |
| `C:\Scripts\signx-warehouse\g_drive_unmatched_customers.csv` | 466 rows: warehouse customers NOT found on G: drive |
| `C:\Scripts\signx-warehouse\g_drive_discovery.md` | This report |
