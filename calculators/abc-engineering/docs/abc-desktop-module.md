# Legacy Engineering Desktop Module - Complete Reference

## Overview
- **Application**: Legacy Sign Engineering (AbcEng.exe) - desktop sign estimating software
- **Developer**: Legacy vendor (Windows MFC/C++ application)
- **Technology**: MFC/C++ Win32, Crystal Reports (crpe32.dll + p2*/u2* DLL series), Access MDB database (abcsignc.mdb)
- **Code Basis**: "1997 UBC code is used as the engineering approach"
- **Engineering Assumptions**: Concrete 3000 psi 28-day strength, normal weight; Steel A36 (36,000 psi yield); A307 bolts (20,000 psi Fb)
- **Data Format**: Custom .abc binary files containing VBScript macros, formulas, sections, and string data
- **Help System**: Compiled HTML Help (.chm) decompiled to individual HTML files

## Reverse Engineering Pipeline
9-step PowerShell extraction pipeline (Step1_ExportRegistry.ps1 through Step9_CreateZip.ps1):
1. Step1_ExportRegistry - Export Windows registry keys for ABC Sign
2. Step2 through Step5 - Extract root files, data directories, database
3. Step6 (multiple iterations: 6b, 6c, 6d, 6e, Final) - VBScript extraction/decoding from .abc binary files
4. Step7 - Parse .abc binary data files to JSON
5. Step8 - Decompile CHM help files
6. Step9 - Create distribution zip

## Application Architecture

### Binary Data Files (.abc format)
13 data files parsed to JSON, with statistics:
| File | Size | Formulas | Sections | Unique Strings |
|------|------|----------|----------|----------------|
| bill_mat_nm.abc | 129,047 | 1,490 | 1,419 | 2,405 |
| dept_nm.abc | 657 | 4 | 13 | 27 |
| descript_nm.abc | 31,284 | 605 | 337 | 1,060 |
| invent_nm.abc | 66,987 | 705 | 1,175 | 3,227 |
| labor_nm.abc | 263,742 | 1,617 | 1,978 | 2,917 |
| macros_nm.abc | 2,113 | 13 | 0 | 26 |
| menu_nm.abc | 173,367 | 1,125 | 968 | 3,235 |
| sales_nm.abc | 408 | 2 | 0 | 5 |
| scripts_nm.abc | 255,801 | 5,090 | 3 | 4,987 |
| stat_nm.abc | 2,908 | 2 | 0 | 15 |
| user_nm.abc | 98 | 0 | 0 | 3 |
| wocfg_nm.abc | 140 | 0 | 0 | 7 |
| mconv.dat | 131,081 | 774 | 859 | 2,797 |

### VBScript Modules
29 module names found in scripts_nm.abc binary (3 fully extracted):

**Engineering Modules (KEY):**
- BoltBase.vbs - Anchor bolt and base plate calculations
- CSRFound.vbs - Circular/Square/Rectangular foundation calculations
- SprFound.vbs - Spread footing foundation calculations

**Reporting Modules:**
- estglob.vbs - Global declarations (partially decoded - contains sign estimation variables)
- estreport.vbs - Estimate report generation
- ProposalReport.vbs - Proposal report generation

**Other Modules:**
- DeptInfoReport.vbs, emplPrint.vbs, InventoryReport.vbs, LaborFactReport.vbs
- OpenEstimateReport.vbs, OpenJobReport.vbs, Print_job_order.vbs
- Print_manuf_order.vbs, Print_shop_order.vbs, salesPerfReport.vbs
- StatAnReport.vbs, wk_in_progress.vbs, handle_journals.vbs
- job_shop_copy.vbs, updatejobDates.vbs, openfile.vbs
- PreviewAlloc.vbs, InvLinksReport.vbs, lbRecPrint.vbs
- matRecPrint.vbs, misAmntReport.vbs, upInvoicesReport.vbs, JournalReport.vbs

