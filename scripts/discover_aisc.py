"""Quick discovery script to see sheet names and columns in the AISC Excel file."""
import sys
import pandas as pd

XLSX = "C:/Users/Brady.EAGLE/Desktop/SIGNX/info/aisc-shapes-database-v16.0_a1085.xlsx"

print("Loading Excel file...", flush=True)
xl = pd.ExcelFile(XLSX)

print(f"\nFound {len(xl.sheet_names)} sheets:", flush=True)
for s in xl.sheet_names:
    print(f"  {repr(s)}", flush=True)

print("\n--- Column headers per sheet (first 5 rows) ---", flush=True)
for sheet in xl.sheet_names:
    df = xl.parse(sheet, nrows=3)
    print(f"\n[{sheet}]  shape={df.shape}", flush=True)
    print(f"  columns: {list(df.columns)[:30]}", flush=True)
    if len(df) > 0:
        print(f"  row0: {dict(list(df.iloc[0].items())[:10])}", flush=True)

print("\nDone.", flush=True)
sys.stdout.flush()
