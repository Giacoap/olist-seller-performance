# Olist Seller Performance Analysis — Scoping Document

## 1. Business Context

Olist is a Brazilian marketplace intermediary that connects small and medium-sized sellers to major e-commerce channels under a single contract. Rather than managing their own storefronts across multiple platforms, sellers list through Olist and fulfill orders directly to customers using Olist's logistics network. This model reduces friction for sellers but places them at the center of the customer experience: once an order is placed, the seller is responsible for packing, dispatching, and meeting delivery deadlines.

Sellers are the core operational unit of the Olist marketplace. The platform's reputation, customer retention, and gross merchandise volume all depend on how consistently sellers perform. A seller who ships late, misprices freight, or delivers a product that doesn't match its listing degrades the customer experience — and that degradation is visible at the marketplace level, not just the individual transaction level.

The primary feedback mechanism available to Olist is the post-purchase satisfaction survey. After receiving an order — or after the estimated delivery date passes — customers are invited to rate their experience on a 1–5 scale and leave an optional written comment. This review signal is the most direct and systematic measurement of seller-level customer outcomes available in the dataset.

Freight cost adds a layer of complexity. In Brazil, shipping is expensive relative to product price — logistically, the country's size and infrastructure create wide regional disparities in delivery cost and speed. Freight is often passed on to the buyer, which means it directly affects perceived value. A seller offering a competitive product at a fair price can still generate dissatisfaction if freight cost feels disproportionate — or conversely, absorbing freight cost may be a competitive lever that top performers use intentionally.

There is also a structural information asymmetry in this system. Individual sellers see their own orders, their own reviews, and their own delivery outcomes. Olist, however, sees the full picture: which categories generate the most complaints, which geographies drive freight-related dissatisfaction, which sellers consistently overperform or underperform relative to their peers. This analysis is an exercise in making that systemic view explicit and actionable.

## 2. Stakeholder & Decision

The primary stakeholder for this analysis is Olist's **Seller Success team** — the internal function responsible for onboarding new sellers, monitoring their performance over time, and deciding when and how to intervene. This team operates at the intersection of commercial growth and quality control: they want more sellers generating more GMV, but not at the cost of customer satisfaction scores that affect the marketplace's reputation.

This analysis is designed as an **operational monitoring tool**, not a one-time report. The goal is to give the Seller Success team a continuously usable instrument for three types of decisions:

**Primary decision — intervention prioritization.** Which sellers need active support right now? Which are at risk of becoming a reputational liability? The tool should make it immediately visible which sellers are underperforming across key dimensions so the team can allocate attention where it has the most impact.

**Secondary decision — pattern replication.** What do top-performing sellers have in common? If consistent patterns emerge — around category mix, freight strategy, dispatch speed, or geography — those patterns can inform how Olist onboards and coaches new sellers entering the platform.