### Global Variables (from estglob.vbs, partially decoded)
Key sign estimation variables discovered:
- gBSC(99,50) - BSC data array (99 sections x 50 iterations)
- gLetterCount(99,50) - Letter count per section
- gNeonTubes(99,50) - Neon tube count per section
- gFaces(99) - Number of faces per section
- gPyBe(99) - Unknown parameter
- gAccessFrame(99) - Access frame data
- gWideFabFrame(99) - Wide fabrication frame
- gSignLength(99) - Sign length per section (note: array supports up to 99 sections)
- gSignHeight(99) - Sign height per section
- gBorderLength(99,50) - Border length per section/iteration
- gBorderSize(99,50) - Border size per section/iteration
- MAX_ITERATION = unknown (likely 50)
- MAX_SECTION = 99
- DEBUG = False
- NARROW_TYPE = 3, MEDIUM_TYPE = 4, WIDE_TYPE = 6
- OUTLINED = unknown, SHADED = 34
- Unit conversion factors: gUnitFactors(0)=3.2 (unknown), (1)=1.0, (2)=25.4 (inches to mm), (4)=3.2, (5)=2.946373 (cu yards), (6)=2.5662 (ft to meters), (7)=4302 (unknown), (13)=105.36 (gal to lit)
- Customer info: customerName, customerAddress, customerCity, customerState, customerZip, customerPhone, customerFax
- Job site: customerJSAddress, customerJSCity, customerJSState, customerJSZip
- gbPostAndPanelType - Post and panel sign type flag
- gPostAndPanelArea - Post and panel area
- gEstFlagNew - Estimate new flag (True)

### Database (Access MDB)
Tables exported to CSV:
- Addresses - Address records
- CustomerCards - Customer card data
- Customers - Customer records
- Materials - Materials database
- Paperclip - Paperclip/attachment records

### Registry Keys
- HKCU\Software\ABC Signs - User preferences
- HKLM\Software\ABC Sign - Machine configuration
- HKLM\Software\ABCSignEstimate - Estimate associations
- HKCU file extension associations
- HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall - Uninstall info

### Excel Templates
Report templates used with Crystal Reports/VBScript:
- EstReport.xlt - Estimate report
- ProposalReport.xlt - Proposal report
- Shop_Order.xlt - Shop order
- Job_Order.xlt - Job order
- JobShopCopy.xlt - Job shop copy
- Manuf_Order.xlt - Manufacturing order
- Orders.xlt - Orders
- ProdSchedule.xlt - Production schedule
- WorkInProgress.xlt - Work in progress
- WorkCompleted.xlt - Work completed
- salary.xlt - Salary
- sales_perform.xlt - Sales performance
- stat_analysis.xlt - Statistical analysis

### Engineering Spreadsheets
- BoltBase.xls - Anchor bolt/base plate calculations (matches BoltBase.vbs)
- CSRFound.xls - Circular/Square/Rectangular foundation (matches CSRFound.vbs)
- SprFound.xls - Spread footing foundation (matches SprFound.vbs)
- Gusset.xls - Gusset dimension table

### Sample Estimates
- Motel1.est, REST1.est - Sample project estimates
- Union1-7.est (with A variants) - Union project series

## Engineering Module Documentation (from CHM Help)

### Section Modulus / PBF Dialog (engPBF.htm, Image2.jpg)
- **PBF** = Perimeter Bending Force: force on flexible sign face transmitted to frame as bending force (lbs/ft of frame perimeter)
- Input: Centroid Height, Sign Area, Number of Support Columns, Wind Pressure
- Calculates section modulus from moment and allowable stress
- Auto-selects pipe diameter from pipe data table

