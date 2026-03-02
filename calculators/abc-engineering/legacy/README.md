# Legacy - ABC Engineering Desktop Module Extraction

This directory contains the complete reverse-engineered artifacts from the ABC Engineering desktop estimating software (AbcEng.exe), an MFC/C++ Windows application by ABC Sign Products, Inc.

## Source
Extracted from `C:\Tools\ABC_Engineering_Clone\` using a 9-step PowerShell pipeline (Step1_ExportRegistry through Step9_CreateZip).

## Directory Structure

### `chm_help/`
Decompiled CHM (Compiled HTML Help) files from the engineering help system. Contains:
- **engPBF.htm** - Section Modulus / Perimeter Bending Force dialog documentation
- **engBolt.htm** - Anchor Bolt dialog documentation
- **engFoundCirc.htm** - Circular foundation dialog
- **engFoundSq.htm** - Square foundation dialog
- **engFoundRect.htm** - Rectangular foundation dialog
- **engFoundSpread.htm** - Spread foundation dialog
- **engSoilPress.htm** - UBC Table 18-I-A soil pressure values
- **engSoilDlg.htm** - Soil pressure dialog documentation
- **engGlossary.htm** - Engineering term definitions
- **engAvg.htm** - Average centroid height calculator
- **engSectMod.htm** - Section modulus reference
- **engAbout.htm** - About/version info
- **Base Plate and Anchor Bolt Design.htm** - KEY DOCUMENT: Complete anchor bolt/baseplate design methodology, 1997 UBC code basis, washer table, caisson bolt details. Authored by R C Hansen Consulting, P.E.
- **Gusset table.htm** - Complete gusset dimension table for 21 pipe sizes (Excel export by Tomas Davidonis)
- **Pipe Weight Chart.htm** - Complete pipe/tube weight data: Sch40 + Sch80 pipe (2"-60"), thin + heavy wall square tube (2"-16")
- **Spread Footing Foundations with Rebar Cage.htm** - Rebar cage construction details
- **Image2.jpg** - Section Modulus / PBF dialog screenshot
- **Image4.jpg** - Anchor Bolt dialog screenshot
- **Image5.jpg** - Spread Foundation dialog screenshot
- **Image6.jpg** - Circ/Sq/Rect Foundation dialog screenshot
- **Baseplate.jpg** - Typical baseplate drawing (bolt holes at 1.25x bolt dia)
- **Gusset.jpg** - Plan view of column baseplate connection with gusset locations

### `vbscripts/`
VBScript modules extracted from `scripts_nm.abc` binary (255,801 bytes). Contains 29 module name references, 3 fully extracted:
- **_GLOBAL_DECLARATIONS.vbs** - Partially decoded global variables (sign dimensions, material arrays, customer info)
- **_MODULE_INDEX.txt** - Complete list of all 29 VBS module names
- **_MANIFEST.json** - Extraction metadata
- **_ALL_EXTRACTED_TEXT.txt** - All extractable text from the binary
- **_DECODED_FULL.txt** - Full decoded output
- **_DECODED_VBSCRIPT_FULL.txt** - VBScript-specific decoded output
- **DeInit.vbs, Init.vbs, InitData.vbs** - Initialization/cleanup procedures
- **IncCurRow.vbs, InsertRow.vbs** - Row manipulation
- **SetGlobal.vbs, SetMacroValue.vbs, SetSpecValue.vbs** - Value setters
- **WriteLabor.vbs, WriteMaterial.vbs** - Data writers
- **WriteSalesAgreementOnly.vbs, WriteSalesAgreementTerms.vbs** - Sales agreement output
- **WriteSalesAgreementWithOptionalMaintenance.vbs** - Maintenance agreement variant
- **WriteMaintenanceAgreementOnly.vbs** - Maintenance agreement output

Key engineering modules (referenced but embedded in binary, not fully extractable):
- BoltBase.vbs, CSRFound.vbs, SprFound.vbs

### `parsed_data/`
JSON files parsed from .abc binary data files. Each contains extracted strings, formulas, sections, and float values:
- **bill_mat_nm_abc.json** (129KB) - Bill of materials data (1,490 formulas, 2,405 unique strings)
- **labor_nm_abc.json** (264KB) - Labor data (1,617 formulas, 2,917 unique strings)
- **scripts_nm_abc.json** (256KB) - Script/macro data (5,090 formulas, 4,987 unique strings)
- **menu_nm_abc.json** (173KB) - Menu structure (1,125 formulas, 3,235 unique strings)
- **mconv_dat.json** (131KB) - Conversion data (774 formulas, 2,797 unique strings)
- **invent_nm_abc.json** (67KB) - Inventory data
- **descript_nm_abc.json** (31KB) - Description data
- **dept_nm_abc.json, macros_nm_abc.json, sales_nm_abc.json, stat_nm_abc.json, user_nm_abc.json, wocfg_nm_abc.json** - Supporting data
- **_PARSE_SUMMARY.json** - Parse statistics for all files

### `database/`
Access MDB database (abcsignc.mdb) exported to CSV with schema files:
- **Customers.csv / Customers_schema.txt**
- **CustomerCards.csv / CustomerCards_schema.txt**
- **Addresses.csv / Addresses_schema.txt**
- **Materials.csv / Materials_schema.txt**
- **Paperclip.csv / Paperclip_schema.txt**
- **_TABLE_LIST.txt** - List of all database tables
- **_FULL_SCHEMA.csv** - Complete schema export

### `registry/`
Windows registry exports for the application:
- **HKCU_ABC_Signs.reg** - User preferences
- **HKCU_abc_fileext.reg** - File extension associations
- **HKLM_ABC_Sign.reg** - Machine configuration
- **HKLM_ABCSignEstimate.reg** - Estimate file associations
- **HKLM_Uninstall.reg** - Uninstall registry entries

### `templates/`
Excel templates and engineering spreadsheets:
- **BoltBase.xls** - Anchor bolt/base plate calculation spreadsheet
- **CSRFound.xls** - Circular/Square/Rectangular foundation spreadsheet
- **SprFound.xls** - Spread footing foundation spreadsheet
- **Gusset.xls** - Gusset dimension table spreadsheet
- **EstReport.xlt, ProposalReport.xlt** - Report templates
- **Shop_Order.xlt, Job_Order.xlt, Manuf_Order.xlt** - Order templates
- **WorkInProgress.xlt, WorkCompleted.xlt** - Work tracking
- **ProdSchedule.xlt, Orders.xlt** - Scheduling/orders
- **salary.xlt, sales_perform.xlt, stat_analysis.xlt** - Business analytics
- **logo.bmp** - Company logo

### `FILE_MANIFEST.csv`
Complete file listing from the original ABC Engineering Clone directory.

## What's NOT Included
The following files from the original clone are NOT in this repo (too large/binary):
- DLLs (MFC42.DLL, Crystal Reports p2*/u2* series, crpe32.dll, etc.)
- EXEs (AbcEng.exe, Estimate.exe, EstConv.exe, UserManager.exe)
- Raw .abc binary data files (originals of parsed JSON)
- Access MDB database file (abcsignc.mdb - exported to CSV instead)
- .est estimate files (Motel1.est, REST1.est, Union1-7.est)
- Crystal Report files (.rpt)

These can be found in the original clone at `C:\Tools\ABC_Engineering_Clone\` on Brady's machine.

## Key People
- **Sandy Brooks** - ABC Sign Products author
- **Tomas Davidonis** (tomdav) - Developer at "No Magic" / "UAB BPI", created gusset table and pipe weight chart
- **Bob Hansen, P.E.** - R C Hansen Consulting, Fort Collins CO - Engineering consultant, authored anchor bolt design methodology
