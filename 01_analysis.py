"""
olist-seller-performance -- análisis principal

Ver 00_scoping.md para la pregunta de negocio, sub-preguntas y métricas.
Cada sección de este script mapea a una sub-pregunta del scoping document.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# Phase 1: Load and clean
# ==============================================================================
# Loads all 9 source CSVs, parses date columns, applies scoping-defined filters,
# and resolves known data quality issues before any metric calculation.
# Quality findings are printed at the end of this section.

# ── 1.1 Raw load ──────────────────────────────────────────────────────────────

DATE_COLS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
    "order_items": ["shipping_limit_date"],
}

orders_raw       = pd.read_csv("data/olist_orders_dataset.csv",                encoding="utf-8")
order_items_raw  = pd.read_csv("data/olist_order_items_dataset.csv",           encoding="utf-8")
payments_raw     = pd.read_csv("data/olist_order_payments_dataset.csv",        encoding="utf-8")
reviews_raw      = pd.read_csv("data/olist_order_reviews_dataset.csv",         encoding="utf-8")
customers_raw    = pd.read_csv("data/olist_customers_dataset.csv",             encoding="utf-8")
sellers_raw      = pd.read_csv("data/olist_sellers_dataset.csv",               encoding="utf-8")
products_raw     = pd.read_csv("data/olist_products_dataset.csv",              encoding="utf-8")
geolocation_raw  = pd.read_csv("data/olist_geolocation_dataset.csv",           encoding="utf-8")
cat_translation  = pd.read_csv("data/product_category_name_translation.csv",   encoding="utf-8")

# ── 1.2 Parse dates ───────────────────────────────────────────────────────────

for col in DATE_COLS["orders"]:
    orders_raw[col] = pd.to_datetime(orders_raw[col], errors="coerce")

for col in DATE_COLS["reviews"]:
    reviews_raw[col] = pd.to_datetime(reviews_raw[col], errors="coerce")

order_items_raw["shipping_limit_date"] = pd.to_datetime(
    order_items_raw["shipping_limit_date"], errors="coerce"
)

# ── 1.3 Filter to delivered orders (core analysis scope) ─────────────────────
# Scoping doc §6: only orders with order_status = 'delivered' are included.

orders = orders_raw[orders_raw["order_status"] == "delivered"].copy()

# ── 1.4 Clean reviews ─────────────────────────────────────────────────────────
# Two issues found:
#   a) 814 duplicate review_id rows -- exact record duplicates, drop all but first.
#   b) 551 order_ids appear in more than one review row (customer re-submitted
#      or system duplicate). Strategy: keep the most recent by review_creation_date
#      so the latest signal is used. This affects <0.6% of reviews.

reviews = (
    reviews_raw
    .drop_duplicates(subset="review_id", keep="first")
    .sort_values("review_creation_date", ascending=False)
    .drop_duplicates(subset="order_id", keep="first")
    .reset_index(drop=True)
)

# ── 1.5 Clean geolocation ─────────────────────────────────────────────────────
# 261,831 fully duplicate rows (same zip, lat, lng). Drop exact duplicates, then
# aggregate to state level (median lat/lng) as specified in scoping doc §6.
# Zip-level precision is noisy; state-level is sufficient for geographic analysis.

geo_states = (
    geolocation_raw
    .drop_duplicates()
    .groupby("geolocation_state", as_index=False)
    .agg(lat=("geolocation_lat", "median"), lng=("geolocation_lng", "median"))
)

# ── 1.6 Add English category names to products ────────────────────────────────
# Two categories present in products have no translation entry in the Kaggle
# source file. Manual translations added here for traceability:
#
#   'pc_gamer'
#       -> 'pc_gamer'
#       Rationale: widely understood as-is; no standard Portuguese expansion
#       exists. Kept identical to the Portuguese original.
#
#   'portateis_cozinha_e_preparadores_de_alimentos'
#       -> 'portable_kitchen_food_processors'
#       Rationale: direct translation of "portáteis de cozinha e preparadores
#       de alimentos" (portable kitchen appliances and food processors).
#
# Both are added to the lookup before merging so the merge is deterministic
# and the source of each translation is auditable.

extra_translations = pd.DataFrame({
    "product_category_name": [
        "pc_gamer",
        "portateis_cozinha_e_preparadores_de_alimentos",
    ],
    "product_category_name_english": [
        "pc_gamer",
        "portable_kitchen_food_processors",
    ],
})
cat_translation_full = pd.concat([cat_translation, extra_translations], ignore_index=True)

products = products_raw.merge(cat_translation_full, on="product_category_name", how="left")
# After merge: 610 products retain null product_category_name (no category in
# source data). These rows are kept in all general joins and metric calculations.
# They are excluded only in sub-questions that depend specifically on category
# (SQ5 -- category-level outcomes; SQ8 -- top performer profile by category).
# All other metrics treat them as ordinary products.

# ── 1.7 Pass-through tables (no cleaning needed) ──────────────────────────────

order_items = order_items_raw.copy()
payments    = payments_raw.copy()
customers   = customers_raw.copy()
sellers     = sellers_raw.copy()

# ── 1.8 Data quality report ───────────────────────────────────────────────────

print("=" * 70)
print("PHASE 1 -- DATA QUALITY REPORT")
print("=" * 70)

print(f"\n[orders]")
print(f"  Total rows: {len(orders_raw):,}  |  Delivered (core scope): {len(orders):,}")
print(f"  order_status distribution:")
for status, n in orders_raw["order_status"].value_counts().items():
    print(f"    {status:<15} {n:>6,}")
print(f"  Date nulls in DELIVERED subset:")
for col in DATE_COLS["orders"]:
    n = orders[col].isnull().sum()
    if n > 0:
        print(f"    {col}: {n} nulls  -> excluded from metrics that require this column")

print(f"\n[order_items]")
print(f"  Rows: {len(order_items):,}  (>{len(orders):,} orders -> multi-item orders)")
print(f"  price: min={order_items['price'].min():.2f}, max={order_items['price'].max():.2f} -- no zero/negative prices")
print(f"  freight_value: min={order_items['freight_value'].min():.2f} (free shipping exists), max={order_items['freight_value'].max():.2f}")

print(f"\n[payments]")
print(f"  Rows: {len(payments):,}  (>{len(orders):,} orders -> split/multiple payments per order)")
print(f"  Nulls: none")

print(f"\n[reviews]")
print(f"  Raw rows: {len(reviews_raw):,}")
print(f"  Duplicate review_id rows dropped: {reviews_raw.duplicated(subset='review_id').sum()}")
dup_orders_before = reviews_raw.drop_duplicates(subset='review_id')['order_id'].duplicated().sum()
print(f"  Duplicate order_id rows (kept latest): {dup_orders_before}")
print(f"  Clean rows: {len(reviews):,}")
print(f"  review_score distribution:")
for score, n in reviews["review_score"].value_counts().sort_index().items():
    print(f"    {score}: {n:,}")
print(f"  review_comment_title null:   {reviews['review_comment_title'].isnull().sum():,}  ({reviews['review_comment_title'].isnull().mean()*100:.1f}%) -- optional field")
print(f"  review_comment_message null: {reviews['review_comment_message'].isnull().sum():,}  ({reviews['review_comment_message'].isnull().mean()*100:.1f}%) -- optional field")

print(f"\n[customers]")
print(f"  Rows: {len(customers):,}  |  Unique customer_id: {customers['customer_id'].nunique():,}")
print(f"  Unique customer_unique_id: {customers['customer_unique_id'].nunique():,}  ({len(customers)-customers['customer_unique_id'].nunique():,} repeat customers across multiple orders)")
print(f"  Nulls: none")

print(f"\n[sellers]")
print(f"  Rows: {len(sellers):,}  |  States represented: {sellers['seller_state'].nunique()}")
print(f"  Nulls: none")

print(f"\n[products]")
print(f"  Rows: {len(products):,}")
print(f"  product_category_name null: {products['product_category_name'].isnull().sum()} -- no category in source, will be treated as 'unknown' per metric")
print(f"  Categories missing translation (patched manually): pc_gamer, portateis_cozinha_e_preparadores_de_alimentos")
print(f"  product_weight/dimensions null: {products['product_weight_g'].isnull().sum()} rows -- not used in core metrics")

print(f"\n[geolocation]")
print(f"  Raw rows: {len(geolocation_raw):,}  |  Exact duplicate rows dropped: {geolocation_raw.duplicated().sum():,}")
print(f"  Unique zip prefixes: {geolocation_raw['geolocation_zip_code_prefix'].nunique():,}")
print(f"  Aggregated to state level: {len(geo_states)} states")
print(f"  (Zip-level precision not used -- multiple coords per prefix, noisy)")

print(f"\n[category_translation]")
print(f"  Rows: {len(cat_translation):,} original  +  2 manual additions = {len(cat_translation_full):,} total")
print(f"  Nulls: none")

print("\n" + "=" * 70)
print("SUMMARY -- items to carry into Phase 2")
print("=" * 70)
print("""
  1. Core scope: 96,478 delivered orders (96.5% of 99,441 total).

  2. orders -- small null counts in delivered subset:
       order_approved_at: 14 nulls  -> exclude from Dispatch Speed (Metric 7)
       order_delivered_carrier_date: 2 nulls  -> exclude from Dispatch Speed
       order_delivered_customer_date: 8 nulls  -> exclude from On-Time Delivery Rate (Metric 4)

  3. reviews -- 814 duplicate review_id + 551 duplicate order_id rows resolved.
     Strategy: drop duplicate review_id (exact copies), then keep latest review
     per order_id. Net effect: <0.6% of rows affected.

  4. products -- 610 rows with no category name. Keep as null; flag in
     category-level analysis (SQ5).

  5. geolocation -- aggregated to state level (median lat/lng per state).
     Zip-level not used per scoping §6.

  6. Two product categories lacked translation entries; patched manually.

  7. customers -- customer_id is order-scoped (99,441 unique); 96,096 unique
     individuals. This distinction matters if customer-level repeat analysis
     is ever added (not in current scope).

  8. payments has more rows than orders (split payments, vouchers + card).
     When joining, aggregate payment_value per order_id to avoid row inflation.