### Anchor Bolt Dialog (engBolt.htm, Image4.jpg)
- Inputs: Desired bolt diameter, Number of bolts in row parallel to sign face, Bolt spacing in wind direction (>= pipe OD), New/Used pipe selection
- Outputs: "Desired Bolt diameter" vs "Accepted Bolt diameter" (auto-sizes up if needed)
- Maximum bolt diameter: 3"
- Includes "Print Summary" button for reports
- **Washer Table**: For mechanical anchorage in spread footings. Washer bottom must have 3" concrete coverage.
- **Washer thickness formula**: t = SQRT(3 x washer_pressure x ((washer_dia/2 - nut_dia/2)^2) / (0.75 x 36ksi x 1.15))
- **CRITICAL WARNING**: "Do not use washers for caisson designs without specific engineering approval because washers could form a fracture plane perpendicular to the caisson bending direction."
- Caisson anchor bolts should be threaded rod or provided with heads and/or deformations similar to deformed reinforcing bars
- Caisson bolt info provided: embedded length to bend, inside bend radius, horizontal bend length, exposed threaded length, overall length

### Foundation Dialogs
**Circular Foundation (engFoundCirc.htm, Image6.jpg)**:
- "Caisson type" radio group selection
- Input: "Base Diameter/Width"

**Square Foundation (engFoundSq.htm)**:
- Same as circular but with square base dimensions

**Rectangular Foundation (engFoundRect.htm)**:
- Adds "Base Length" edit box beyond square inputs

**Spread Foundation (engFoundSpread.htm, Image5.jpg)**:
- Adds "Ratio of Width to Length (%)" -- default 50%, minimum 40%
- Requires estimated sign weight AND column weight inputs
- **Sign Weight Estimates** (from help docs):
  - 6 psf for plastic/aluminum face signs
  - 10 psf for plastic face/steel frame signs
  - 15 psf for sheet metal/neon signs

### Gusset Table (Gusset table.htm, Gusset.jpg)
- **Author**: Legacy developer
- **Engineering**: R C Hansen Consulting, P.E. (engineering review)
- **Created**: 2000-10-09, Last saved: 2002-03-18
- Title: "Base Plate to Column Connections with Gussets"
- Only for Schedule 40 pipe
- "Use anchor bolt program to determine bolt sizes, location and baseplate dimensions"
- "(minimums with gussets are shown below. Use larger of the two methods of sizing baseplates)"
- "When spacing anchor bolts, allow for nut clearance relative to fillet welds"

**Key Engineering Assumptions:**
1. Fillet welds are equal to column thickness
2. Gussets required to develop column section modulus at base plate, 4 places 90 degrees apart
3. Base plate thickness >= 2x column wall thickness
4. Gussets welded all around, thickness >= 2x column wall thickness minimum
5. Effective throat of fillet weld = 0.707 x fillet weld size
6. The 'toes' of the gusset shall be removed to the size of the fillet weld
7. Leg dimension is from the 90 degree angle to the ends after removing material for fillet weld
8. **Column connections WITHOUT gussets = approximately 70% of column section modulus** (when welded with fillet welds equal to column wall thickness)

**Complete Gusset Data Table (21 Schedule 40 pipe sizes):**