**Tertiary decision — root cause diagnosis.** When a seller has a low review score, is the problem operational (they're dispatching late), structural (they're selling in a category with systematically high return rates), or geographic (they're shipping to regions with poor logistics infrastructure)? The tool should help the team distinguish between these causes, because each one calls for a different response.

## 3. Central Business Question

> *Which sellers on Olist deliver superior customer outcomes — measured by review score and delivery reliability — and what operational factors, including revenue concentration, freight cost, and product category, differentiate top performers from underperformers?*

This question has three properties that make it analytically useful: it defines a composite outcome variable anchored in the customer experience (review score and delivery reliability), it names the operational and commercial dimensions worth investigating as explanatory variables (freight, category, revenue, geography), and it produces a comparative output — top vs. underperformer — that is directly actionable for the Seller Success team. Revenue is treated as a seller-level contextual variable, not as a customer outcome: a seller can generate high GMV while delivering a poor customer experience, and that distinction matters for how the Seller Success team interprets the findings.

## 4. Analytical Sub-Questions

The central business question decomposes into eight sub-questions, ordered to build progressively from individual metrics toward an integrated seller profile.

**SQ1 — Performance segmentation.** How is average review score distributed across sellers? Are there natural clusters of high, mid, and low performers, or is the distribution continuous? This establishes the performance tiers that frame all subsequent analysis.

**SQ2 — Revenue concentration and outcome quality.** How concentrated is GMV among sellers, and is high revenue associated with better or worse customer outcomes? The goal is to determine whether top-revenue sellers also deliver superior review scores, or whether volume and quality are independent — which would have direct implications for how the Seller Success team prioritizes attention.

**SQ3 — Delivery delays: drivers and downstream effects.** What operational factors are associated with late deliveries — seller location, product category, order volume, freight type? And how strongly is delivery delay associated with lower review scores? This sub-question traces the chain from operational failure to customer dissatisfaction to seller performance, treating each link as a measurable association rather than a proven causal relationship.

**SQ4 — Freight cost as a performance lever.** Is there a relationship between freight cost relative to product price and a seller's review score? Sellers who charge disproportionate freight relative to their product price may be generating dissatisfaction that shows up in reviews, even when delivery itself is on time.

**SQ5 — Product categories prone to negative outcomes.** Are certain product categories systematically associated with negative customer outcomes — low review scores, late deliveries, or high freight-to-price ratios — regardless of which seller fulfills the order? If so, the problem is structural to the category, not attributable to individual seller behavior.

**SQ6 — Geographic structural disadvantage.** Do sellers in certain Brazilian states or regions face systematically longer delivery times or higher freight costs that negatively affect their review scores? If geography is a confounding variable, the Seller Success team needs to account for it before penalizing sellers for outcomes partially outside their control.

**SQ7 — Volume versus consistency.** Do high-volume sellers maintain their review score as order volume increases, or does scaling up correlate with greater inconsistency in customer outcomes? This tests whether performance is sustainable or degrades under load.

**SQ8 — Top performer profile.** Synthesizing the findings from SQ1–SQ7: what combination of operational characteristics — category, freight strategy, geography, dispatch speed, volume — best describes the sellers who consistently deliver superior outcomes on Olist? This sub-question produces the pattern that the Seller Success team can use as a reference for onboarding and coaching.

## 5. Key Metrics & Definitions

The following metrics define the analytical variables used throughout the analysis. Where a metric could be calculated in multiple ways, the definition below specifies the exact approach to ensure reproducibility.

**1. Average Review Score per Seller**
The arithmetic mean of `review_score` across all delivered orders associated with a seller. This is the primary customer outcome metric. Sellers with fewer than 5 reviewed orders are flagged as low-confidence and excluded from tier segmentation to avoid small-sample distortion.

**2. Seller GMV**
The sum of `price + freight_value` across all delivered orders associated with a seller. Freight is included because it represents real revenue flowing through the transaction, and excluding it would understate the economic footprint of sellers who operate in high-freight categories or regions.

**3. Order Volume**
The count of delivered orders per seller. Used as the denominator for rate calculations and as a segmentation variable in SQ7 (volume vs. consistency). Only orders with `order_status = 'delivered'` are counted.

**4. On-Time Delivery Rate**
The percentage of a seller's delivered orders where `order_delivered_customer_date ≤ order_estimated_delivery_date`. This is the primary delivery reliability metric. Orders with null delivery dates are excluded from this calculation.

**5. Average Delivery Delay**
The mean number of days between `order_delivered_customer_date` and `order_estimated_delivery_date`, calculated only for orders where the delivery was late (i.e., delay > 0). This metric captures severity of failure, complementing the On-Time Delivery Rate which captures frequency. A seller with a 10% late rate and a 15-day average delay is a meaningfully different risk profile than one with a 10% late rate and a 2-day average delay.

**6. Freight Ratio**
The ratio of `freight_value` to `price` per order item, averaged at the seller level. This normalizes freight cost relative to product value, making sellers in different price tiers comparable. A freight ratio above 0.3 (freight exceeds 30% of product price) is used as an exploratory threshold for high-freight burden, subject to revision after EDA.

**7. Dispatch Speed**
The number of days between `order_approved_at` and `order_delivered_carrier_date`. This measures the portion of the delivery timeline that is directly within the seller's control — the time between payment confirmation and handing the package to the carrier. It isolates seller-side operational speed from carrier transit variability.

**8. Performance Tier**
A derived categorical variable segmenting sellers into three groups — **Top**, **Mid**, and **Low** — based on a composite of Average Review Score and On-Time Delivery Rate. The exact segmentation thresholds are intentionally left open at this stage: they will be determined empirically after EDA of the score and delivery distributions, and documented explicitly in the analysis script before any segmentation is applied. This approach avoids imposing arbitrary cutoffs before the data has been examined. The final thresholds will be reproducible and included in the published code.

**9. Negative Review Rate**
The percentage of a seller's reviewed orders with `review_score ≤ 2`. While correlated with Average Review Score, this metric captures tail risk independently: a seller with a moderate average score but a high rate of very low reviews represents a different customer experience profile than one whose scores cluster around the mean. This distinction is operationally relevant for the Seller Success team's intervention decisions.

## 6. Scope & Constraints

**Dataset scope**
The analysis covers 99,441 orders placed on Olist between September 2016 and October 2018, across 3,095 sellers and approximately 32,951 products in 71 categories. Only orders with `order_status = 'delivered'` are included in the core analysis (96,478 orders), as cancelled, invoiced, and processing orders lack the complete timeline and outcome data required for delivery and review metrics.

**What is included**
Orders, order items, payments, reviews, sellers, products, product categories, customers, and geolocation data. All nine tables are used and joined through `order_id`, `seller_id`, `product_id`, and `customer_id` as primary keys.

**What is excluded**
- Orders with null delivery timestamps, which cannot contribute to delivery reliability metrics
- Sellers with fewer than 5 delivered orders, who are excluded from tier segmentation due to insufficient sample size for reliable averages
- The geolocation table is used at the state level only — zip-code-level precision is available but introduces noise from multiple coordinate entries per prefix

**Known limitations**

*Carrier vs. seller responsibility:* Delivery delay is measured from order approval to customer receipt, but the dataset does not distinguish between delays caused by the seller (slow dispatch) and delays caused by the logistics carrier (slow transit). Dispatch Speed (Metric 7) partially isolates the seller-controlled portion, but carrier performance remains a confounding variable.

*Static dataset and scalability:* The data used in this analysis is a historical snapshot covering 2016–2018, not a live feed. This dataset was selected to prototype and validate the monitoring tool — to demonstrate its analytical logic, metric definitions, and dashboard structure using real transactional data. The tool is designed to be fed with current operational data: the Python script and Tableau dashboard can be connected to an updated data export without structural changes, and any thresholds or benchmarks defined during this phase should be recalibrated at that point. In its current form, the analysis establishes the methodology and validates its usefulness; production deployment would require integration with Olist's live data infrastructure.

*Seller anonymization:* Seller identities have been replaced with fictional names. The analysis produces actionable patterns and segments, but cannot be linked back to real seller accounts without a mapping key not present in the dataset.

*Review participation:* Approximately 41% of customers left a written comment alongside their score. Text-based insights (if pursued) are subject to this selection bias — customers who write comments may not be representative of all reviewers.

## 7. Expected Deliverables

This project produces four deliverables, each serving a distinct purpose and audience.

**1. Python analysis script**
A clean, commented script structured by analytical phase, covering data loading and joining, exploratory data analysis, metric calculation, statistical associations, and seller segmentation. Each section maps to one or more sub-questions from Section 4. The script is reproducible: anyone who clones the repository and downloads the dataset from Kaggle can run the analysis from scratch without modification.

**2. Python visualizations**
A set of exploratory and analytical charts produced with matplotlib and seaborn, embedded directly in the analysis script. Each visualization includes a descriptive title, labeled axes with units, and an intentional color palette. These charts serve as the analytical layer — they are the working visuals used to derive findings, and are part of the code deliverable.

**3. Tableau dashboard**
An operational monitoring dashboard published to Tableau Public, designed for use by the Seller Success team. The dashboard answers the central business question visually and allows filtering by seller, category, state, and performance tier. The specific views and layout will be defined after the Python analysis is complete, based on the actual findings. A separate internal guide will document the step-by-step build process in Tableau, including data source connection, view construction, and dashboard assembly.

**4. Write-up and README**
A narrative write-up in English structured as: context → business question → process → findings → recommendations. This is the public-facing case study document, written for a recruiter or data team audience, not for the Seller Success team. Alongside it, a GitHub README that makes the repository self-explanatory: dataset source, setup instructions, file structure, and a summary of key findings with links to the Tableau dashboard.
