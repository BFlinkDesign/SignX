# Legacy - Engineering Desktop Module Extraction

This directory contains the complete reverse-engineered artifacts from a legacy sign engineering desktop application (an MFC/C++ Windows application).

## What This Is

A legacy sign estimating and engineering system that was used as reference material when building the modern web-based `sign-engineering-calculator.html`. The files here represent the data structures, calculation templates, and configuration from the original software.

## Directory Structure

```
legacy/
├── FILE_MANIFEST.csv       # Complete file listing from original installation
├── README.md               # This file
├── chm_help/               # Extracted help documentation (40+ HTML files)
├── database/               # Database exports (CSV format)
│   ├── Addresses.csv
│   ├── Customers.csv
│   ├── CustomerCards.csv
│   ├── Materials.csv
│   └── Paperclip.csv
├── parsed_data/            # Parsed application data (JSON)
│   ├── bill_mat.json       # Bill of materials structure
│   ├── dept.json           # Department codes
│   ├── description.json    # Item descriptions
│   ├── inventory.json      # Inventory items
│   ├── labor.json          # Labor codes and rates
│   ├── macros.json         # VBScript macro definitions
│   ├── menus.json          # Application menu structure
│   ├── sales.json          # Sales data structure
│   ├── scripts.json        # Embedded script definitions
│   ├── stats.json          # Statistics configuration
│   ├── user.json           # User configuration
│   └── workflow.json       # Workflow definitions
├── registry/               # Windows registry exports
├── templates/              # Excel calculation templates
│   ├── BoltBase.xls        # Bolt base plate calculations
│   ├── CSRFound.xls        # Caisson/spread foundation calculations
│   ├── Gusset.xls          # Gusset plate calculations
│   ├── SprFound.xls        # Spread footing calculations
│   └── *.xlt               # Report and job order templates (13 files)
└── vbscripts/              # VBScript source files (21 scripts)
```

## Engineering Excel Templates

The 4 XLS files in `templates/` are engineering calculation spreadsheets from the legacy software:

| File | Covers |
|------|--------|
| `BoltBase.xls` | Anchor bolt and base plate sizing |
| `CSRFound.xls` | Caisson/round foundation design |
| `Gusset.xls` | Gusset plate design |
| `SprFound.xls` | Spread footing / pad foundation |

**Note**: The legacy software did NOT have separate Excel sheets for Wind Load or Section Modulus — those calculations were handled internally by the application engine. The web-based calculator covers all these functions in JavaScript.

## Key Reference Mappings

The legacy desktop module's Excel templates map to the modern calculator's tabs:

| Legacy Template | Modern Calculator Tab |
|----------------|-----------------------|
| BoltBase.xls | Anchor Bolt tab |
| CSRFound.xls | Foundation tab (circular/caisson) |
| Gusset.xls | Gusset Table tab |
| SprFound.xls | Foundation tab (spread/square) |
| (built-in engine) | Wind Load (sidebar inputs) |
| (built-in engine) | Section Modulus tab |