| Nominal | OD | Wall | Section Mod | Gusset Leg | Gusset Thk | Weld Size | Min BP Square | Min BP Thk |
|---------|------|-------|-------------|------------|------------|-----------|---------------|------------|
| 2" | 2.375 | 0.154 | 0.561 | 1.000 | 3/8 | 3/16 | 4-3/4 | 3/8 |
| 2-1/2" | 2.875 | 0.203 | 1.06 | 1.000 | 1/2 | 1/4 | 5-3/8 | 1/2 |
| 3" | 3.500 | 0.216 | 1.72 | 1.125 | 1/2 | 1/4 | 6-1/4 | 1/2 |
| 3-1/2" | 4.000 | 0.226 | 2.39 | 1.125 | 1/2 | 1/4 | 6-3/4 | 1/2 |
| 4" | 4.500 | 0.237 | 3.21 | 1.125 | 1/2 | 1/4 | 7-1/4 | 1/2 |
| 5" | 5.500 | 0.258 | 5.45 | 1.125 | 1/2 | 1/4 | 8-1/4 | 1/2 |
| 6" | 6.625 | 0.280 | 8.50 | 1.250 | 9/16 | 9/32 | 9-11/16 | 9/16 |
| 7" | 7.625 | 0.301 | 12.20 | 1.500 | 5/8 | 5/16 | 11-1/4 | 5/8 |
| 8" | 8.625 | 0.322 | 16.80 | 1.625 | 5/8 | 11/32 | 12-9/16 | 5/8 |
| 10" | 10.750 | 0.365 | 29.90 | 1.750 | 3/4 | 3/8 | 15 | 3/4 |
| 12" | 12.750 | 0.375 | 43.80 | 2.375 | 3/4 | 3/8 | 18-1/4 | 3/4 |
| 14" | 14.000 | 0.375 | 53.25 | 2.625 | 3/4 | 3/8 | 20 | 3/4 |
| 16" | 16.000 | 0.375 | 70.26 | 2.875 | 3/4 | 3/8 | 22-1/2 | 3/4 |
| 18" | 18.000 | 0.375 | 89.62 | 3.250 | 3/4 | 3/8 | 25-1/4 | 3/4 |
| 20" | 20.000 | 0.375 | 111.35 | 3.500 | 3/4 | 3/8 | 27-3/4 | 3/4 |
| 22" | 22.000 | 0.375 | 135.42 | 3.875 | 3/4 | 3/8 | 30-1/2 | 3/4 |
| 24" | 24.000 | 0.375 | 161.86 | 4.125 | 1 | 3/8 | 33 | 1 |
| 26" | 26.000 | 0.375 | 190.30 | 4.500 | 1 | 3/8 | 35-3/4 | 1 |
| 30" | 30.000 | 0.375 | 254.70 | 4.625 | 1 | 3/8 | 40 | 1 |
| 34" | 34.000 | 0.375 | 328.80 | 5.750 | 1 | 3/8 | 46-1/4 | 1 |
| 36" | 36.000 | 0.375 | 369.20 | 6.125 | 1 | 3/8 | 49 | 1 |

Min BP Square formula: OD + 2x(GussetLeg + WeldSize)

### Pipe Weight Chart (Pipe Weight Chart.htm)
- **Author**: Legacy developer
- **Created**: 2006-03-14

**Schedule 40 (Standard) Pipe -- COMPLETE DATA with weights:**

| Nom | OD | Wall | Sect Mod | Weight (lb/ft) |
|-----|------|-------|----------|----------------|
| 2 | 2.375 | 0.154 | 0.561 | 3.65 |
| 2.5 | 2.875 | 0.203 | 1.06 | 5.79 |
| 3 | 3.500 | 0.216 | 1.72 | 7.58 |
| 3.5 | 4.000 | 0.226 | 2.39 | 9.11 |
| 4 | 4.500 | 0.237 | 3.21 | 10.79 |
| 5 | 5.500 | 0.258 | 5.45 | 14.62 |
| 6 | 6.625 | 0.280 | 8.50 | 18.97 |
| 7 | 7.625 | 0.301 | 12.20 | 23.55 |
| 8 | 8.625 | 0.322 | 16.80 | 28.55 |
| 10 | 10.750 | 0.365 | 29.90 | 40.48 |
| 12 | 12.750 | 0.375 | 43.80 | 49.56 |
| 14 | 14.000 | 0.375 | 53.25 | 54.57 |
| 16 | 16.000 | 0.375 | 70.26 | 62.58 |
| 18 | 18.000 | 0.375 | 89.62 | 70.59 |
| 20 | 20.000 | 0.375 | 111.35 | 78.60 |
| 22 | 22.000 | 0.375 | 135.42 | 86.61 |
| 24 | 24.000 | 0.375 | 161.86 | 94.62 |
| 26 | 26.000 | 0.375 | 190.30 | 102.63 |
| 30 | 30.000 | 0.375 | 254.70 | 118.65 |
| 34 | 34.000 | 0.375 | 328.80 | 134.67 |
| 36 | 36.000 | 0.375 | 369.20 | 142.68 |
| 38 | 38.000 | 0.375 | 412.971 | 150.69 |
| 40 | 40.000 | 0.375 | 458.270 | 158.70 |
| 42 | 42.000 | 0.375 | 505.918 | 166.71 |
| 48 | 48.000 | 0.375 | 662.950 | 190.74 |
| 54 | 54.000 | 0.375 | 841.330 | 215.06 |
| 60 | 60.000 | 0.375 | 1040.040 | 238.80 |

