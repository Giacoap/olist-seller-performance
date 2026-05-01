import pandas as pd

files = [
    "export/seller_metrics.csv",
    "export/category_metrics.csv",
    "export/state_metrics.csv"
]

for filepath in files:
    df = pd.read_csv(filepath, encoding="utf-8-sig", decimal=",")
    df.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";", decimal=",")
    print(f"Converted: {filepath} ({len(df)} rows, {len(df.columns)} cols)")

print("Done.")
