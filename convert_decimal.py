import pandas as pd

files = {
    "export/seller_metrics.csv": ["avg_review_score","negative_review_rate",
                                   "on_time_rate","avg_delay_days",
                                   "avg_dispatch_days","gmv","avg_freight_ratio"],
    "export/category_metrics.csv": ["avg_review_score","late_rate","avg_freight_ratio"],
    "export/state_metrics.csv": ["median_review_score","median_on_time_rate",
                                  "median_freight_ratio","median_dispatch_days",
                                  "total_gmv","pct_top"]
}

for filepath, decimal_cols in files.items():
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df.to_csv(filepath, index=False, encoding="utf-8-sig", decimal=",")
    print(f"Converted: {filepath}")

print("Done.")
