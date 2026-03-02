# KeyedIn Data Capture - Session Handoff

**Date**: 2026-02-06 00:52 CST
**Status**: Informer COMPLETE, Main ERP PENDING LOGIN
**GitHub**: https://github.com/EAGLE605/signx-warehouse

---

## Session Summary

### Completed This Session

1. **Informer Reports** - ALL 30 CAPTURED
   - Captured ViewRPCService GWT-RPC request payloads for all 30 reports
   - Files saved to `C:\Scripts\keyedin-capture\reports\report_*_view_request.txt`

2. **Informer Other Sections**
   - Archives: 0 items (empty)
   - Dashboards: 0 items (empty)

3. **Main ERP Discovery**
   - Located at: `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START`
   - Technology: CGI-based (mvi.exe) - completely different from Informer GWT-RPC
   - Name: KeyedIn Manufacturing - Sign Edition
   - Status: **PENDING LOGIN** - requires authentication

4. **GitHub Repository**
   - Repo: https://github.com/EAGLE605/signx-warehouse (private)
   - 165 files committed
   - Scripts, warehouse data, manifests, screenshots

---

## Captured Informer Reports (30 Total)

| ID | Report Name |
|----|-------------|
| 1441842 | AR Invoice Details |
| 1441843 | AR Invoice Listing |
| 1441844 | AR Open Invoices |
| 1441849 | Cash Receipts |
| 1441850 | Customer Listing |
| 1441851 | Customer Listing Export |
| 1441852 | Customer Location Listing |
| 1441853 | Customer Location Listing Export |
| 1441854 | Inventory List |
| 1441855 | Inventory List Export |
| 1441856 | Inventory Transaction History |
| 1441857 | Invoice Register |
| 1441859 | Open Sales Order Backlog |
| 1441860 | Open Sales Orders |
| 1441861 | Open Work Orders |
| 1441862 | Planned Part Activity |
| 1441865 | Purchase History |
| 1441866 | Purchase Order Detail |
| 1441868 | Purchased Part Variance |
| 1441869 | Quote Status Report |
| 1441870 | Sales Cost Detail Report |
| 1441872 | Sales Order Bookings By Line Date |
| 1441873 | Sales Order Bookings By SO Date |
| 1441874 | Sales Order Detail |
| 1441875 | Sales Order Status by Customer |
| 1441877 | Sales Summary by Customer |
| 1441878 | Sales Summary by Product Type |
| 1441883 | Vendor Listing |
| 1441884 | Vendor Listing Export |
| 1441887 | Work Order Listing |

---

## Next Steps: Main ERP Capture

### Critical User Note
> "some exports dont capture FULL data with the example we figured out in the cost summary using excel vs print"

**Excel exports can TRUNCATE data** - always capture Print/View payloads, not just Excel exports.

### Main ERP Modules to Capture
Once logged in at `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START`:

- [ ] Quotes / Estimating
- [ ] Sales Orders
- [ ] Customers / Customer Locations
- [ ] Vendors
- [ ] Inventory / Parts
- [ ] Work Orders
- [ ] Purchase Orders
- [ ] Invoices / AR
- [ ] AP / Payments
- [ ] GL Transactions

---

## Technical Reference

### Two Systems

| System | URL | Technology | Status |
|--------|-----|------------|--------|
| Informer BI | Port 8443: `/eaglesign/Informer.html` | GWT-RPC v7 | COMPLETE |
| Main ERP | Port 443: `/cgi-bin/mvi.exe/` | CGI | PENDING |

### GWT-RPC Details (Informer)
- Endpoint: `/eaglesign/informer/rpc/protected/ViewRPCService`
- Content-Type: `text/x-gwt-rpc; charset=UTF-8`
- Response Format: `//OK[...]` with pipe-delimited payload
- Run Button UID: `12_63`

---

## File Locations

```
C:\Scripts\keyedin-capture\reports\    # Captured payloads (30 reports)
C:\Scripts\signx-warehouse\            # GitHub repo
├── scripts\                           # Capture/parse tools
├── warehouse\raw\                     # Extracted CSV data
└── SESSION_HANDOFF.md                 # This file
```

---

## Resume Instructions

```
Read C:\Scripts\signx-warehouse\SESSION_HANDOFF.md
```

Then: "Continue capturing Main ERP - log into browser first"

---

**Session End**: 2026-02-06 00:52 CST
**User**: Brady Flink
**Agent**: Claude Opus 4.5
