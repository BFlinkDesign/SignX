import pandas as pd
import numpy as np
import os
import datetime
import openai
from sklearn.ensemble import IsolationForest
from dotenv import load_dotenv

# ---- Config ---- #
WORK_ORDER_CSV = "work_orders.csv"
ALIAS_FILE = "workcode_aliases.csv"
FEEDBACK_FILE = "flywheel_feedback.csv"
AUDIT_FILE = "audit_log.csv"
LABOR_BENCHMARK_FILE = "labor_benchmark.xlsx"
MATERIAL_BENCHMARK_FILE = "material_benchmark.xlsx"
OUTLIER_FILE = "outlier_log.csv"

# Load OpenAI Key
load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")

def log_audit(event, details):
    log_entry = {
        "Timestamp": datetime.datetime.now().isoformat(),
        "Event": event,
        "Details": str(details)
    }
    mode = 'a' if os.path.exists(AUDIT_FILE) else 'w'
    df = pd.DataFrame([log_entry])
    df.to_csv(AUDIT_FILE, mode=mode, header=not os.path.exists(AUDIT_FILE), index=False)

def load_alias_map():
    if os.path.exists(ALIAS_FILE):
        alias_df = pd.read_csv(ALIAS_FILE)
        return dict(zip(alias_df['alias'], alias_df['work_code']))
    return {}

def clean_workcodes(df, alias_map):
    df['WorkCode'] = df['WorkCode'].astype(str).str.strip().str.upper()
    df['WorkCode'] = df['WorkCode'].replace(alias_map)
    return df

def apply_feedback(df):
    if os.path.exists(FEEDBACK_FILE):
        fb = pd.read_csv(FEEDBACK_FILE)
        for _, row in fb.iterrows():
            if not pd.isna(row.get("OverrideLaborHours")):
                mask = (df["WorkCode"] == row["WorkCode"]) & (df["Description"] == row["Description"])
                df.loc[mask, "ActualLaborHours"] = row["OverrideLaborHours"]
                log_audit("OverrideLaborHours", dict(row))
    return df

def labor_benchmark(df):
    labor = df[['WorkCode', 'Description', 'ActualLaborHours']].dropna()
    labor = labor[labor['ActualLaborHours'] > 0]
    summary = (labor
        .groupby(['WorkCode', 'Description'])
        .agg(
            Low=('ActualLaborHours', 'min'),
            Mean=('ActualLaborHours', 'mean'),
            High=('ActualLaborHours', 'max'),
            Stdev=('ActualLaborHours', 'std'),
            CVpct=('ActualLaborHours', lambda x: np.std(x)/np.mean(x)*100 if np.mean(x) > 0 else np.nan),
            Count=('ActualLaborHours', 'count')
        )
        .reset_index()
    )
    summary['Recommended Hrs/Unit'] = (summary['Mean']*4).round()/4
    return summary

def material_benchmark(df):
    material = df[['MaterialPartNumber', 'MaterialDescription', 'QuantityUsed']].dropna()
    material = material[material['QuantityUsed'] > 0]
    summary = (material
        .groupby(['MaterialPartNumber', 'MaterialDescription'])
        .agg(
            Avg_Qty=('QuantityUsed', 'mean'),
            Stdev=('QuantityUsed', 'std'),
            CVpct=('QuantityUsed', lambda x: np.std(x)/np.mean(x)*100 if np.mean(x) > 0 else np.nan),
            Count=('QuantityUsed', 'count')
        )
        .reset_index()
    )
    return summary

def detect_outliers_ai(df, labor_summary):
    all_outliers = []
    for _, row in labor_summary.iterrows():
        code, desc = row['WorkCode'], row['Description']
        code_df = df[(df['WorkCode'] == code) & (df['Description'] == desc)]
        if len(code_df) < 5:
            continue  # not enough data for AI
        X = code_df[['ActualLaborHours']].values
        iso = IsolationForest(contamination=0.1, random_state=42)
        code_df['OutlierAI'] = iso.fit_predict(X)
        outliers = code_df[code_df['OutlierAI'] == -1]
        for idx, r in outliers.iterrows():
            all_outliers.append({
                'WorkCode': code,
                'Description': desc,
                'LaborHour': r['ActualLaborHours'],
                'WO_ID': r.get('WorkOrderID', ''),
                'Reason': 'AI Outlier'
            })
    if all_outliers:
        pd.DataFrame(all_outliers).to_csv(OUTLIER_FILE, index=False)
        log_audit("OutliersDetected", f"{len(all_outliers)} outliers logged by AI")

def gpt_explain_outliers():
    if not os.path.exists(OUTLIER_FILE):
        return
    outliers = pd.read_csv(OUTLIER_FILE)
    for idx, row in outliers.iterrows():
        prompt = (f"Root cause analysis: In our manufacturing benchmark dataset, "
                  f"work code '{row['WorkCode']}' for '{row['Description']}' had an actual labor hour of {row['LaborHour']}. "
                  f"This was flagged as an outlier. Give a brief root cause hypothesis and action to correct.")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert operations analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            result = response.choices[0].message['content'].strip()
            outliers.loc[idx, "GPT_Explanation"] = result
            log_audit("GPTExplain", dict(row) | {"GPT_Explanation": result})
        except Exception as e:
            outliers.loc[idx, "GPT_Explanation"] = f"Error: {e}"
    outliers.to_csv(OUTLIER_FILE, index=False)

def save_outputs(labor_summary, material_summary):
    with pd.ExcelWriter(LABOR_BENCHMARK_FILE, engine='openpyxl') as writer:
        labor_summary.to_excel(writer, index=False, sheet_name='Labor Benchmark')
        material_summary.to_excel(writer, index=False, sheet_name='Material Benchmark')

def main():
    alias_map = load_alias_map()
    df = pd.read_csv(WORK_ORDER_CSV)
    df = clean_workcodes(df, alias_map)
    df = apply_feedback(df)
    labor_summary = labor_benchmark(df)
    material_summary = material_benchmark(df)
    save_outputs(labor_summary, material_summary)
    detect_outliers_ai(df, labor_summary)
    gpt_explain_outliers()
    print(f"✅ ALL DONE. See '{LABOR_BENCHMARK_FILE}', '{MATERIAL_BENCHMARK_FILE}', and '{OUTLIER_FILE}'. Audit in '{AUDIT_FILE}'.")

if __name__ == "__main__":
    main()