**Schedule 80 (Extra Strong) Pipe:**

| Nom | OD | Wall | Sect Mod | Weight (lb/ft) |
|-----|------|-------|----------|----------------|
| 2 | 2.375 | 0.218 | 0.7309 | 5.02 |
| 2.5 | 2.875 | 0.276 | 1.339 | 7.66 |
| 3 | 3.500 | 0.300 | 2.225 | 10.25 |
| 3.5 | 4.000 | 0.318 | 3.14 | 12.51 |
| 4 | 4.500 | 0.337 | 4.271 | 14.93 |
| 5 | 5.500 | 0.375 | 7.431 | 20.78 |
| 6 | 6.625 | 0.432 | 12.22 | 28.57 |
| 7 | 7.625 | 0.430 | 16.55 | 33.04 |
| 8 | 8.625 | 0.500 | 24.51 | 43.39 |
| 10 | 10.750 | 0.500 | 39.43 | 54.74 |
| 12 | 12.750 | 0.500 | 56.70 | 65.40 |
| 14 | 14.000 | 0.500 | 69.10 | 72.00 |
| 16 | 16.000 | 0.500 | 91.50 | 83.00 |
| 18 | 18.000 | 0.500 | 117.00 | 93.00 |
| 20 | 20.000 | 0.500 | 145.70 | 105.00 |
| 22 | 22.000 | 0.500 | 177.50 | 115.00 |
| 24 | 24.000 | 0.500 | 213.00 | 125.00 |
| 26 | 26.000 | 0.500 | 250.70 | 136.00 |
| 30 | 30.000 | 0.500 | 335.50 | 158.00 |
| 34 | 34.000 | 0.500 | 434.40 | 179.00 |
| 36 | 36.000 | 0.500 | 488.10 | 190.00 |
| 38 | 38.000 | 0.500 | 545.20 | 200.25 |
| 40 | 40.000 | 0.500 | 605.302 | 210.93 |
| 42 | 42.000 | 0.500 | 668.540 | 221.61 |
| 48 | 48.000 | 0.500 | 877.120 | 253.65 |
| 54 | 54.000 | 0.500 | 1113.980 | 285.69 |
| 60 | 60.000 | 0.500 | 1379.320 | 317.73 |

**Thin Wall Square Tube:**

| Nom | OD | Wall | Sect Mod | Weight (lb/ft) |
|-----|------|-------|----------|----------------|
| 2 | 2 | 0.188 | 0.716 | 4.49 |
| 2.5 | 2.5 | 0.188 | 1.20 | 5.75 |
| 3 | 3 | 0.188 | 1.81 | 7.04 |
| 3.5 | 3.5 | 0.188 | 2.54 | 8.30 |
| 4 | 4 | 0.188 | 3.40 | 9.59 |
| 5 | 5 | 0.250 | 7.01 | 15.91 |
| 6 | 6 | 0.250 | 10.40 | 19.31 |
| 7 | 7 | 0.250 | 14.40 | 22.71 |
| 8 | 8 | 0.375 | 27.20 | 38.42 |
| 10 | 10 | 0.375 | 43.90 | 48.61 |
| 12 | 12 | 0.375 | 64.30 | 58.47 |
| 14 | 14 | 0.375 | 88.60 | 68.67 |
| 16 | 16 | 0.375 | 117.00 | 78.53 |

