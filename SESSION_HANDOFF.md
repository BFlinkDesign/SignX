# KeyedIn Data Capture - Session Handoff

**Date**: 2026-02-06
**Status**: Informer COMPLETE, Main ERP PENDING LOGIN

---

## Completed Work

### Informer Reports (30/30 Captured)

All GWT-RPC ViewRPCService request payloads captured from KeyedIn Informer BI module.

**Location**: `C:\Scripts\keyedin-capture\reports\`
**Naming Convention**: `report_{slug}_view_request.txt`

| Report ID | Report Name | File |
|-----------|-------------|------|
| 1441842 | AR Invoice Details | report_ar_invoice_details_view_request.txt |
| 1441843 | AR Invoice Listing | report_ar_invoice_listing_view_request.txt |
| 1441844 | AR Open Invoices | report_ar_open_invoices_view_request.txt |
| 1441849 | Cash Receipts | report_cash_receipts_view_request.txt |
| 1441850 | Customer Listing | report_customer_listing_view_request.txt |
| 1441851 | Customer Listing Export | report_customer_listing_export_view_request.txt |
| 1441852 | Customer Location Listing | report_customer_location_listing_view_request.txt |
| 1441853 | Customer Location Listing Export | report_customer_location_listing_export_view_request.txt |
| 1441854 | Inventory List | report_inventory_list_view_request.txt |
| 1441855 | Inventory List Export | report_inventory_list_export_view_request.txt |
| 1441856 | Inventory Transaction History | report_inventory_transaction_history_view_request.txt |
| 1441857 | Invoice Register | report_invoice_register_view_request.txt |
| 1441859 | Open Sales Order Backlog | report_open_sales_order_backlog_view_request.txt |
| 1441860 | Open Sales Orders | report_open_sales_orders_view_request.txt |
| 1441861 | Open Work Orders | report_open_work_orders_view_request.txt |
| 1441862 | Planned Part Activity | report_planned_part_activity_view_request.txt |
| 1441865 | Purchase History | report_purchase_history_view_request.txt |
| 1441866 | Purchase Order Detail | report_purchase_order_detail_view_request.txt |
| 1441868 | Purchased Part Variance | report_purchased_part_variance_view_request.txt |
| 1441869 | Quote Status Report | report_quote_status_report_view_request.txt |
| 1441870 | Sales Cost Detail Report | report_sales_cost_detail_report_view_request.txt |
| 1441872 | Sales Order Bookings By Line Date | report_sales_order_bookings_by_line_date_view_request.txt |
| 1441873 | Sales Order Bookings By SO Date | report_sales_order_bookings_by_so_date_view_request.txt |
| 1441874 | Sales Order Detail | report_sales_order_detail_view_request.txt |
| 1441875 | Sales Order Status by Customer | report_sales_order_status_by_customer_view_request.txt |
| 1441877 | Sales Summary by Customer | report_sales_summary_by_customer_view_request.txt |
| 1441878 | Sales Summary by Product Type | report_sales_summary_by_product_type_view_request.txt |
| 1441883 | Vendor Listing | report_vendor_listing_view_request.txt |
| 1441884 | Vendor Listing Export | report_vendor_listing_export_view_request.txt |
| 1441887 | Work Order Listing | report_work_order_listing_view_request.txt |

**Informer Other Sections**:
- Archives: 0 items (empty)
- Dashboards: 0 items (empty)

---

## Pending Work

### Main KeyedIn ERP - Data Capture

**Status**: At login page, requires authentication

**URLs**:
- Login: `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START`
- System: KeyedIn Manufacturing - Sign Edition
- Technology: CGI-based (mvi.exe) - NOT GWT-RPC

**Modules to Capture** (once logged in):
- Quotes / Estimating
- Sales Orders
- Customers
- Customer Locations
- Vendors
- Inventory / Parts
- Work Orders
- Purchase Orders
- Invoices / AR
- AP / Payments
- GL Transactions

**CRITICAL NOTE**:
> "some exports dont capture FULL data with the example we figured out in the cost summary using excel vs print"

**Excel exports can TRUNCATE data** - always capture Print/View payloads, not just Excel exports.

---

## Technical Details

### Informer System (COMPLETED)
- **URL**: `https://eaglesign.keyedinsign.com:8443/eaglesign/Informer.html`
- **Protocol**: GWT-RPC v7 (pipe-delimited)
- **Endpoint**: `/eaglesign/informer/rpc/protected/ViewRPCService`
- **Content-Type**: `text/x-gwt-rpc; charset=UTF-8`
- **Navigation**: Hash-based (`#action=ReportRun&reportId={ID}`)
- **Run Button UID**: `12_63` (consistent across reports)

### Main ERP (PENDING)
- **URL**: `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/`
- **Protocol**: Traditional HTTP form posts (CGI)
- **Authentication**: Form-based (username/password)
- **Backend**: mvi.exe CGI application

### Server Contexts (Port 8443)
All are Informer BI modules:
- `/eaglesign` - Eagle Sign (primary)
- `/graphicfx` - GraphicFX
- `/naglesigns` - Nagle Signs

---

## File Locations

```
C:\Scripts\keyedin-capture\
├── reports\                    # Captured payloads
│   ├── report_*_view_request.txt
│   ├── report_*_view_response.txt
│   ├── report_*_cmd_request.txt
│   └── raw_captures.json       # Original capture data
├── SESSION_HANDOFF.md          # This file
└── ...

C:\Scripts\signx-warehouse\scripts\
├── split_captures.py           # Splits raw_captures.json into individual files
├── capture_hook.js             # Browser console hook (alternative capture method)
└── scrape_informer.py          # Uses captured payloads for automation
```

---

## Pipeline

```
capture_hook.js (browser console)
       ↓
raw_captures.json
       ↓
split_captures.py
       ↓
report_*_view_request.txt (individual payloads)
       ↓
scrape_informer.py → CSV files
```

---

## To Resume

1. **Log into Main ERP**:
   - Navigate to: `https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START`
   - Enter credentials and sign in

2. **Capture Strategy for Main ERP**:
   - Use Chrome DevTools Network tab
   - Navigate to each module (Quotes, Sales Orders, etc.)
   - Use **Print/View** functions (NOT Excel export)
   - Capture POST requests to mvi.exe endpoints
   - Save request/response payloads

3. **MCP Tools Available**:
   - `mcp__chrome-devtools__navigate_page`
   - `mcp__chrome-devtools__click`
   - `mcp__chrome-devtools__fill`
   - `mcp__chrome-devtools__list_network_requests`
   - `mcp__chrome-devtools__get_network_request`
   - `mcp__chrome-devtools__take_snapshot`

---

## Session Context

**User**: Brady Flink (logged into Informer as Brady Flink)
**Browser**: Chrome with DevTools Protocol enabled
**Current Page**: Main ERP login page

**Original Request**:
> "capture EVERYTHING in the main erp - remember some exports dont capture FULL data with the example we figured out in the cost summary using excel vs print"