""")

# ==============================================================================
# Phase 2: EDA
# ==============================================================================
# Covers the full dataset before any seller-level metric aggregation.
# Each subsection has a print block (key numbers) and one or more saved charts.
# Findings in this section drive the empirical thresholds used in Phase 3.
#
# Charts are saved to charts/eda/. Directory is created if it does not exist.

import os
os.makedirs("charts/eda", exist_ok=True)

# Color palette used throughout -- muted, consistent across all charts.
PALETTE   = sns.color_palette("muted")
C_BLUE    = PALETTE[0]
C_ORANGE  = PALETTE[1]
C_GREEN   = PALETTE[2]
C_RED     = PALETTE[3]

# ── 2.0 Core join ─────────────────────────────────────────────────────────────
# Single flat table used across all EDA sub-sections.
# One row = one order-item in a delivered order, with review attached.
#
# Handling:
#   - reviews joined via order_id; unreviewed orders get NaN review_score
#   - products joined via product_id (left join keeps null-category items)
#   - sellers joined via seller_id
#   - customers joined via customer_id

df = (
    order_items
    .merge(orders[["order_id", "customer_id",
                   "order_purchase_timestamp",
                   "order_approved_at",
                   "order_delivered_carrier_date",
                   "order_delivered_customer_date",
                   "order_estimated_delivery_date"]],
           on="order_id", how="inner")   # inner = delivered orders only
    .merge(reviews[["order_id", "review_score"]], on="order_id", how="left")
    .merge(products[["product_id", "product_category_name_english"]],
           on="product_id", how="left")
    .merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")
    .merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
)

# Derived columns used across multiple EDA sections.
df["delay_days"]    = (df["order_delivered_customer_date"] -
                       df["order_estimated_delivery_date"]).dt.total_seconds() / 86400
df["dispatch_days"] = (df["order_delivered_carrier_date"] -
                       df["order_approved_at"]).dt.total_seconds() / 86400
df["freight_ratio"] = df["freight_value"] / df["price"]
df["order_month"]   = df["order_purchase_timestamp"].dt.to_period("M")

print(f"Core df shape: {df.shape}  "
      f"({df['order_id'].nunique():,} orders, {df['seller_id'].nunique():,} sellers, "
      f"{df['product_category_name_english'].nunique()} categories)")

# ── 2.1 Temporal distribution ─────────────────────────────────────────────────

monthly = df.drop_duplicates("order_id").groupby("order_month").size()

fig, ax = plt.subplots(figsize=(12, 4))
ax.bar(monthly.index.astype(str), monthly.values, color=C_BLUE, width=0.7)
ax.set_title("Monthly delivered order volume (Sep 2016 -- Aug 2018)", fontsize=13)
ax.set_xlabel("Month")
ax.set_ylabel("Number of delivered orders")
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
plt.savefig("charts/eda/01_monthly_volume.png", dpi=150)
plt.close()

print("\n[2.1 Temporal distribution]")
print(f"  Date range: {df['order_purchase_timestamp'].min().date()} to "
      f"{df['order_purchase_timestamp'].max().date()}")
print(f"  Peak month: {monthly.idxmax()} ({monthly.max():,} orders)")
print(f"  Low month:  {monthly.idxmin()} ({monthly.min():,} orders)")

# ── 2.2 Review score distribution ─────────────────────────────────────────────
# Two views: (a) per-order score, (b) per-seller average score (>=5 orders).

# (a) Order-level
order_reviews = df.drop_duplicates("order_id")[["order_id", "review_score"]]
score_counts  = order_reviews["review_score"].value_counts().sort_index()
coverage      = order_reviews["review_score"].notna().mean() * 100

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

axes[0].bar(score_counts.index, score_counts.values, color=C_BLUE, edgecolor="white")
axes[0].set_title("Review score distribution -- per order", fontsize=12)
axes[0].set_xlabel("Review score (1-5)")
axes[0].set_ylabel("Number of orders")
axes[0].set_xticks([1, 2, 3, 4, 5])
for i, (score, cnt) in enumerate(score_counts.items()):
    axes[0].text(score, cnt + 200, f"{cnt:,}", ha="center", fontsize=9)

# (b) Seller-level (>=5 orders)
order_seller = df[["order_id", "seller_id", "review_score"]].drop_duplicates("order_id")
seller_order_count = order_seller.groupby("seller_id")["order_id"].nunique()
eligible_sellers   = seller_order_count[seller_order_count >= 5].index
seller_avg_score   = (
    order_seller[order_seller["seller_id"].isin(eligible_sellers)]
    .groupby("seller_id")["review_score"].mean()
)

axes[1].hist(seller_avg_score.dropna(), bins=40, color=C_GREEN, edgecolor="white")
axes[1].axvline(seller_avg_score.median(), color=C_RED, linestyle="--",
                label=f"Median: {seller_avg_score.median():.2f}")
axes[1].set_title("Avg review score per seller (sellers with >=5 orders, n=1,766)", fontsize=12)
axes[1].set_xlabel("Average review score")
axes[1].set_ylabel("Number of sellers")
axes[1].legend()

plt.tight_layout()
plt.savefig("charts/eda/02_review_score_dist.png", dpi=150)
plt.close()

print("\n[2.2 Review score distribution]")
print(f"  Review coverage on delivered orders: {coverage:.1f}%")
print(f"  Order-level score counts: {score_counts.to_dict()}")
print(f"  Sellers >=5 orders (tier-eligible): {len(eligible_sellers):,}")
print(f"  Seller avg score -- mean: {seller_avg_score.mean():.3f}  "
      f"std: {seller_avg_score.std():.3f}  "
      f"median: {seller_avg_score.median():.3f}")
print(f"  p25: {seller_avg_score.quantile(0.25):.3f}  "
      f"p10: {seller_avg_score.quantile(0.10):.3f}  "
      f"p90: {seller_avg_score.quantile(0.90):.3f}")
pct_below4 = (seller_avg_score < 4.0).mean() * 100
print(f"  Sellers with avg score < 4.0: {pct_below4:.1f}%")

# ── 2.3 Delivery performance ──────────────────────────────────────────────────
# On-time delivery rate overall; delay magnitude for late orders.

order_delivery = df.drop_duplicates("order_id")[
    ["order_id", "seller_id", "delay_days"]
].copy()
total_with_date = order_delivery["delay_days"].notna().sum()
on_time_n = (order_delivery["delay_days"] <= 0).sum()
late_n    = (order_delivery["delay_days"] > 0).sum()
on_time_rate = on_time_n / total_with_date * 100

late_delays = order_delivery[order_delivery["delay_days"] > 0]["delay_days"]

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Bar: on-time vs late
axes[0].bar(["On time", "Late"], [on_time_n, late_n],
            color=[C_GREEN, C_RED], edgecolor="white")
axes[0].set_title("Delivery timeliness -- delivered orders", fontsize=12)
axes[0].set_ylabel("Number of orders")
for i, v in enumerate([on_time_n, late_n]):
    axes[0].text(i, v + 300, f"{v:,}\n({v/total_with_date*100:.1f}%)",
                 ha="center", fontsize=10)

# Histogram: delay magnitude (late only, clipped at 60 days to show distribution)
clip_days = 60
late_clipped = late_delays.clip(upper=clip_days)
axes[1].hist(late_clipped, bins=40, color=C_RED, edgecolor="white")
axes[1].axvline(late_delays.median(), color="black", linestyle="--",
                label=f"Median: {late_delays.median():.1f} days")
axes[1].set_title(f"Delay magnitude -- late orders only (clipped at {clip_days} days)", fontsize=12)
axes[1].set_xlabel("Days late")
axes[1].set_ylabel("Number of orders")
axes[1].legend()

plt.tight_layout()
plt.savefig("charts/eda/03_delivery_performance.png", dpi=150)
plt.close()

print("\n[2.3 Delivery performance]")
print(f"  Orders with delivery date: {total_with_date:,}")
print(f"  On time: {on_time_n:,} ({on_time_rate:.1f}%)  |  Late: {late_n:,} ({100-on_time_rate:.1f}%)")
print(f"  Late delay -- median: {late_delays.median():.1f} days  "
      f"mean: {late_delays.mean():.1f} days  "
      f"max: {late_delays.max():.1f} days")
print(f"  >30 days late: {(late_delays>30).sum():,}  |  >60 days: {(late_delays>60).sum():,}")

# ── 2.4 Dispatch speed ────────────────────────────────────────────────────────
# Days from order_approved_at to order_delivered_carrier_date.
#
# Anomaly: 1,350 rows (1.4%) have dispatch_days < 0, meaning
# order_delivered_carrier_date < order_approved_at. Investigation confirmed:
#   - All 1,350 have approved_at strictly after carrier_date (no exceptions).
#   - 165 cases have carrier_date before the purchase_timestamp itself --
#     the most extreme form of the anomaly.
#   - Magnitude distribution: 48% within 0.5 days, 66% within 6 hours,
#     97% within 10 days; one extreme outlier at -171 days.
#   - Probable cause: Olist's payment system logs order_approved_at as the
#     business-processing timestamp (sometimes rounded to the next business
#     day or batch-processed), while the carrier system logs the actual
#     physical pickup time in real-time. For the sub-hour cases this is a
#     clock/rounding artefact; for multi-day cases the seller likely
#     arranged carrier pickup before payment was formally confirmed in
#     Olist's back-office (e.g., boleto bancario, which has a payment lag).
#
# Decision: exclude these 1,350 rows only from Dispatch Speed (Metric 7).
# Orders are retained in all other metrics unchanged.

order_dispatch = df.drop_duplicates("order_id")[["order_id", "dispatch_days"]].copy()
neg_dispatch   = (order_dispatch["dispatch_days"] < 0).sum()
dispatch_valid = order_dispatch[order_dispatch["dispatch_days"] >= 0]["dispatch_days"]

fig, ax = plt.subplots(figsize=(9, 5))
clip_disp = 30
ax.hist(dispatch_valid.clip(upper=clip_disp), bins=40, color=C_BLUE, edgecolor="white")
ax.axvline(dispatch_valid.median(), color=C_RED, linestyle="--",
           label=f"Median: {dispatch_valid.median():.1f} days")
ax.set_title(f"Dispatch speed -- approved to carrier handoff (clipped at {clip_disp} days)", fontsize=12)
ax.set_xlabel("Days (order_approved_at -> order_delivered_carrier_date)")
ax.set_ylabel("Number of orders")
ax.legend()
plt.tight_layout()
plt.savefig("charts/eda/04_dispatch_speed.png", dpi=150)
plt.close()

print("\n[2.4 Dispatch speed]")
print(f"  Negative dispatch days (anomaly, excluded from metric): {neg_dispatch:,} "
      f"({neg_dispatch/order_dispatch['dispatch_days'].notna().sum()*100:.1f}%)")
print(f"  Valid dispatch -- median: {dispatch_valid.median():.2f} days  "
      f"mean: {dispatch_valid.mean():.2f}  "
      f"p75: {dispatch_valid.quantile(0.75):.2f}  "
      f"p90: {dispatch_valid.quantile(0.90):.2f}")
print(f"  Same-day or next-day dispatch (<=1 day): "
      f"{(dispatch_valid <= 1).mean()*100:.1f}%")
print(f"  >5 days to dispatch: {(dispatch_valid > 5).mean()*100:.1f}%")

# ── 2.5 Freight ratio ─────────────────────────────────────────────────────────
# freight_value / price per item, averaged later at seller level in Phase 3.
#
# Threshold decision (revised from scoping):
#   Original placeholder: 0.3 (flagged 40.5% of sellers -- near the median,
#   not an outlier signal; see 00_scoping.md Metric 6 for full rationale).
#   Revised threshold: 0.40 (empirical p75 of seller-level avg freight ratio).
#   This marks the top 25% of sellers by freight burden -- the operationally
#   meaningful cut for a monitoring tool. The p90 (0.61) is available as a
#   stricter "extreme" flag and will be tested in Phase 4 sensitivity analysis.
FREIGHT_RATIO_THRESHOLD     = 0.40   # p75 -- primary high-freight flag
FREIGHT_RATIO_THRESHOLD_P90 = 0.61   # p90 -- extreme-freight sensitivity flag

fr = df["freight_ratio"].dropna()
fr_valid = fr[np.isfinite(fr)]   # drop any inf (would need price=0, not present)

fig, ax = plt.subplots(figsize=(9, 5))
clip_fr = 2.0
ax.hist(fr_valid.clip(upper=clip_fr), bins=50, color=C_ORANGE, edgecolor="white")
ax.axvline(FREIGHT_RATIO_THRESHOLD, color=C_RED, linestyle="--",
           label=f"High-freight threshold (p75): {FREIGHT_RATIO_THRESHOLD}")
ax.axvline(FREIGHT_RATIO_THRESHOLD_P90, color=C_RED, linestyle=":",
           alpha=0.6, label=f"Extreme-freight threshold (p90): {FREIGHT_RATIO_THRESHOLD_P90}")
ax.axvline(fr_valid.median(), color="black", linestyle=":",
           label=f"Median: {fr_valid.median():.2f}")
ax.set_title(f"Freight ratio per item (clipped at {clip_fr}x)", fontsize=12)
ax.set_xlabel("freight_value / price")
ax.set_ylabel("Number of items")
ax.legend()
plt.tight_layout()
plt.savefig("charts/eda/05_freight_ratio.png", dpi=150)
plt.close()

print("\n[2.5 Freight ratio]")
print(f"  Items in delivered orders: {len(fr_valid):,}")
print(f"  Median: {fr_valid.median():.3f}  Mean: {fr_valid.mean():.3f}  "
      f"p75: {fr_valid.quantile(0.75):.3f}  p90: {fr_valid.quantile(0.90):.3f}")
print(f"  Max: {fr_valid.max():.2f}x  (extreme outlier)")
print(f"  High-freight threshold (p75 / revised): {FREIGHT_RATIO_THRESHOLD} "
      f"-- flags top 25% of sellers")
print(f"  Extreme-freight threshold (p90): {FREIGHT_RATIO_THRESHOLD_P90}")

# ── 2.6 GMV concentration ─────────────────────────────────────────────────────
# Pareto analysis: what share of GMV comes from the top X% of sellers?

df["item_gmv"] = df["price"] + df["freight_value"]
gmv_per_seller = df.groupby("seller_id")["item_gmv"].sum().sort_values(ascending=False)
total_gmv      = gmv_per_seller.sum()
gmv_cumshare   = gmv_per_seller.cumsum() / total_gmv * 100
seller_pctile  = np.arange(1, len(gmv_per_seller) + 1) / len(gmv_per_seller) * 100

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(seller_pctile, gmv_cumshare.values, color=C_BLUE, linewidth=2)
ax.axhline(80, color=C_RED, linestyle="--", alpha=0.7, label="80% GMV")
ax.fill_between(seller_pctile, gmv_cumshare.values, alpha=0.15, color=C_BLUE)
ax.set_title("GMV concentration -- cumulative share by seller percentile", fontsize=12)
ax.set_xlabel("Seller percentile (ranked by GMV, highest first)")
ax.set_ylabel("Cumulative % of total GMV")
ax.legend()
plt.tight_layout()
plt.savefig("charts/eda/06_gmv_concentration.png", dpi=150)
plt.close()

top10_share = gmv_per_seller.iloc[:int(len(gmv_per_seller)*0.10)].sum() / total_gmv * 100
top20_share = gmv_per_seller.iloc[:int(len(gmv_per_seller)*0.20)].sum() / total_gmv * 100
top1_share  = gmv_per_seller.iloc[:int(len(gmv_per_seller)*0.01)].sum() / total_gmv * 100

print("\n[2.6 GMV concentration]")
print(f"  Total GMV (price + freight): R$ {total_gmv:,.0f}")
print(f"  Sellers: {len(gmv_per_seller):,}")
print(f"  Top 1%  of sellers: {top1_share:.1f}% of GMV")
print(f"  Top 10% of sellers: {top10_share:.1f}% of GMV")
print(f"  Top 20% of sellers: {top20_share:.1f}% of GMV")
print(f"  Median seller GMV: R$ {gmv_per_seller.median():,.0f}")

# ── 2.7 Seller order volume distribution ──────────────────────────────────────
# Volume distribution determines how many sellers reach the >=5 order threshold.

seller_vol = df.drop_duplicates("order_id").groupby("seller_id")["order_id"].nunique()

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Left: all sellers, log scale to handle long tail
axes[0].hist(seller_vol, bins=50, color=C_BLUE, edgecolor="white", log=True)
axes[0].axvline(5, color=C_RED, linestyle="--", label="Tier threshold (5 orders)")
axes[0].set_title("Seller order volume distribution (log y-axis)", fontsize=12)
axes[0].set_xlabel("Delivered orders per seller")
axes[0].set_ylabel("Number of sellers (log scale)")
axes[0].legend()

# Right: zoom in on 1-50 range for legibility
axes[1].hist(seller_vol.clip(upper=50), bins=50, color=C_BLUE, edgecolor="white")
axes[1].axvline(5, color=C_RED, linestyle="--", label="Tier threshold (5 orders)")
axes[1].set_title("Seller order volume (clipped at 50 -- shows long tail)", fontsize=12)
axes[1].set_xlabel("Delivered orders per seller (clipped at 50)")
axes[1].set_ylabel("Number of sellers")
axes[1].legend()

plt.tight_layout()
plt.savefig("charts/eda/07_seller_volume.png", dpi=150)
plt.close()

print("\n[2.7 Seller volume]")
print(f"  Sellers in delivered orders: {len(seller_vol):,}")
print(f"  Median orders per seller: {seller_vol.median():.0f}  "
      f"Mean: {seller_vol.mean():.1f}  Max: {seller_vol.max():,}")
print(f"  Sellers with 1 order: {(seller_vol==1).sum():,}")
print(f"  Sellers with >=5 orders (tier-eligible): {(seller_vol>=5).sum():,}")
print(f"  Sellers with >=50 orders: {(seller_vol>=50).sum():,}")

# ── 2.8 Category distribution ─────────────────────────────────────────────────
# Top categories by item count and by avg review score.

cat_counts = (
    df[df["product_category_name_english"].notna()]
    .groupby("product_category_name_english")["order_id"]
    .nunique()
    .sort_values(ascending=False)
)
top15 = cat_counts.head(15)

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(top15.index[::-1], top15.values[::-1], color=C_BLUE, edgecolor="white")
ax.set_title("Top 15 product categories by number of delivered orders", fontsize=12)
ax.set_xlabel("Number of delivered orders")
ax.set_ylabel("")
plt.tight_layout()
plt.savefig("charts/eda/08_top_categories.png", dpi=150)
plt.close()

print("\n[2.8 Category distribution]")
print(f"  Categories with >=1 delivered order: {len(cat_counts)}")
print(f"  Orders with no category (excluded from category analyses): "
      f"{df[df['product_category_name_english'].isna()]['order_id'].nunique():,}")
print(f"  Top 5 by order count:")
for cat, n in top15.head(5).items():
    print(f"    {cat:<40} {n:,}")

# ── 2.9 Geographic distribution of sellers ────────────────────────────────────

seller_state = df.drop_duplicates("seller_id")[["seller_id","seller_state"]]
state_counts = seller_state["seller_state"].value_counts()

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(state_counts.index[::-1], state_counts.values[::-1], color=C_GREEN, edgecolor="white")
ax.set_title("Seller count by state (Sao Paulo dominance expected)", fontsize=12)
ax.set_xlabel("Number of sellers")
ax.set_ylabel("State")
plt.tight_layout()
plt.savefig("charts/eda/09_seller_by_state.png", dpi=150)
plt.close()

sp_share = state_counts["SP"] / state_counts.sum() * 100
print("\n[2.9 Geographic distribution -- sellers]")
print(f"  States with sellers: {len(state_counts)}")
print(f"  SP sellers: {state_counts['SP']:,} ({sp_share:.1f}% of all sellers)")
print(f"  Top 5 states: {state_counts.head(5).to_dict()}")

# ── 2.10 EDA summary ──────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("EDA SUMMARY -- findings and decisions for Phase 3")
print("=" * 70)
print("""
  1. TEMPORAL: Orders grow steadily from late 2016, peak around Nov 2017,
     then flatten through mid-2018. No data quality concerns in the timeline.

  2. REVIEW SCORES: Strongly right-skewed (5s dominate). At seller level
     (>=5 orders), distribution narrows considerably: mean=4.18, std=0.45.
     This compression means tier cutoffs need to be placed carefully --
     small numerical differences carry real signal. Tentative thresholds
     to test in Phase 3: Top >= 4.5, Low <= 3.8 (based on p75 / p25 spread;
     4.5 chosen over the initial 4.3 to produce a more distinctive Top group).
     Confirmed against the on-time delivery rate in Phase 3.

  3. DELIVERY: 91.9% on-time rate. Of the 8.1% late: median delay 5.8 days,
     mean 9.6 days, with a long tail (>60 days: small but present).
     Delivery timeliness is a meaningful differentiator.

  4. DISPATCH SPEED: Median 1.8 days from approval to carrier handoff.
     1,350 negative-dispatch rows (1.4%) are data anomalies -- excluded
     from Metric 7 calculations only, orders kept for all other metrics.

  5. FREIGHT RATIO: Median 0.23, mean 0.32. Original 0.3 threshold flagged
     40.5% of sellers -- near the median, not an outlier signal. Revised to
     p75 = 0.40 (top 25% of sellers). p90 = 0.61 retained for Phase 4
     sensitivity analysis. Both thresholds updated in 00_scoping.md.

  6. GMV CONCENTRATION: Top 10% of sellers = 66.3% of GMV; top 20% = 81.6%.
     Classic long-tail marketplace. Revenue concentration is a key context
     variable for SQ2 -- high-GMV sellers are not necessarily high-scorers.

  7. SELLER VOLUME: Median 7 orders per seller. 1,766 sellers reach the
     >=5 threshold (tier-eligible). 1,204 sellers fall below -- they will
     be kept in item-level analyses but excluded from tier segmentation.

  8. CATEGORIES: 73 categories, bed_bath_table leads by volume. 610 products
     with no category kept in general analyses; excluded only in SQ5/SQ8.

  9. GEOGRAPHY: SP accounts for 60%+ of sellers. Geographic concentration
     is a structural confound for SQ6 -- state-level comparisons will need
     to account for SP's outsized weight.