**Heavy Wall Square Tube:**

| Nom | OD | Wall | Sect Mod | Weight (lb/ft) |
|-----|------|-------|----------|----------------|
| 2 | 2 | 0.250 | 0.852 | 5.71 |
| 2.5 | 2.5 | 0.250 | 1.46 | 7.41 |
| 3 | 3 | 0.250 | 2.24 | 9.11 |
| 3.5 | 3.5 | 0.250 | 3.18 | 10.81 |
| 4 | 4 | 0.375 | 5.76 | 18.02 |
| 5 | 5 | 0.375 | 9.63 | 23.12 |
| 6 | 6 | 0.500 | 18.00 | 36.72 |
| 7 | 7 | 0.500 | 25.50 | 43.51 |
| 8 | 8 | 0.500 | 34.40 | 50.31 |
| 10 | 10 | 0.500 | 56.20 | 63.91 |
| 12 | 12 | 0.500 | 83.30 | 77.51 |
| 14 | 14 | 0.500 | 115.00 | 90.77 |
| 16 | 16 | 0.500 | 152.00 | 104.03 |

NOTE: The pipe weight chart has MORE data than currently implemented in the playground:
- Schedule 40 extends to 60" (playground only goes to 36")
- Includes Schedule 80 pipe (not in playground)
- Includes thin wall AND heavy wall square tube variants (playground only has one set)
- Includes weight per foot data (not in playground)

### Soil Pressure (engSoilPress.htm, engSoilDlg.htm)
UBC Table 18-I-A soil values:
| Soil Type | Vertical (psf) | Lateral (psf/ft) |
|-----------|----------------|-------------------|
| Clay | 1,000 | 100 |
| Sand | 1,500 | 150 |
| Gravel | 2,000 | 200 |
| Rock | 2,000 | 400 |

Soil dialog features: 4 presets + 2 custom values, "Edit All" button, "Restore Defaults"

### Average Centroid Height (engAvg.htm)
Calculator for multiple sign cabinets - computes weighted average centroid height when a structure has multiple sign elements at different heights.

### Glossary (engGlossary.htm)
Definitions for: Area, Centroid Height, Perimeter, Support Column, Steel Type (New/Used), Wind Pressure

### Spread Footing with Rebar Cage (Spread Footing Foundations with Rebar Cage.htm)
- Rebar cage: parallel bars running vertically and horizontally on each side
- At least 3" inside outside edges of concrete foundation
- Typically 12" on center spacing
- Crosstie bars at intersections
- Created: 2002-03-18

### UI Screenshots
Available in `legacy/ui_screenshots/` (originally in CHM help):
- Image2.jpg - Section Modulus / PBF dialog window
- Image4.jpg - Anchor Bolt dialog window
- Image5.jpg - Spread Foundation dialog window
- Image6.jpg - Circular/Square/Rectangular Foundation dialog window
- Baseplate.jpg - Typical baseplate drawing (bolt holes at 1.25x bolt diameter)
- Gusset.jpg - Plan view of column baseplate connection showing gusset locations and weld pattern

## DLL/EXE Inventory (Root_Files)
### Core Application
- AbcEng.exe - Main engineering application
- Estimate.exe - Estimating application
- EstConv.exe - Estimate file converter
- UserManager.exe - User management utility

### Application Libraries
- abcapi.dll - Application API library
- abceng.dll - Engineering calculation library
- jobAPI.dll, jobRep.dll, jobWrite.dll - Job management
- CustomerCards.dll - Customer card management
- NMDBBRLib.dll - "No Magic" DB/BR library

