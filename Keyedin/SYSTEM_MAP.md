# KeyedIn Legacy ERP — Complete System Map

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│              eaglesign.keyedinsign.com                │
│                                                       │
│  Port 443 (HTTPS) ─── KeyedIn Legacy ERP             │
│  │  CGI: /cgi-bin/mvi.exe/{FUNCTION_CODE}            │
│  │  Auth: Form-based (USERNAME/PASSWORD cookies)      │
│  │  DB: U2/UniVerse (MultiValue NoSQL)                │
│  │  UI: HTML framesets with nested iframes            │
│  │                                                    │
│  Ports 8440-8442 ──── Informer BI (3 instances LIVE) │
│  │  Multi-tenant Jetty cluster                        │
│  │                                                    │
│  Port 8443 (HTTPS) ── Informer BI Instance (DOWN)    │
│     Tenants: eaglesign                                │
│     Engine: Entrinsik Informer 5 (GWT-RPC)            │
│     30 reports configured                             │
└──────────────────────────────────────────────────────┘
```

## ERP Module Inventory — 19 Modules, 240 Functions

### 1. Contact Management (CRM)
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| CRM.CONTACT.MGT | Contact management | 24 tables, 123 rows |
| CRM.NOTES.REPORT | Contact notes report | 3 tables, 11 rows |
| CRM.SOLUTIONS.LISTING | Solutions catalog | 2 tables, 2 rows |
| CRM.ATTACHMENTS.DELETE | Attachment cleanup | 5 tables, 10 rows |

### 2. Customers
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| CUSTOMERS | Customer listing/entry | 3 tables, 28 rows |
| BILL.TO | Bill-to addresses | 4 tables, 42 rows |
| SHIP.TO | Ship-to addresses | 2 tables, 15 rows |
| CUST.PRICE.MAINT | Customer pricing | 3 tables, 6 rows |
| CUST.PROD | Customer product analysis | 2 pre blocks |
| CUST.PROD.EXPORT | Customer product export | 2 tables, 7 rows |
| CUST.SUM | Customer summary | 3 tables, 10 rows |
| LEAD.SOURCE.EVENT.LISTING | Lead sources | 2 tables, 5 rows |

### 3. Sales & Orders
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| ORDER.ENTRY | Sales order entry | 5 tables, 35 rows |
| OPEN.SO | Open sales orders | 3 tables, 18 rows |
| LOOK.SO | Sales order lookup | 5 tables, 27 rows |
| LSO | Sales order list | 3 tables, 6 rows |
| SO.COMMIT | Sales order commit | 3 tables, 12 rows |
| SO.CONTRACT | Sales contracts | 4 tables, 14 rows |
| SO.PRINT | Sales order print | 3 tables, 10 rows |
| DAY.SALES | Daily sales audit | 3 tables, 17 rows |
| DAILY.SHIP.REPORT | Daily shipping report | 3 tables, 15 rows |
| SHIPLISTS | Ship lists | 6 tables, 16 rows |
| SHIPMENTS | Shipment tracking | 3 tables, 6 rows |
| SHIPMENTS.TRACKING | Shipment details | 3 tables, 6 rows |
| ORDER.CLASSES.LIST | Order class codes | 2 tables, 14 rows |
| ORDER.TYPES.LIST | Order type codes | 2 tables, 3 rows |
| SALES.CODES.LIST | Sales codes | 2 tables, 41 rows |
| SALES.TERRITORY | Territory management | 3 tables, 12 rows |
| SALESPERSONS.LIST | Salesperson listing | 2 tables, 13 rows |
| TERRITORY.CODES.LIST | Territory codes | 2 tables, 20 rows |

### 4. Estimating / Quoting
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| EST.QUOTE.ENTRY | Quote entry form | 6 tables, 52 rows |
| EST.QUOTE.STATUS | Quote status report | 3 tables, 17 rows |
| EST.QUOTE.STATUS.CODE.LIST | Status codes | 2 tables, 32 rows |
| EST.BATCH.INACTIVE | Batch inactive | 3 tables, 14 rows |
| EST.CHANGE.ACCTID | Change account ID | 2 tables, 9 rows |
| EST.CREATE.SO | Create SO from estimate | 5 tables, 27 rows |
| EST.PROP.DELETE | Delete proposals | Empty form |
| EST.PROP.PRINT | Print proposals | 4 tables, 20 rows |
| EST.PROP.REPRINT | Reprint proposals | 3 tables, 5 rows |
| EST.PROP.RESET.DATE | Reset proposal date | 2 tables, 7 rows |
| EST.PROPOSAL.STATUS | Proposal status | 3 tables, 7 rows |
| EST.QUOTE.COPY | Copy quote | Empty form |
| EST.QUOTE.PRINT | Print quote | Empty form |
| EST.RESET.EXP.DATE | Reset expiry date | 2 tables, 7 rows |
| EST.SIGN.TEMPLATE.MAINT | Sign template maint | 4 tables, 12 rows |
| EST.TEMPLATE.PRINT | Template print | 3 tables, 4 rows |
| CONVERT.QUOTE.TO.MFG | Convert to MFG | 3 tables, 12 rows |
| QUOTE.ENTRY.LIMITED | Limited quote entry | 6 tables, 47 rows |
| QUOTE.LISTING | Quote listing | 3 tables, 14 rows |
| QUOTE.MASS.COPY | Mass copy quotes | 3 tables, 16 rows |
| QUOTE.MASS.DELETE | Mass delete quotes | 4 tables, 10 rows |
| QUOTE.MASS.UPDATE | Mass update quotes | 3 tables, 15 rows |
| QUOTE.PIPELINE.REPORT | Pipeline report | 5 tables, 22 rows |
| QUOTE.SALES.DIFFS | Quote vs sales diffs | 2 pre blocks |
| QUOTE.SALES.STAGE.CODE.LISTING | Stage codes | 2 tables, 23 rows |
| QV.PRINT | Quote view print | 4 tables, 10 rows |

### 5. Purchasing
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| PURCHASE | Purchase order entry | 3 tables, 15 rows |
| PO.ACTION.RELEASE | PO action release | 3 tables, 12 rows |
| PO.ACTIONS | PO action log | 3 tables, 9 rows |
| PO.CHANGE | PO changes | 4 tables, 21 rows |
| PO.CLOSE | PO close | 3 tables, 6 rows |
| PO.INQUIRY | PO inquiry | 3 tables, 22 rows |
| PO.RECEIPTS | PO receipts | 3 tables, 9 rows |
| PO.REQ.DELETE | Delete requisitions | 2 tables, 316 rows |
| PO.REQ.RELEASE | Release requisitions | 3 tables, 13 rows |
| PUR.COMMIT | Purchase commit | 2 tables, 11 rows |
| PUR.HISTORY | Purchase history | 3 tables, 4 rows |
| PUR.PART.VAR | Part variance | 6 tables, 48 rows |
| PUR.PO.DEL.ANALYSIS | PO delivery analysis | 4 tables, 18 rows |
| PUR.PO.SCHED.ANALYSIS | PO schedule analysis | 4 tables, 18 rows |
| PUR.PO.VAR.ANALYSIS | PO variance analysis | 6 tables, 31 rows |
| PUR.PRINT | Purchase print | 3 tables, 9 rows |
| SHOW.BUYERS | Buyer listing | 2 tables, 9 rows |
| SHOW.PO | PO display | 3 tables, 5 rows |

### 6. Inventory / Parts
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| ITEM.MASTER.LIST | Item master listing | 3 tables, 16 rows |
| PART.COST.LIST | Part cost listing | 3 tables, 14 rows |
| PART.COSTS | Part cost details | 3 tables, 15 rows |
| PART.PRICE.LIST | Part price listing | 3 tables, 12 rows |
| PART.PRICES | Part pricing | 5 tables, 40 rows |
| SHOW.PART.PRICES | Part price display | 5 tables, 40 rows |
| STOCK | Stock inquiry | 4 tables, 16 rows |
| STOCK.STATUS | Stock status | 3 tables, 27 rows |
| RAW.MATL.MAINT | Raw material maint | 2 tables, 14 rows |
| SHOW.INV.TYPES | Inventory types | 2 tables, 54 rows |
| OBSOLETE | Obsolete parts | 2 tables, 10 rows |
| USAGE.ANAL.FILE | Usage analysis | 3 tables, 17 rows |
| FIRST.ISSUE | First issue tracking | 3 tables, 8 rows |
| ISSUE | Material issue | 2 tables, 12 rows |
| SHOW.ADJUST.CODE | Adjustment codes | 2 tables, 15 rows |
| SHOW.ISSUE.REASON.CODES | Issue reason codes | 2 tables, 7 rows |
| TRANSFER | Inventory transfer | 2 tables, 9 rows |

### 7. Production / Work Orders
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| WO.INQUIRY | Work order inquiry | 4 tables, 21 rows |
| WO.CHANGE | Work order changes | 3 tables, 13 rows |
| WO.COMMENTS.MAINT | WO comments | 3 tables, 12 rows |
| WO.COMPLETION.INQUIRY | Completion inquiry | 5 tables, 24 rows |
| WO.GROUP.ANALYSIS | Group analysis | 3 tables, 4 rows |
| WO.HISTORY | WO history | 3 tables, 4 rows |
| WO.OP.STATUS | Operation status | 3 tables, 10 rows |
| WO.OPEN | Open work orders | 2 tables, 8 rows |
| WO.OPEN.PO | Open WO POs | 3 tables, 4 rows |
| WO.PRICE.CALC | WO price calc | 4 tables, 12 rows |
| WO.PRINT | WO print | 2 tables, 15 rows |
| WO.PRODUCTION.SUMMARY | Production summary | 2 tables, 12 rows |
| WO.ROUTING.MAINT | Routing maintenance | 4 tables, 14 rows |
| WO.STATUS.BILL | WO status - BOM | 3 tables, 8 rows |
| WO.STATUS.GLTRANS | WO status - GL | 3 tables, 8 rows |
| WO.STATUS.LABR | WO status - labor | 3 tables, 8 rows |
| WO.STATUS.LDTL | WO status - labor detail | 3 tables, 8 rows |
| WO.STATUS.LDTL.LIMITED | WO status - limited | 3 tables, 8 rows |
| WO.STATUS.MATDIR | WO status - direct matl | 3 tables, 8 rows |
| WO.STATUS.MATL | WO status - material | 3 tables, 8 rows |
| WO.STATUS.OUTP | WO status - output | 3 tables, 8 rows |
| WO.STATUS.SUM | WO status summary | 6 tables, 22 rows |
| WO.TO.START | WO to start | 2 tables, 4 rows |
| SHOW.WO.COMMENTS | WO comments display | 3 tables, 11 rows |
| SHOW.WO.MATL | WO material display | 3 tables, 8 rows |
| SHOW.WO.OPS | WO operations display | 3 tables, 9 rows |
| SHOW.WO.PRICE.CALC | WO price calc display | 4 tables, 7 rows |
| KILL.WO.RELEASE | Kill WO release | 2 tables, 8 rows |
| SHOW.OP.STATUS | Operation status | 2 tables, 9 rows |
| SHOW.ENGR.STATUS.CODES | Engineering status codes | 2 tables, 6 rows |

### 8. Financial / Gross Margin
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| GM.BY.INV | Gross margin by invoice | 2 pre blocks |
| GM.BY.INV.EXPORT | GM by invoice export | 2 tables, 8 rows |
| GM.BY.PROD | Gross margin by product | 2 pre blocks |
| GM.DET.PROD.PART | GM detail by part | 2 pre blocks |
| GM.PROJECT | GM by project | 2 tables, 15 rows |
| LIST.AP.DET | AP detail listing | 4 tables, 16 rows |
| COST.INQ | Cost inquiry | 4 tables, 21 rows |
| COST.POST | Cost posting | 3 tables, 17 rows |
| SA.BY.STATE | Sales analysis by state | 2 tables, 11 rows |
| TAX.BY.TYPE.REPORT | Tax by type report | 5 tables, 21 rows |
| SALES.TAXES.LIST | Tax codes listing | 2 tables, 437 rows |
| PROD.CUST | Production by customer | 2 pre blocks |
| PROD.SUM | Production summary | 2 pre blocks |
| SLSPER.PROD | Salesperson production | 2 pre blocks |
| SLSPER.PROD.EXPORT | Salesperson export | 2 tables, 7 rows |

### 9. Planning / BOM / MRP
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| PLAN.BOM | BOM planning | 3 tables, 8 rows |
| PLAN.MAINT | Plan maintenance | 4 tables, 11 rows |
| PLAN.ROUTE | Routing plan | 3 tables, 8 rows |
| LIST.PLAN | Plan listing | 3 tables, 4 rows |
| LOOK.PLAN | Plan lookup | 3 tables, 8 rows |
| PARTS.MRP | Parts MRP | 5 tables, 15 rows |
| MRP.CALC | MRP calculation | 1 tables, 1 rows |
| SHOW.MRP | MRP display | 2 tables, 4 rows |
| SUM.BILL | BOM summary | 3 tables, 8 rows |
| COPY.BILL | Copy BOM | 2 tables, 5 rows |
| COMPLETE.BILL | Complete BOM | 3 tables, 8 rows |
| ROUTING.MAINT | Routing maintenance | 3 tables, 4 rows |
| PRINT.RT | Print routing | 1 tables, 3 rows |

### 10. Production Control
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| PROD.CALENDAR | Production calendar | 3 tables, 22 rows |
| PREPLAN.REPORT | Pre-plan report | 3 tables, 12 rows |
| WIP.RECEIPTS | WIP receipts | 2 tables, 12 rows |
| WIP.RETRO | WIP retro | 2 tables, 12 rows |
| EXPORT.WIP.SUMMARY | WIP summary export | 2 tables, 12 rows |
| EXPORT.WO.LABOR.ANALYSIS | WO labor analysis | 5 tables, 22 rows |
| LABOR.TASK.BY.DEPARTMENT | Labor by dept | 6 tables, 21 rows |
| MATL.ISSUED | Material issued | 3 tables, 8 rows |
| MATL.RECEIVED | Material received | 4 tables, 11 rows |

### 11. Employee / Labor
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| EMP.EFF | Employee efficiency | 2 tables, 9 rows |
| EMP.HOURS.BY.DATE | Hours by date | 3 tables, 12 rows |
| EMP.HOURS.BY.OP | Hours by operation | 3 tables, 9 rows |
| EMP.HOURS.BY.PAY.PERIOD | Hours by pay period | 3 tables, 10 rows |
| SUM.DEPT.EFF | Dept efficiency summary | 2 tables, 3 rows |
| SUM.WC.EFF | Work center efficiency | 2 tables, 3 rows |
| RESOURCE.INQUIRY | Resource inquiry | 3 tables, 10 rows |
| RESOURCE.LIST | Resource listing | 3 tables, 9 rows |

### 12. Vendors
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| VENDORS | Vendor listing | 4 tables, 28 rows |
| VM.INQUIRY | Vendor inquiry | 3 tables, 14 rows |

### 13. System / Admin
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| COUNTRY.LIST | Country codes | 2 tables, 33 rows |
| STATES.LIST | State/Province codes | 2 tables, 65 rows |
| MY.PROFILE.MAINT | User profile | 4 tables, 11 rows |
| USER.LOGOFF | Session logoff | 2 tables, 2 rows |
| REPORT.VIEW.INDEX | Spooled report browser | 3 tables, 57 rows |
| VIEW.TRANSMITTED.FORMS | Transmitted forms log | 13 tables, 95 rows |
| SHOW.ACTIVITY | Activity log | 4 tables, 5 rows |
| CLEAR.ME | Clear session | 2 tables, 2 rows |
| SS.VALUE | System value | 1 tables, 1 rows |

### 14. Codes & Reference Data
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| ACCOUNT.TYPE.CODE.LISTING | Account type codes | 2 tables, 9 rows |
| EXTRA.CHARGES.LIST | Extra charges | 2 tables, 18 rows |
| LANDLORD.MALL.TC.LISTING | Landlord/mall codes | 3 tables, 4 rows |
| PRICE.CLASS.CODE.LIST | Price class codes | 2 tables, 6 rows |
| PRICE.CODES.LIST | Price codes | 2 tables, 10 rows |
| REASON.CODES.LIST | Reason codes | 2 tables, 8 rows |
| SHOW.UM.CODES | Unit of measure | 2 tables, 34 rows |
| SIGN.TEMPLATE.LISTING | Sign templates | 2 tables, 57 rows |
| SIGN.TYPE.CODES.LISTING | Sign types | 2 tables, 40 rows |
| WORK.CODE.LIST | Work codes | 2 tables, 64 rows |
| WORK.DEPT.LIST | Work departments | 2 tables, 23 rows |
| WORK.DEPT.LOAD | Dept workload | 3 tables, 13 rows |
| PROJECT.MILESTONE.CODES.LISTING | Milestone codes | 2 tables, 6 rows |
| PROJECT.STATUS.CODES.LISTING | Project status codes | 2 tables, 2 rows |
| PROJECT.TYPE.CODES.LISTING | Project type codes | 2 tables, 2 rows |
| SERVICE.CALL.STATUS.CODE.LISTING | Service call codes | 2 tables, 5 rows |

### 15. Service / Warranty
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| SERVICE.CALL.STATUS.REPORT | Service call status | 5 tables, 21 rows |

### 16. Import Utilities
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| IMPORT.BOM | Import BOM data | Empty form |
| IMPORT.CRM.NEW | Import CRM contacts | 1 tables, 1 rows |
| IMPORT.PARTS | Import parts | Empty form |
| IMPORT.ROUTING | Import routing | Empty form |
| IMPORT.SIGN.TEMPLATE | Import templates | Empty form |

### 17. Purchasing Reports
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| WSA.PURCHASE.REPORT | WSA purchase report | 4 tables, 10 rows |

### 18. Project Management
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| #PROJECT.* (14 functions) | Project management SPA | Identical 28KB each |

### 19. Reports / BI
| Function Code | Description | Data Type |
|--------------|-------------|-----------|
| IT.HISTORY | IT history | 1 tables, 12 rows |
| SHOW.PS | Print status | 4 tables, 12 rows |

## Informer BI Reports (30 total — port 8443)

Report IDs 1441842 through 1441871. Metadata available from prior GWT-RPC extraction.
Full data extraction pending port 8443 recovery. See `informer_watchdog.py`.

## Spooled Reports (44 total — port 443)

All 44 extracted verbatim from `REPORT.VIEW.INDEX` → `REPORT.VIEW` → `REPORT.IFRAME`.
Data stored as raw text from `<pre>` tags, preserving original formatting.
Total: 33.9 MB across 44 reports.