""")

# ==============================================================================
# Phase 3: Metric calculation
# ==============================================================================
# Produces `seller_metrics`: one row per seller, all 9 metrics from scoping §5.
# Metrics are calculated at the correct granularity:
#   - Order-level (review score, delivery, dispatch): deduped to (order_id, seller_id)
#   - Item-level (freight ratio, GMV): all items kept
# The join base is `df` built in Phase 2.

os.makedirs("charts/metrics", exist_ok=True)

# ── 3.0 Base tables for aggregation ───────────────────────────────────────────
# order_seller: one row per (order, seller) pair -- used for order-level metrics.
# Multi-item orders with items from different sellers produce one row per seller.
# This correctly attributes each order's review and delivery outcome to each
# contributing seller.

order_seller = (
    df[["order_id", "seller_id", "review_score",
        "delay_days", "dispatch_days", "seller_state"]]
    .drop_duplicates(subset=["order_id", "seller_id"])
    .copy()
)

# ── 3.1 Metric 1 -- Average Review Score per Seller ───────────────────────────

m1 = (
    order_seller
    .groupby("seller_id")
    .agg(
        avg_review_score=("review_score", "mean"),
        n_reviewed=("review_score", "count"),   # denominator for confidence
    )
    .reset_index()
)

# ── 3.2 Metric 3 -- Order Volume & Metric 9 -- Negative Review Rate ───────────
# Calculated together since both iterate over order_seller.

m3_m9 = (
    order_seller
    .groupby("seller_id")
    .agg(
        order_volume=("order_id", "nunique"),
        neg_review_count=("review_score", lambda x: (x <= 2).sum()),
    )
    .reset_index()
)
m3_m9["negative_review_rate"] = m3_m9["neg_review_count"] / m3_m9["order_volume"]

# ── 3.3 Metric 4 -- On-Time Delivery Rate & Metric 5 -- Avg Delivery Delay ───

# Exclude rows where delay_days is null (8 orders missing delivery date).
delivery = order_seller[order_seller["delay_days"].notna()].copy()
delivery["is_late"]    = delivery["delay_days"] > 0
delivery["delay_late"] = delivery["delay_days"].where(delivery["delay_days"] > 0)

m4_m5 = (
    delivery
    .groupby("seller_id")
    .agg(
        n_delivery_obs=("delay_days", "count"),
        on_time_count=("is_late", lambda x: (~x).sum()),
        late_count=("is_late", "sum"),
        avg_delay_days=("delay_late", "mean"),   # mean of late-only delays
    )
    .reset_index()
)
m4_m5["on_time_rate"] = m4_m5["on_time_count"] / m4_m5["n_delivery_obs"]

# ── 3.4 Metric 7 -- Dispatch Speed ───────────────────────────────────────────
# Exclude negative dispatch_days rows (data anomaly, see §2.4 comment).

dispatch = order_seller[
    order_seller["dispatch_days"].notna() & (order_seller["dispatch_days"] >= 0)
].copy()

m7 = (
    dispatch
    .groupby("seller_id")
    .agg(avg_dispatch_days=("dispatch_days", "mean"))
    .reset_index()
)

# ── 3.5 Metric 2 -- Seller GMV & Metric 6 -- Freight Ratio ───────────────────
# Item-level aggregation (no deduplication -- each item contributes independently).

df["item_gmv"] = df["price"] + df["freight_value"]

m2_m6 = (
    df
    .groupby("seller_id")
    .agg(
        gmv=("item_gmv", "sum"),
        avg_freight_ratio=("freight_ratio", "mean"),
    )
    .reset_index()
)
m2_m6["high_freight"] = m2_m6["avg_freight_ratio"] > FREIGHT_RATIO_THRESHOLD

# ── 3.6 Seller state (from sellers table -- one state per seller) ─────────────

seller_geo = sellers[["seller_id", "seller_state"]].copy()

# ── 3.7 Assemble seller_metrics ───────────────────────────────────────────────

seller_metrics = (
    m1
    .merge(m3_m9[["seller_id","order_volume","negative_review_rate"]], on="seller_id", how="left")
    .merge(m4_m5[["seller_id","on_time_rate","avg_delay_days","on_time_count","late_count"]], on="seller_id", how="left")
    .merge(m7, on="seller_id", how="left")
    .merge(m2_m6, on="seller_id", how="left")
    .merge(seller_geo, on="seller_id", how="left")
)

print(f"seller_metrics shape: {seller_metrics.shape}  ({len(seller_metrics):,} sellers)")
print(f"Nulls:\n{seller_metrics.isnull().sum()[seller_metrics.isnull().sum()>0]}")

# ── 3.8 Metric 8 -- Performance Tier ─────────────────────────────────────────
# Tier is based on a composite of avg_review_score and on_time_rate.
# Only sellers with >=5 delivered orders are tier-eligible (scoping §5, Metric 1).
#
# Thresholds -- empirically determined from Phase 2 EDA and reviewed against
# the bivariate distribution below:
#   Top:  avg_review_score >= 4.5  AND  on_time_rate >= 0.90
#   Low:  avg_review_score <= 3.8  OR   on_time_rate <  0.80
#   Mid:  everything else
#
# Score Top cutoff set at 4.5 (approx p75 of eligible-seller distribution).
# An initial 4.3 candidate produced a Top group of 34.7% -- too broad for a
# monitoring tool where "top performer" should be a distinctive label.
# 4.5 tightens this to a more exclusive group (see tier summary below).
#
# Rationale for OR vs AND in the Low tier:
#   A seller with a high score but very poor delivery reliability (< 80% on-time)
#   still poses operational risk and warrants attention from the Seller Success
#   team. The OR rule ensures delivery failures surface in Low even when
#   customers have been forgiving in their ratings.
#
# These thresholds are intentionally documented here (scoping §5, Metric 8)
# and will be finalized after reviewing the bivariate chart below.

SCORE_TOP   = 4.5
SCORE_LOW   = 3.8
OTR_TOP     = 0.90   # on-time rate floor for Top tier
OTR_LOW     = 0.80   # on-time rate ceiling for Low tier

eligible = seller_metrics[seller_metrics["order_volume"] >= 5].copy()

def assign_tier(row):
    score = row["avg_review_score"]
    otr   = row["on_time_rate"]
    if pd.isna(score) or pd.isna(otr):
        return "Unclassified"
    if score >= SCORE_TOP and otr >= OTR_TOP:
        return "Top"
    if score <= SCORE_LOW or otr < OTR_LOW:
        return "Low"
    return "Mid"

eligible["tier"] = eligible.apply(assign_tier, axis=1)
seller_metrics = seller_metrics.merge(
    eligible[["seller_id", "tier"]], on="seller_id", how="left"
)
# Sellers below threshold get NaN tier -- clearly flagged in reports.

# ── 3.9 Bivariate: review score vs on-time rate ───────────────────────────────

tier_colors = {"Top": C_GREEN, "Mid": C_BLUE, "Low": C_RED, "Unclassified": "grey"}

fig, ax = plt.subplots(figsize=(10, 7))
for tier_name, grp in eligible.groupby("tier"):
    ax.scatter(grp["on_time_rate"], grp["avg_review_score"],
               alpha=0.4, s=30, label=tier_name, color=tier_colors.get(tier_name, "grey"))
ax.axhline(SCORE_TOP, color=C_GREEN, linestyle="--", linewidth=1, alpha=0.8,
           label=f"Score Top cutoff: {SCORE_TOP}")
ax.axhline(SCORE_LOW, color=C_RED, linestyle="--", linewidth=1, alpha=0.8,
           label=f"Score Low cutoff: {SCORE_LOW}")
ax.axvline(OTR_TOP, color=C_GREEN, linestyle=":", linewidth=1, alpha=0.8,
           label=f"OTR Top floor: {OTR_TOP}")
ax.axvline(OTR_LOW, color=C_RED, linestyle=":", linewidth=1, alpha=0.8,
           label=f"OTR Low ceiling: {OTR_LOW}")
ax.set_title("Seller performance: avg review score vs on-time delivery rate\n"
             "(tier-eligible sellers, n>=5 orders)", fontsize=12)
ax.set_xlabel("On-time delivery rate")
ax.set_ylabel("Average review score (1-5)")
ax.legend(fontsize=9, loc="lower left")
plt.tight_layout()
plt.savefig("charts/metrics/01_bivariate_score_otr.png", dpi=150)
plt.close()

# ── 3.10 Tier summary ─────────────────────────────────────────────────────────

tier_counts = eligible["tier"].value_counts()

print("\n" + "=" * 70)
print("PHASE 3 -- SELLER METRICS SUMMARY")
print("=" * 70)

print(f"\n[Seller metrics table]")
print(f"  Total sellers: {len(seller_metrics):,}")
print(f"  Tier-eligible (>=5 orders): {len(eligible):,}")
print(f"  Below threshold (<5 orders): {len(seller_metrics)-len(eligible):,}")

print(f"\n[Tier distribution]")
tier_gmv = eligible.groupby("tier")["gmv"].sum()
total_gmv_eligible = tier_gmv.sum()
for tier_name in ["Top", "Mid", "Low", "Unclassified"]:
    if tier_name in tier_counts:
        n     = tier_counts[tier_name]
        pct_n = n / len(eligible) * 100
        g     = tier_gmv.get(tier_name, 0)
        pct_g = g / total_gmv_eligible * 100
        print(f"  {tier_name:<15} {n:>5,} sellers ({pct_n:5.1f}%)  |  "
              f"GMV R$ {g:>12,.0f} ({pct_g:5.1f}%)")

print(f"\n[Metric distributions -- eligible sellers]")
for col, label in [
    ("avg_review_score",   "Avg review score"),
    ("on_time_rate",       "On-time delivery rate"),
    ("avg_delay_days",     "Avg delay (late orders, days)"),
    ("avg_dispatch_days",  "Avg dispatch speed (days)"),
    ("avg_freight_ratio",  "Avg freight ratio"),
    ("gmv",                "Seller GMV (R$)"),
    ("order_volume",       "Order volume"),
]:
    s = eligible[col].dropna()
    print(f"  {label:<38} median={s.median():.3f}  "
          f"p25={s.quantile(0.25):.3f}  p75={s.quantile(0.75):.3f}")

print(f"\n[Freight burden]")
pct_high = (eligible["avg_freight_ratio"] > FREIGHT_RATIO_THRESHOLD).mean() * 100
pct_ext  = (eligible["avg_freight_ratio"] > FREIGHT_RATIO_THRESHOLD_P90).mean() * 100
print(f"  Eligible sellers with avg freight ratio > {FREIGHT_RATIO_THRESHOLD} (p75): {pct_high:.1f}%")
print(f"  Eligible sellers with avg freight ratio > {FREIGHT_RATIO_THRESHOLD_P90} (p90): {pct_ext:.1f}%")

print(f"\n[Negative review rate]")
nrr = eligible["negative_review_rate"].dropna()
print(f"  Median: {nrr.median():.3f}  p75: {nrr.quantile(0.75):.3f}  "
      f"p90: {nrr.quantile(0.90):.3f}  max: {nrr.max():.3f}")
high_nrr = (nrr > 0.20).sum()
print(f"  Sellers with >20% negative review rate: {high_nrr} ({high_nrr/len(nrr)*100:.1f}%)")

# ── 3.11 Supporting charts ────────────────────────────────────────────────────

# Review score by tier (box plot)
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

tier_order = ["Top", "Mid", "Low"]
plot_data  = eligible[eligible["tier"].isin(tier_order)]

# Box: review score by tier
tier_score_data = [plot_data[plot_data["tier"]==t]["avg_review_score"].dropna()
                   for t in tier_order]
bp = axes[0].boxplot(tier_score_data, tick_labels=tier_order, patch_artist=True)
for patch, color in zip(bp["boxes"], [C_GREEN, C_BLUE, C_RED]):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
axes[0].set_title("Avg review score by tier", fontsize=11)
axes[0].set_ylabel("Average review score")

# Box: on-time rate by tier
tier_otr_data = [plot_data[plot_data["tier"]==t]["on_time_rate"].dropna()
                 for t in tier_order]
bp2 = axes[1].boxplot(tier_otr_data, tick_labels=tier_order, patch_artist=True)
for patch, color in zip(bp2["boxes"], [C_GREEN, C_BLUE, C_RED]):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
axes[1].set_title("On-time delivery rate by tier", fontsize=11)
axes[1].set_ylabel("On-time rate")

# Box: GMV by tier (log scale)
tier_gmv_data = [plot_data[plot_data["tier"]==t]["gmv"].dropna()
                 for t in tier_order]
bp3 = axes[2].boxplot(tier_gmv_data, tick_labels=tier_order, patch_artist=True)
for patch, color in zip(bp3["boxes"], [C_GREEN, C_BLUE, C_RED]):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
axes[2].set_yscale("log")
axes[2].set_title("Seller GMV by tier (log scale)", fontsize=11)
axes[2].set_ylabel("GMV (R$, log scale)")

plt.suptitle("Performance tier profiles", fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig("charts/metrics/02_tier_profiles.png", dpi=150, bbox_inches="tight")
plt.close()

# Metric distributions: freight ratio and dispatch speed by tier
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

for i, tier_name in enumerate(tier_order):
    grp = plot_data[plot_data["tier"] == tier_name]
    color = [C_GREEN, C_BLUE, C_RED][i]
    axes[0].hist(grp["avg_freight_ratio"].clip(upper=1.5), bins=30,
                 alpha=0.5, color=color, label=tier_name, edgecolor="white")
    axes[1].hist(grp["avg_dispatch_days"].clip(upper=10), bins=30,
                 alpha=0.5, color=color, label=tier_name, edgecolor="white")

axes[0].axvline(FREIGHT_RATIO_THRESHOLD, color="black", linestyle="--",
                label=f"p75 threshold: {FREIGHT_RATIO_THRESHOLD}")
axes[0].set_title("Avg freight ratio by tier (clipped at 1.5)", fontsize=11)
axes[0].set_xlabel("Avg freight ratio")
axes[0].set_ylabel("Number of sellers")
axes[0].legend()

axes[1].set_title("Avg dispatch speed by tier (clipped at 10 days)", fontsize=11)
axes[1].set_xlabel("Avg days (approval -> carrier)")
axes[1].set_ylabel("Number of sellers")
axes[1].legend()

plt.tight_layout()
plt.savefig("charts/metrics/03_freight_dispatch_by_tier.png", dpi=150)
plt.close()

print("\nCharts saved: charts/metrics/01_bivariate_score_otr.png")
print("             charts/metrics/02_tier_profiles.png")
print("             charts/metrics/03_freight_dispatch_by_tier.png")

# ==============================================================================
# Phase 4: Analysis (mapped to SQ1--SQ8)
# ==============================================================================
# Each sub-section maps directly to a sub-question in 00_scoping.md §4.
# Working dataframes:
#   seller_metrics / eligible  -- one row per seller (Phase 3 output)
#   df                         -- one row per order-item (Phase 2 output)
#   order_seller               -- one row per (order, seller) pair (Phase 3)
# Spearman r used throughout (distributions are non-normal).

from scipy import stats

os.makedirs("charts/analysis", exist_ok=True)

# Convenience: eligible sellers with tier assigned (Top/Mid/Low only)
seg = eligible[eligible["tier"].isin(["Top", "Mid", "Low"])].copy()

# ── SQ1: Performance segmentation ─────────────────────────────────────────────
# How is avg review score distributed across sellers?
# Are there natural clusters or is it continuous?

fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(seg["avg_review_score"], bins=50, color=C_BLUE, edgecolor="white")
ax.axvline(SCORE_TOP, color=C_GREEN, linestyle="--", linewidth=1.5,
           label=f"Top cutoff: {SCORE_TOP}")
ax.axvline(SCORE_LOW, color=C_RED, linestyle="--", linewidth=1.5,
           label=f"Low cutoff: {SCORE_LOW}")
for tier_name, color in [("Top", C_GREEN), ("Low", C_RED)]:
    grp = seg[seg["tier"] == tier_name]["avg_review_score"]
    ax.axvspan(grp.min(), grp.max(), alpha=0.07, color=color)
ax.set_title("SQ1: Distribution of avg review score per seller\n"
             "(tier-eligible sellers, n=1,766)", fontsize=12)
ax.set_xlabel("Average review score")
ax.set_ylabel("Number of sellers")
ax.legend()
plt.tight_layout()
plt.savefig("charts/analysis/sq1_score_distribution.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ1 -- Performance segmentation")
print("=" * 70)
print(f"  Distribution is unimodal and left-skewed (no natural clusters).")
print(f"  Tiers reflect deliberate cutoffs, not empirical gaps in the data.")
tier_summary = seg.groupby("tier").agg(
    n=("seller_id", "count"),
    score_median=("avg_review_score", "median"),
    score_p25=("avg_review_score", lambda x: x.quantile(0.25)),
    score_p75=("avg_review_score", lambda x: x.quantile(0.75)),
).loc[["Top","Mid","Low"]]
print(f"\n  {'Tier':<6} {'n':>5}  {'score median':>13}  {'p25':>6}  {'p75':>6}")
for tier_name, row in tier_summary.iterrows():
    print(f"  {tier_name:<6} {int(row['n']):>5}  {row['score_median']:>13.3f}  "
          f"{row['score_p25']:>6.3f}  {row['score_p75']:>6.3f}")

# ── SQ2: Revenue concentration and outcome quality ─────────────────────────────
# Is high GMV associated with better or worse customer outcomes?

gmv_quartile_labels = ["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]
seg["gmv_quartile"] = pd.qcut(seg["gmv"], q=4, labels=gmv_quartile_labels)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Scatter: GMV vs avg review score
for tier_name in ["Top", "Mid", "Low"]:
    grp = seg[seg["tier"] == tier_name]
    axes[0].scatter(grp["gmv"], grp["avg_review_score"],
                    alpha=0.35, s=20, color=tier_colors[tier_name], label=tier_name)
axes[0].set_xscale("log")
axes[0].set_title("SQ2: Seller GMV vs avg review score", fontsize=11)
axes[0].set_xlabel("Seller GMV, R$ (log scale)")
axes[0].set_ylabel("Average review score")
axes[0].legend(fontsize=9)
r_sq2, p_sq2 = stats.spearmanr(seg["gmv"].dropna(), seg["avg_review_score"].dropna())
axes[0].text(0.03, 0.05, f"Spearman r = {r_sq2:.3f}  (p={p_sq2:.3f})",
             transform=axes[0].transAxes, fontsize=9)

# Box: avg review score by GMV quartile
quartile_data = [seg[seg["gmv_quartile"] == q]["avg_review_score"].dropna()
                 for q in gmv_quartile_labels]
bp = axes[1].boxplot(quartile_data, tick_labels=gmv_quartile_labels, patch_artist=True)
for patch in bp["boxes"]:
    patch.set_facecolor(C_BLUE)
    patch.set_alpha(0.5)
axes[1].set_title("SQ2: Avg review score by seller GMV quartile", fontsize=11)
axes[1].set_xlabel("GMV quartile")
axes[1].set_ylabel("Average review score")
axes[1].tick_params(axis="x", rotation=15)
plt.tight_layout()
plt.savefig("charts/analysis/sq2_gmv_vs_score.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ2 -- Revenue concentration and outcome quality")
print("=" * 70)
print(f"  Spearman r (GMV vs avg review score): {r_sq2:.3f}  (p={p_sq2:.4f})")
if abs(r_sq2) < 0.1:
    interpretation = "negligible -- GMV and review score are essentially independent"
elif r_sq2 > 0:
    interpretation = f"weak positive -- higher-GMV sellers trend marginally better"
else:
    interpretation = f"weak negative -- higher-GMV sellers trend marginally worse"
print(f"  Interpretation: {interpretation}")
print(f"  Score by GMV quartile (median):")
for q in gmv_quartile_labels:
    med = seg[seg["gmv_quartile"] == q]["avg_review_score"].median()
    print(f"    {q:<18}: {med:.3f}")

# ── SQ3: Delivery delays -- drivers and downstream effects ────────────────────
# Part A: What is associated with late delivery? (dispatch speed, geography)
# Part B: How strongly does delay reduce review score?

# Part A -- dispatch speed vs on-time rate (seller level)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

valid_disp = seg.dropna(subset=["avg_dispatch_days", "on_time_rate"])
axes[0].scatter(valid_disp["avg_dispatch_days"].clip(upper=8),
                valid_disp["on_time_rate"],
                alpha=0.3, s=20, color=C_BLUE)
r_disp, p_disp = stats.spearmanr(valid_disp["avg_dispatch_days"],
                                  valid_disp["on_time_rate"])
axes[0].set_title("SQ3a: Dispatch speed vs on-time delivery rate", fontsize=11)
axes[0].set_xlabel("Avg dispatch speed (days, clipped at 8)")
axes[0].set_ylabel("On-time delivery rate")
axes[0].text(0.03, 0.05, f"Spearman r = {r_disp:.3f}  (p={p_disp:.4f})",
             transform=axes[0].transAxes, fontsize=9)

# Part B -- order-level: on-time vs late review score comparison
order_outcomes = order_seller.merge(
    df[["order_id","seller_id"]].drop_duplicates(), on=["order_id","seller_id"], how="left"
)[["order_id", "review_score", "delay_days"]].drop_duplicates("order_id")
order_outcomes = order_outcomes.dropna(subset=["delay_days","review_score"])
order_outcomes["delivery_status"] = np.where(
    order_outcomes["delay_days"] <= 0, "On time", "Late"
)

status_means = order_outcomes.groupby("delivery_status")["review_score"].mean()
on_time_scores = order_outcomes[order_outcomes["delivery_status"]=="On time"]["review_score"]
late_scores    = order_outcomes[order_outcomes["delivery_status"]=="Late"]["review_score"]
t_stat, t_p    = stats.mannwhitneyu(on_time_scores, late_scores, alternative="greater")

axes[1].boxplot([on_time_scores, late_scores],
                tick_labels=["On time", "Late"], patch_artist=True,
                boxprops=dict(facecolor=C_BLUE, alpha=0.5))
axes[1].set_title("SQ3b: Review score -- on time vs late delivery", fontsize=11)
axes[1].set_ylabel("Review score (1-5)")
axes[1].text(0.03, 0.05,
             f"On time mean: {status_means['On time']:.2f}\n"
             f"Late mean:    {status_means['Late']:.2f}\n"
             f"Mann-Whitney p < 0.001",
             transform=axes[1].transAxes, fontsize=9)
plt.tight_layout()
plt.savefig("charts/analysis/sq3_delivery_vs_score.png", dpi=150)
plt.close()

# Part A supplement -- on-time rate by seller state (top 10 states by seller count)
top_states = seg["seller_state"].value_counts().head(10).index
state_otr  = (seg[seg["seller_state"].isin(top_states)]
              .groupby("seller_state")["on_time_rate"].median()
              .sort_values())

fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(state_otr.index, state_otr.values, color=C_BLUE, edgecolor="white")
ax.axvline(seg["on_time_rate"].median(), color=C_RED, linestyle="--",
           label=f"Overall median: {seg['on_time_rate'].median():.3f}")
ax.set_title("SQ3a: Median on-time delivery rate by seller state\n"
             "(top 10 states by seller count)", fontsize=11)
ax.set_xlabel("Median on-time delivery rate")
ax.legend()
plt.tight_layout()
plt.savefig("charts/analysis/sq3a_ontime_by_state.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ3 -- Delivery delays: drivers and downstream effects")
print("=" * 70)
print(f"  [Part A -- dispatch speed as driver]")
print(f"  Spearman r (dispatch days vs on-time rate): {r_disp:.3f}  (p={p_disp:.4f})")
print(f"  Top 10 states by seller count -- on-time rate range: "
      f"{state_otr.min():.3f} to {state_otr.max():.3f}")
print(f"  Worst state: {state_otr.idxmin()} ({state_otr.min():.3f})  "
      f"Best: {state_otr.idxmax()} ({state_otr.max():.3f})")
print(f"\n  [Part B -- late delivery -> lower review score]")
print(f"  On-time orders -- mean score:  {status_means['On time']:.3f}  "
      f"(n={len(on_time_scores):,})")
print(f"  Late orders    -- mean score:  {status_means['Late']:.3f}  "
      f"(n={len(late_scores):,})")
print(f"  Score drop for late delivery:  "
      f"{status_means['On time']-status_means['Late']:.3f} points")
print(f"  Mann-Whitney U (one-sided):    p = {t_p:.2e}  (highly significant)")

# ── SQ4: Freight cost as a performance lever ──────────────────────────────────
# Is high freight ratio associated with lower review scores?

fig, ax = plt.subplots(figsize=(9, 5))
valid_fr = seg.dropna(subset=["avg_freight_ratio","avg_review_score"])
ax.scatter(valid_fr["avg_freight_ratio"].clip(upper=1.2),
           valid_fr["avg_review_score"],
           alpha=0.3, s=20, color=C_ORANGE)
ax.axvline(FREIGHT_RATIO_THRESHOLD, color=C_RED, linestyle="--",
           label=f"High-freight threshold: {FREIGHT_RATIO_THRESHOLD}")
r_fr, p_fr = stats.spearmanr(valid_fr["avg_freight_ratio"],
                               valid_fr["avg_review_score"])
ax.set_title("SQ4: Avg freight ratio vs avg review score (seller level)", fontsize=12)
ax.set_xlabel("Avg freight ratio (clipped at 1.2)")
ax.set_ylabel("Average review score")
ax.text(0.03, 0.05, f"Spearman r = {r_fr:.3f}  (p={p_fr:.4f})",
        transform=ax.transAxes, fontsize=9)
ax.legend()
plt.tight_layout()
plt.savefig("charts/analysis/sq4_freight_vs_score.png", dpi=150)
plt.close()

high_fr_score  = seg[seg["avg_freight_ratio"] >  FREIGHT_RATIO_THRESHOLD]["avg_review_score"].median()
low_fr_score   = seg[seg["avg_freight_ratio"] <= FREIGHT_RATIO_THRESHOLD]["avg_review_score"].median()
print("\n" + "=" * 70)
print("SQ4 -- Freight cost as a performance lever")
print("=" * 70)
print(f"  Spearman r (freight ratio vs review score): {r_fr:.3f}  (p={p_fr:.4f})")
print(f"  Median review score -- high freight (>{FREIGHT_RATIO_THRESHOLD}): {high_fr_score:.3f}")
print(f"  Median review score -- normal freight:                            {low_fr_score:.3f}")
print(f"  Score gap: {low_fr_score - high_fr_score:.3f} points")

# ── SQ5: Product categories prone to negative outcomes ────────────────────────
# Which categories have systematically low scores, high late rates, high freight?
# Uses df (item-level) joined to order-level outcomes. Category nulls excluded.

cat_base = (
    df[df["product_category_name_english"].notna()]
    .drop_duplicates(subset=["order_id", "product_category_name_english"])
    [["order_id", "product_category_name_english", "review_score",
      "delay_days", "freight_ratio"]]
    .copy()
)
cat_base["is_late"] = cat_base["delay_days"] > 0

cat_agg = (
    cat_base
    .groupby("product_category_name_english")
    .agg(
        n_orders=("order_id", "nunique"),
        avg_score=("review_score", "mean"),
        late_rate=("is_late", "mean"),
        avg_freight_ratio=("freight_ratio", "mean"),
    )
    .reset_index()
    .query("n_orders >= 50")   # min 50 orders for stable estimates
    .sort_values("avg_score")
)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Worst 15 and best 15 by avg score
worst15 = cat_agg.head(15)
best15  = cat_agg.tail(15).sort_values("avg_score", ascending=False)

axes[0].barh(worst15["product_category_name_english"],
             worst15["avg_score"], color=C_RED, edgecolor="white")
axes[0].set_title("SQ5: 15 lowest-rated categories (min 50 orders)", fontsize=11)
axes[0].set_xlabel("Average review score")
axes[0].set_xlim(1, 5)

axes[1].barh(best15["product_category_name_english"],
             best15["avg_score"], color=C_GREEN, edgecolor="white")
axes[1].set_title("SQ5: 15 highest-rated categories (min 50 orders)", fontsize=11)
axes[1].set_xlabel("Average review score")
axes[1].set_xlim(1, 5)

plt.tight_layout()
plt.savefig("charts/analysis/sq5_category_outcomes.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ5 -- Product categories prone to negative outcomes")
print("=" * 70)
print(f"  Categories with >=50 orders: {len(cat_agg)}")
print(f"\n  Bottom 5 by avg review score:")
for _, row in cat_agg.head(5).iterrows():
    print(f"    {row['product_category_name_english']:<45} "
          f"score={row['avg_score']:.3f}  late={row['late_rate']*100:.1f}%  "
          f"n={int(row['n_orders']):,}")
print(f"\n  Top 5 by avg review score:")
for _, row in cat_agg.tail(5).sort_values("avg_score", ascending=False).iterrows():
    print(f"    {row['product_category_name_english']:<45} "
          f"score={row['avg_score']:.3f}  late={row['late_rate']*100:.1f}%  "
          f"n={int(row['n_orders']):,}")
print(f"\n  Highest late-delivery rate categories:")
for _, row in cat_agg.nlargest(5, "late_rate").iterrows():
    print(f"    {row['product_category_name_english']:<45} "
          f"late={row['late_rate']*100:.1f}%  score={row['avg_score']:.3f}")

# ── SQ6: Geographic structural disadvantage ───────────────────────────────────
# Do sellers in certain states face systematically worse delivery or higher freight?

state_agg = (
    seg.groupby("seller_state")
    .agg(
        n_sellers=("seller_id", "count"),
        median_score=("avg_review_score", "median"),
        median_otr=("on_time_rate", "median"),
        median_freight=("avg_freight_ratio", "median"),
        median_dispatch=("avg_dispatch_days", "median"),
    )
    .query("n_sellers >= 5")
    .reset_index()
    .sort_values("median_otr")
)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# On-time rate by state
axes[0].barh(state_agg["seller_state"], state_agg["median_otr"],
             color=C_BLUE, edgecolor="white")
axes[0].axvline(seg["on_time_rate"].median(), color=C_RED, linestyle="--",
                label=f"Overall median: {seg['on_time_rate'].median():.3f}")
axes[0].set_title("SQ6: Median on-time rate by seller state\n"
                  "(states with >=5 eligible sellers)", fontsize=11)
axes[0].set_xlabel("Median on-time delivery rate")
axes[0].legend(fontsize=8)

# Avg review score by state (sorted same order as OTR for comparison)
score_by_state = state_agg.set_index("seller_state")["median_score"]
axes[1].barh(state_agg["seller_state"], score_by_state.values,
             color=C_GREEN, edgecolor="white")
axes[1].axvline(seg["avg_review_score"].median(), color=C_RED, linestyle="--",
                label=f"Overall median: {seg['avg_review_score'].median():.3f}")
axes[1].set_title("SQ6: Median avg review score by seller state\n"
                  "(same sort order as on-time rate)", fontsize=11)
axes[1].set_xlabel("Median avg review score")
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig("charts/analysis/sq6_geography.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ6 -- Geographic structural disadvantage")
print("=" * 70)
print(f"  States with >=5 eligible sellers: {len(state_agg)}")
print(f"\n  Worst 5 states by median on-time rate:")
for _, row in state_agg.head(5).iterrows():
    print(f"    {row['seller_state']}  OTR={row['median_otr']:.3f}  "
          f"score={row['median_score']:.3f}  n={int(row['n_sellers'])}")
print(f"\n  Best 5 states by median on-time rate:")
for _, row in state_agg.tail(5).sort_values("median_otr", ascending=False).iterrows():
    print(f"    {row['seller_state']}  OTR={row['median_otr']:.3f}  "
          f"score={row['median_score']:.3f}  n={int(row['n_sellers'])}")
r_geo, p_geo = stats.spearmanr(state_agg["median_otr"], state_agg["median_score"])
print(f"\n  Spearman r (state OTR vs state score): {r_geo:.3f}  (p={p_geo:.4f})")

# ── SQ7: Volume versus consistency ────────────────────────────────────────────
# Do high-volume sellers maintain review score as volume increases?

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Scatter: order volume vs avg review score
for tier_name in ["Top", "Mid", "Low"]:
    grp = seg[seg["tier"] == tier_name]
    axes[0].scatter(grp["order_volume"], grp["avg_review_score"],
                    alpha=0.3, s=20, color=tier_colors[tier_name], label=tier_name)
axes[0].set_xscale("log")
r_vol, p_vol = stats.spearmanr(seg["order_volume"], seg["avg_review_score"])
axes[0].set_title("SQ7: Order volume vs avg review score", fontsize=11)
axes[0].set_xlabel("Delivered orders per seller (log scale)")
axes[0].set_ylabel("Average review score")
axes[0].text(0.03, 0.05, f"Spearman r = {r_vol:.3f}  (p={p_vol:.4f})",
             transform=axes[0].transAxes, fontsize=9)
axes[0].legend(fontsize=9)

# Score consistency (std dev) by volume quartile
seg["vol_quartile"] = pd.qcut(seg["order_volume"], q=4,
                               labels=["Q1 low", "Q2", "Q3", "Q4 high"])
vol_consistency = seg.groupby("vol_quartile", observed=True).agg(
    score_std=("avg_review_score", "std"),
    score_median=("avg_review_score", "median"),
    n=("seller_id", "count"),
).reset_index()

x = np.arange(len(vol_consistency))
axes[1].bar(x, vol_consistency["score_std"], color=C_BLUE, edgecolor="white")
axes[1].set_xticks(x)
axes[1].set_xticklabels(vol_consistency["vol_quartile"])
axes[1].set_title("SQ7: Score std dev by volume quartile\n"
                  "(lower = more consistent)", fontsize=11)
axes[1].set_xlabel("Volume quartile")
axes[1].set_ylabel("Std dev of avg review score")
plt.tight_layout()
plt.savefig("charts/analysis/sq7_volume_consistency.png", dpi=150)
plt.close()

print("\n" + "=" * 70)
print("SQ7 -- Volume versus consistency")
print("=" * 70)
print(f"  Spearman r (order volume vs avg review score): {r_vol:.3f}  (p={p_vol:.4f})")
print(f"  Score std dev by volume quartile:")
for _, row in vol_consistency.iterrows():
    print(f"    {str(row['vol_quartile']):<10}  std={row['score_std']:.3f}  "
          f"median score={row['score_median']:.3f}  n={int(row['n'])}")

# ── SQ8: Top performer profile ─────────────────────────────────────────────────
# What combination of operational characteristics describes Top vs Low sellers?

profile_metrics = [
    ("avg_review_score",  "Avg review score"),
    ("on_time_rate",      "On-time rate"),
    ("avg_dispatch_days", "Avg dispatch (days)"),
    ("avg_freight_ratio", "Avg freight ratio"),
    ("negative_review_rate", "Negative review rate"),
    ("order_volume",      "Order volume"),
    ("gmv",               "GMV (R$)"),
]

top_grp = seg[seg["tier"] == "Top"]
low_grp = seg[seg["tier"] == "Low"]

print("\n" + "=" * 70)
print("SQ8 -- Top performer profile")
print("=" * 70)
print(f"\n  {'Metric':<30}  {'Top median':>12}  {'Low median':>12}  {'Ratio T/L':>10}")
print(f"  {'-'*30}  {'-'*12}  {'-'*12}  {'-'*10}")
profile_rows = []
for col, label in profile_metrics:
    t_med = top_grp[col].median()
    l_med = low_grp[col].median()
    ratio = t_med / l_med if l_med != 0 else float("nan")
    print(f"  {label:<30}  {t_med:>12.3f}  {l_med:>12.3f}  {ratio:>10.2f}x")
    profile_rows.append((label, t_med, l_med))

# Radar / grouped bar chart comparing Top vs Low profiles (normalized 0-1)
labels_p  = [r[0] for r in profile_rows]
top_vals  = np.array([r[1] for r in profile_rows], dtype=float)
low_vals  = np.array([r[2] for r in profile_rows], dtype=float)

# Normalize each metric 0-1 across the two values for visual comparison.
# For dispatch, freight, negative_review_rate: lower is better -- invert.
invert_idx = {2, 3, 4}   # dispatch, freight, neg review rate indices
norm_top = np.zeros(len(top_vals))
norm_low = np.zeros(len(low_vals))
combined  = np.column_stack([top_vals, low_vals])
for i in range(len(top_vals)):
    mn, mx = combined[i].min(), combined[i].max()
    if mx == mn:
        norm_top[i] = norm_low[i] = 0.5
        continue
    norm_top[i] = (top_vals[i] - mn) / (mx - mn)
    norm_low[i] = (low_vals[i] - mn) / (mx - mn)
    if i in invert_idx:   # invert: lower raw value = better = higher bar
        norm_top[i] = 1 - norm_top[i]
        norm_low[i] = 1 - norm_low[i]

x      = np.arange(len(labels_p))
width  = 0.35
fig, ax = plt.subplots(figsize=(13, 5))
ax.bar(x - width/2, norm_top, width, label="Top", color=C_GREEN, alpha=0.75, edgecolor="white")
ax.bar(x + width/2, norm_low, width, label="Low", color=C_RED,   alpha=0.75, edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(labels_p, rotation=25, ha="right", fontsize=9)
ax.set_title("SQ8: Top vs Low seller profile\n"
             "(all metrics normalized 0-1; higher = better for each metric)", fontsize=12)
ax.set_ylabel("Normalized score (higher = better)")
ax.legend()
plt.tight_layout()
plt.savefig("charts/analysis/sq8_top_vs_low_profile.png", dpi=150)
plt.close()

# Top performers by category -- are certain categories over-represented in Top tier?
df_tier = df.merge(seg[["seller_id","tier"]], on="seller_id", how="inner")
df_tier = df_tier[df_tier["product_category_name_english"].notna()]
cat_tier_share = (
    df_tier.groupby(["product_category_name_english","tier"])
    .agg(n_orders=("order_id","nunique"))
    .reset_index()
    .pivot(index="product_category_name_english", columns="tier", values="n_orders")
    .fillna(0)
)
cat_tier_share["total"] = cat_tier_share.sum(axis=1)
for t in ["Top","Mid","Low"]:
    if t in cat_tier_share.columns:
        cat_tier_share[f"pct_{t.lower()}"] = cat_tier_share[t] / cat_tier_share["total"]
top_heavy_cats = (cat_tier_share[cat_tier_share["total"]>=100]
                  .sort_values("pct_top", ascending=False)
                  .head(10))
print(f"\n  Top 10 categories most concentrated in Top-tier sellers (min 100 orders):")
print(f"  {'Category':<45} {'% Top':>8}  {'% Low':>8}  {'n orders':>9}")
for cat, row in top_heavy_cats.iterrows():
    print(f"  {cat:<45} {row.get('pct_top',0)*100:>7.1f}%  "
          f"{row.get('pct_low',0)*100:>7.1f}%  {int(row['total']):>9,}")

print(f"\n  Key differentiators (Top vs Low):")
print(f"    - Dispatch speed: Top sellers dispatch {low_grp['avg_dispatch_days'].median()-top_grp['avg_dispatch_days'].median():.1f} days faster")
print(f"    - On-time rate:   Top {top_grp['on_time_rate'].median()*100:.1f}% vs Low {low_grp['on_time_rate'].median()*100:.1f}%")
print(f"    - Neg review rate: Top {top_grp['negative_review_rate'].median()*100:.1f}% vs Low {low_grp['negative_review_rate'].median()*100:.1f}%")
print(f"    - Freight ratio:  Top {top_grp['avg_freight_ratio'].median():.3f} vs Low {low_grp['avg_freight_ratio'].median():.3f}")

print("\nPhase 4 charts saved to charts/analysis/")

# ==============================================================================
# Phase 5: Export
# ==============================================================================
# Produces four CSV files consumed by the Tableau dashboard:
#
#   export/seller_metrics.csv   -- one row per seller (all 9 metrics + tier)
#   export/category_metrics.csv -- one row per category (SQ5 source)
#   export/state_metrics.csv    -- one row per state  (SQ6 source)
#   export/orders_tableau.csv   -- one row per order-item (drill-down layer)
#
# All files use UTF-8 encoding with a BOM (utf-8-sig) so Excel/Tableau open
# accented characters correctly without manual encoding selection.

os.makedirs("export", exist_ok=True)

# ── 5.1 Seller display names (Game of Thrones characters) ─────────────────────
# Seller identities are anonymized hashes. Assigning readable GoT names makes
# the dashboard scannable. Names are assigned deterministically by GMV rank
# (highest GMV = most recognizable character). Sellers beyond the list length
# get a name with a numeric suffix for uniqueness.

GOT_NAMES = [
    "Jon Snow", "Daenerys Targaryen", "Tyrion Lannister", "Cersei Lannister",
    "Jaime Lannister", "Sansa Stark", "Arya Stark", "Bran Stark",
    "Ned Stark", "Catelyn Stark", "Robb Stark", "Theon Greyjoy",
    "Jorah Mormont", "Brienne of Tarth", "Sandor Clegane", "Gregor Clegane",
    "Petyr Baelish", "Varys", "Samwell Tarly", "Olenna Tyrell",
    "Margaery Tyrell", "Loras Tyrell", "Stannis Baratheon", "Melisandre",
    "Davos Seaworth", "Shireen Baratheon", "Robert Baratheon", "Joffrey Baratheon",
    "Tommen Baratheon", "Myrcella Baratheon", "Oberyn Martell", "Ellaria Sand",
    "Doran Martell", "Tormund Giantsbane", "Ygritte", "Mance Rayder",
    "Eddison Tollett", "Jeor Mormont", "Lyanna Mormont", "Qyburn",
    "Pycelle", "Kevan Lannister", "Tywin Lannister", "Gendry",
    "Hot Pie", "Podrick Payne", "Bronn", "Missandei",
    "Grey Worm", "Daario Naharis", "Hizdahr zo Loraq", "Jaqen Hghar",
    "The Waif", "Three-Eyed Raven", "Meera Reed", "Jojen Reed",
    "Roose Bolton", "Ramsay Bolton", "Walder Frey", "Benjen Stark",
    "Lyanna Stark", "Rhaegar Targaryen", "Viserys Targaryen", "Drogo",
    "Irri", "Doreah", "Xaro Xhoan Daxos", "Pyat Pree",
    "Quaithe", "Euron Greyjoy", "Yara Greyjoy", "Balon Greyjoy",
    "Rodrik Cassel", "Maester Luwin", "Hodor", "Osha",
    "Rickon Stark", "Shae", "Ros", "Talisa Stark",
    "Edmure Tully", "Brynden Tully", "Lysa Arryn", "Robin Arryn",
    "Ilyn Payne", "Meryn Trant", "Beric Dondarrion", "Thoros of Myr",
    "Lady Stoneheart", "Coldhands", "Night King", "Wun Wun",
    "Styr", "Karl Tanner", "Locke", "Rast",
    "Craster", "Gilly", "Sam Tarly Sr", "Randyll Tarly",
]

# Assign: sort all sellers by GMV desc, map sequentially through the name list.
sellers_ranked = (
    seller_metrics[["seller_id", "gmv"]]
    .sort_values("gmv", ascending=False, na_position="last")
    .reset_index(drop=True)
)
name_list = []
name_counts = {}
for i in range(len(sellers_ranked)):
    base = GOT_NAMES[i % len(GOT_NAMES)]
    count = name_counts.get(base, 0)
    name_counts[base] = count + 1
    name_list.append(base if count == 0 else f"{base} {count+1}")

sellers_ranked["seller_name"] = name_list
name_map = sellers_ranked.set_index("seller_id")["seller_name"]

# ── 5.2 seller_metrics.csv ────────────────────────────────────────────────────

export_sellers = seller_metrics.copy()
export_sellers["seller_name"] = export_sellers["seller_id"].map(name_map)

# Round floats to 4 decimal places for clean CSVs
float_cols = ["avg_review_score", "negative_review_rate", "on_time_rate",
              "avg_delay_days", "avg_dispatch_days", "avg_freight_ratio",
              "gmv"]
for col in float_cols:
    if col in export_sellers.columns:
        export_sellers[col] = export_sellers[col].round(4)

# Column order: identity first, then outcome metrics, then operational, then context
col_order = [
    "seller_id", "seller_name", "seller_state", "tier",
    "order_volume", "n_reviewed",
    "avg_review_score", "negative_review_rate",
    "on_time_rate", "on_time_count", "late_count", "avg_delay_days",
    "avg_dispatch_days",
    "gmv", "avg_freight_ratio", "high_freight",
]
export_sellers = export_sellers[[c for c in col_order if c in export_sellers.columns]]
export_sellers.to_csv("export/seller_metrics.csv", index=False, encoding="utf-8-sig")

print("=" * 70)
print("PHASE 5 -- EXPORT")
print("=" * 70)
print(f"\n[seller_metrics.csv]")
print(f"  Rows: {len(export_sellers):,}  |  Columns: {list(export_sellers.columns)}")
print(f"  Tier breakdown: "
      f"Top={export_sellers['tier'].eq('Top').sum()}  "
      f"Mid={export_sellers['tier'].eq('Mid').sum()}  "
      f"Low={export_sellers['tier'].eq('Low').sum()}  "
      f"null={export_sellers['tier'].isna().sum()}")

# ── 5.3 category_metrics.csv ──────────────────────────────────────────────────
# Re-derive from df to keep Phase 5 self-contained.

cat_export = (
    df[df["product_category_name_english"].notna()]
    .drop_duplicates(subset=["order_id", "product_category_name_english"])
    .assign(is_late=lambda d: d["delay_days"] > 0)
    .groupby("product_category_name_english")
    .agg(
        n_orders=("order_id",        "nunique"),
        avg_review_score=("review_score",    "mean"),
        late_rate=("is_late",        "mean"),
        avg_freight_ratio=("freight_ratio",  "mean"),
    )
    .reset_index()
    .sort_values("avg_review_score")
    .round(4)
)
cat_export.to_csv("export/category_metrics.csv", index=False, encoding="utf-8-sig")
print(f"\n[category_metrics.csv]")
print(f"  Rows: {len(cat_export):,}  |  Columns: {list(cat_export.columns)}")

# ── 5.4 state_metrics.csv ─────────────────────────────────────────────────────
# State-level seller aggregates for geographic views in Tableau.

state_export = (
    seller_metrics
    .groupby("seller_state")
    .agg(
        n_sellers_total=("seller_id",         "count"),
        n_sellers_eligible=("tier",            lambda x: x.notna().sum()),
        n_top=("tier",                         lambda x: (x == "Top").sum()),
        n_mid=("tier",                         lambda x: (x == "Mid").sum()),
        n_low=("tier",                         lambda x: (x == "Low").sum()),
        median_review_score=("avg_review_score", "median"),
        median_on_time_rate=("on_time_rate",    "median"),
        median_freight_ratio=("avg_freight_ratio","median"),
        median_dispatch_days=("avg_dispatch_days","median"),
        total_gmv=("gmv",                      "sum"),
    )
    .reset_index()
    .round(4)
)
state_export["pct_top"] = (state_export["n_top"] /
                            state_export["n_sellers_eligible"].replace(0, np.nan)).round(4)
state_export.to_csv("export/state_metrics.csv", index=False, encoding="utf-8-sig")
print(f"\n[state_metrics.csv]")
print(f"  Rows: {len(state_export):,}  |  Columns: {list(state_export.columns)}")

# ── 5.5 orders_tableau.csv ────────────────────────────────────────────────────
# Granular order-item table for drill-down views. One row per (order, item).
# Includes tier and seller_name for easy filtering.

orders_export = (
    df[[
        "order_id", "seller_id", "product_id",
        "product_category_name_english",
        "order_purchase_timestamp",
        "seller_state", "customer_state",
        "price", "freight_value", "freight_ratio",
        "review_score", "delay_days", "dispatch_days",
    ]]
    .copy()
    .merge(export_sellers[["seller_id","seller_name","tier"]], on="seller_id", how="left")
)
orders_export["is_late"]     = (orders_export["delay_days"] > 0).astype(int)
orders_export["order_month"] = orders_export["order_purchase_timestamp"].dt.to_period("M").astype(str)
orders_export["high_freight"] = (orders_export["freight_ratio"] > FREIGHT_RATIO_THRESHOLD).astype(int)

# Drop raw timestamp (Tableau gets year_month instead; timestamp kept in orders if needed)
orders_export = orders_export.drop(columns=["order_purchase_timestamp"])

# Round floats
for col in ["price","freight_value","freight_ratio","delay_days","dispatch_days"]:
    orders_export[col] = orders_export[col].round(4)

orders_export.to_csv("export/orders_tableau.csv", index=False, encoding="utf-8-sig")
print(f"\n[orders_tableau.csv]")
print(f"  Rows: {len(orders_export):,}  |  Columns: {list(orders_export.columns)}")

# ── 5.6 Export summary ────────────────────────────────────────────────────────

import os as _os
print(f"\n[File sizes]")
for fname in ["seller_metrics.csv","category_metrics.csv",
              "state_metrics.csv","orders_tableau.csv"]:
    size_kb = _os.path.getsize(f"export/{fname}") / 1024
    print(f"  export/{fname:<30} {size_kb:>7.1f} KB")

print(f"\n[Data integrity checks]")
# All sellers in orders_tableau have a tier or are <5-order sellers
missing_tier = orders_export["tier"].isna().sum()
print(f"  orders_tableau rows with null tier (seller <5 orders): {missing_tier:,}")
# seller_metrics rows == original seller count
print(f"  seller_metrics row count matches source: "
      f"{len(export_sellers) == len(seller_metrics)}")
# Category export covers all categories that had orders
print(f"  category_metrics covers {len(cat_export)} of {df['product_category_name_english'].nunique()} categories with orders")

print("\nAll exports written to export/")
print("Ready for Tableau Public connection.")
