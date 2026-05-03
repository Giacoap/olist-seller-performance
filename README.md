# Olist Seller Performance Monitor

A data analysis project examining what differentiates high-performing sellers from underperformers on Olist, Brazil's largest marketplace intermediary. Built as an operational monitoring tool for the Seller Success team, the analysis covers nearly 100,000 orders across 3,000 sellers and identifies dispatch speed as the dominant driver of customer satisfaction — a finding with direct implications for seller coaching and onboarding.

## Dataset

**Source:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — Kaggle  
**Scale:** 99,441 orders · 3,095 sellers · 71 product categories  
**Period:** September 2016 – October 2018  
**Tables used:** orders, order items, payments, reviews, sellers, products, customers, geolocation, product category translations

Seller identities are anonymized using Game of Thrones character names. The dataset is not included in this repository — download it from Kaggle and place the CSV files in `data/` before running the analysis.

## Tools

- **Python** — pandas, numpy, matplotlib, seaborn
- **Tableau Public** — operational monitoring dashboard
- **Git** — version control

## Files

olist-seller-performance/
├── 00_scoping.md        — Business question, sub-questions, and metric definitions
├── 01_analysis.py       — Main analysis script (load → EDA → metrics → analysis → export)
├── 02_writeup.md        — Narrative case study (context → findings → recommendations)
├── convert_decimal.py   — Utility script: converts CSV decimal separators for AR locale Tableau
├── data/                — Raw CSVs from Kaggle (not tracked by git)
├── export/              — Metric tables exported for Tableau (seller, category, state, orders)
├── charts/              — Exploratory and analytical charts produced by the analysis script
└── viz/                 — Final visualizations

## Dashboard

**[Olist Seller Performance Monitor — Tableau Public](https://public.tableau.com/app/profile/giacomo.apicella/viz/OlistSellerPerformanceMonitor/olist_seller_performance_dashboard)**

An interactive monitoring tool for the Seller Success team. Filter by tier, state, or category to prioritize interventions. Click any seller to see their full performance profile. Click any state in the geographic chart to filter the seller table.

## Reproducibility

**Requirements:** Python 3.8+, pandas, numpy, matplotlib, seaborn

```bash
# Clone the repository
git clone https://github.com/Giacoap/olist-seller-performance.git
cd olist-seller-performance

# Install dependencies
pip install pandas numpy matplotlib seaborn

# Download the dataset from Kaggle and place CSVs in data/
# https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

# Run the analysis
python 01_analysis.py
```

The script produces charts in `charts/` and metric exports in `export/`. If using Tableau with an Argentine locale (comma as decimal separator), run `convert_decimal.py` after the analysis script before connecting Tableau to the exports.

## Key findings

- **Dispatch speed is the dominant driver.** Top-tier sellers dispatch in a median of 1.74 days vs. 3.42 days for Low-tier sellers. That gap cascades into a 1.73-point difference in average review score between on-time and late deliveries (4.30 vs. 2.57, Mann-Whitney p ≈ 0).

- **Revenue and quality are essentially independent.** The second-largest seller by GMV (R$ 237K) sits in the Low tier with a 25% negative review rate. GMV and review score correlate at Spearman r = −0.152 — weak enough that revenue cannot serve as a proxy for quality.

- **Freight cost is not a meaningful lever.** Spearman r = −0.047 between freight ratio and review score. The median score gap between high-freight and normal-freight sellers is 0.058 points — practically negligible.

- **Geography is a weak signal.** State-level on-time rates differ by less than 4 percentage points across the platform. Geographic location does not meaningfully explain seller performance differences.

- **Volume predicts consistency, not quality.** Score standard deviation halves from Q1 to Q4 volume quartile (0.611 → 0.295). High-volume sellers are predictable; low-volume sellers are variable.

- **Category problems split into two types.** Categories like audio have poor scores *and* high late-delivery rates (operational problem). Categories like men's fashion clothing have poor scores *with* low late-delivery rates (structural/product problem). Each requires a different intervention.

Full narrative, methodology, and recommendations: [02_writeup.md](02_writeup.md)

## Author

Giacomo Apicella · [github.com/Giacoap](https://github.com/Giacoap) · [giacoap.github.io](https://giacoap.github.io)