### Microsoft MFC Runtime
- MFC42.DLL, MSVCIRT.DLL, MSVCP60.DLL, MSVCRT.DLL

### Crystal Reports (p2* series = Seagate Crystal Reports 8)
- crpe32.dll - Crystal Reports print engine
- crpaig32.dll, crxlat32.dll - Crystal Reports support
- p2bact.dll, p2bact3.dll, p2bbde.dll, p2bbtrv.dll, p2bxbse.dll - Data access
- p2ctbtrv.dll - Btrieve connectivity
- p2iract.dll, p2iract3.dll, p2ixbse.dll - Index/reporting
- p2lodbc.dll - ODBC layer
- p2molap.dll - OLAP
- p2sacl.dll, p2sdb2.dll, p2sexsr.dll, p2sfs.dll - Data sources
- p2sifmx.dll, p2smapi.dll, p2smcube.dll, p2smsiis.dll - Data sources
- p2sodbc.dll, p2solap.dll, p2soledb.dll - Data sources
- p2sora7.dll, p2soutlk.dll, p2srepl.dll - Data sources
- p2ssql.dll, p2ssyb10.dll, p2strack.dll, p2swblg.dll - Data sources
- PDSODBC.DLL - PDS ODBC driver

### Crystal Reports (u2* series = runtime/export)
- u252000.dll, u25dts.dll - Year 2000/DTS support
- u2dapp.dll, u2ddisk.dll, u2dmapi.dll, u2dnotes.dll, u2dpost.dll, u2dvim.dll - Destinations
- u2fcr.dll, u2fdif.dll, u2fhtml.dll, u2fodbc.dll - Export formats
- u2frdef.dll, u2frec.dll, u2frtf.dll, u2fsepv.dll - Export formats
- u2ftext.dll, u2fwks.dll, u2fwordw.dll, u2fxls.dll - Export formats
- u2l2000.dll, u2lbar.dll, u2lcom.dll, u2ldts.dll - Libraries
- u2lexch.dll, u2lfinra.dll, u2lsamp1.dll - Libraries

## Relationship to Playground

The Sign Engineering Calculator (sign-engineering-calculator.html) was built as a modern web-based replacement for this desktop application. Key mappings:

| Desktop Module | Playground Equivalent |
|----------------|----------------------|
| Section Modulus / PBF dialog | Section Modulus tab |
| Anchor Bolt dialog (BoltBase.vbs) | Anchor Bolt tab |
| Circ/Sq/Rect Foundation dialog (CSRFound.vbs) | Foundation tab |
| Spread Foundation dialog (SprFound.vbs) | Not yet implemented |
| Gusset table (Gusset.xls) | Gusset Table tab |
| Soil Pressure dialog | Soil Reference tab |
| PIPE[] data | Matches 21 Sch40 sizes from gusset table |
| BOLT[] data | A307 bolt sizes from base plate doc |
| Sign presets | 6 presets (not in desktop) |
| Foundation presets | 4 presets (not in desktop) |
| Auto-feasibility | Unique to playground (not in desktop) |
| SVG diagrams | Unique to playground (not in desktop) |
| Real-time recalc | Unique to playground (desktop had "Calculate" button) |

### Data Gaps (Desktop has, Playground missing)
1. Pipe weight per foot data (desktop has for all sizes)
2. Schedule 80 pipe data (desktop has full table)
3. Pipe sizes 38"-60" (desktop extends beyond 36")
4. Thin wall vs heavy wall square tube distinction
5. Square tube sizes 7, 14, 16 (desktop has 13 thin + 13 heavy sizes)
6. Spread footing foundation type
7. Average centroid height calculator
8. Sign weight estimation (6/10/15 psf by type)
9. Washer sizing for mechanical anchorage
10. Caisson anchor bolt bend/length calculations
11. Customer info and job site tracking
12. Estimate file save/load
13. Crystal Reports PDF output
14. Materials/labor/inventory databases
