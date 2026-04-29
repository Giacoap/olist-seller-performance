# Olist Seller Performance — A Monitoring Tool for the Seller Success Team

## Executive Summary

This analysis examines what differentiates high-performing sellers from underperformers on Olist, Brazil's largest marketplace intermediary, using two years of transactional data covering nearly 100,000 orders and 3,000 sellers. The dominant operational driver of customer satisfaction is **dispatch speed** — the time a seller takes to hand off a package to the carrier — not freight cost, geographic location, or order volume. Top-tier sellers dispatch roughly twice as fast as their Low-tier peers, and that single behavior cascades into higher on-time delivery rates, higher review scores, and lower negative review rates.

A counterintuitive finding shapes the strategic implication: **high revenue does not predict high quality**. The second-largest seller on the platform sits in the Low tier with a 25% negative review rate, demonstrating that commercial success and customer outcomes are essentially independent dimensions. The output of this analysis is an operational monitoring tool — a Tableau dashboard backed by a reproducible Python pipeline — designed for ongoing use by Olist's Seller Success team to prioritize interventions, replicate top-performer patterns, and diagnose root causes of underperformance.

## Context

Olist is a Brazilian marketplace intermediary that connects small and medium sellers to major e-commerce channels under a single contract. Sellers list through Olist and fulfill orders directly to customers using Olist's logistics network — meaning that once an order is placed, the seller is responsible for packing, dispatching, and meeting delivery commitments. The platform brokers visibility and infrastructure; the seller delivers the actual customer experience.

This division of labor places sellers at the center of the marketplace's reputation. A late dispatch, a mispriced freight charge, or a product that doesn't match its listing degrades the customer experience — and that degradation is visible at the platform level, not just the individual transaction level. Olist's commercial success is structurally tied to how consistently its seller base performs.

The team responsible for managing that performance — Seller Success — operates with a fundamental information disadvantage. Each individual seller sees their own orders, reviews, and delivery outcomes, but only Olist sees the full picture: which categories generate the most complaints, which sellers consistently overperform or underperform their peers, and which patterns separate the two groups. Without that systemic view made explicit, the team cannot prioritize interventions, identify what good performance looks like, or distinguish operational problems from structural ones. This analysis exists to make that view available.

The primary measurement instrument is the post-purchase satisfaction survey. After receiving an order — or after the estimated delivery date passes — customers rate their experience on a 1–5 scale. This review signal is the most systematic seller-level outcome metric available in the dataset, and it anchors every comparison in the analysis that follows.

## Approach

The analysis was structured around a single central question: *which sellers on Olist deliver superior customer outcomes — measured by review score and delivery reliability — and what operational factors, including revenue concentration, freight cost, and product category, differentiate top performers from underperformers?* That question was decomposed into eight sub-questions covering performance segmentation, the relationship between revenue and quality, the drivers and consequences of delivery delays, freight cost as a performance lever, category-level outcomes, geographic effects, the volume-consistency tradeoff, and a synthesized profile of the top performer.

The dataset is the Brazilian E-Commerce Public Dataset by Olist, published on Kaggle, covering 99,441 orders placed between September 2016 and October 2018 across 3,095 sellers and approximately 33,000 products in 71 categories. Seller and partner identities have been anonymized using names from Game of Thrones — a privacy convention that preserves analytical utility while preventing re-identification of real businesses. Throughout this writeup, references to specific sellers (Daenerys Targaryen, Jon Snow, etc.) are these anonymized identifiers, not real merchants.

The core analysis was restricted to delivered orders (96,478 of 99,441), where complete delivery and review timelines exist. Sellers with fewer than five delivered orders were excluded from tier segmentation to avoid small-sample distortion, leaving 1,766 tier-eligible sellers; the remaining 1,204 sellers below the threshold remain visible in the dashboard for monitoring purposes but are flagged as low-confidence and excluded from comparative tier analysis until they accumulate sufficient history. Five primary metrics were computed at the seller level: average review score, on-time delivery rate, average dispatch speed (days from order approval to carrier handoff), freight ratio (freight value relative to product price), and negative review rate (% of orders with a 1–2 star score). The Performance Tier was constructed empirically from the observed distributions: **Top tier requires both an average score ≥ 4.5 AND an on-time rate ≥ 90%** (the joint p75 of the eligible population), while **Low tier flags any seller with average score ≤ 3.8 OR on-time rate < 80%** — the OR rule was deliberate, ensuring that delivery failures surface even when customers have rated leniently.

The analytical pipeline was implemented in Python using pandas and numpy for data processing, with matplotlib and seaborn for exploratory visualization. The final outputs include a reproducible analysis script, four exported metric tables that feed an operational Tableau dashboard, and the dashboard itself, published to Tableau Public for ongoing use by the Seller Success team.

## Key Findings

### The dominant signal: dispatch speed

The single strongest pattern in the entire dataset is the relationship between how quickly a seller hands off a package to the carrier and every downstream customer outcome. Top-tier sellers dispatch in a median of 1.74 days; Low-tier sellers take 3.42 days — exactly twice as long. That operational gap propagates directly into customer experience: late deliveries are associated with an average score drop of 1.73 points (on-time mean = 4.30 vs. late mean = 2.57, Mann-Whitney p ≈ 0), and dispatch speed itself is a meaningful predictor of on-time delivery (Spearman r = -0.262, p < 0.0001). Sellers who take longer to hand off are reliably worse at hitting delivery windows, and missed delivery windows are the strongest single driver of negative reviews. Everything else in this analysis is secondary to this one operational variable.

### Two hypotheses that didn't survive the data

The scoping plan flagged two intuitive hypotheses worth testing: that disproportionate freight cost generates customer dissatisfaction, and that sellers in regions with poor logistics infrastructure face a structural disadvantage. Neither held up.

Freight cost showed a Spearman correlation of just -0.047 with average review score — statistically significant at α = 0.05 only because of the large sample, but practically negligible. The median score gap between high-freight and normal-freight sellers is 0.058 points, well below any meaningful threshold. Customers appear indifferent to freight cost as long as delivery is on time, which points back to dispatch speed as the dominant mechanism.

Geography was directionally correct but statistically weak: state-level median on-time rates and median review scores correlate at Spearman r = 0.511, but with only 12 states qualifying for inclusion, the result fell short of significance (p = 0.089). More telling, São Paulo and Rio de Janeiro — Brazil's two largest urban hubs — are tied for the worst on-time rates among large states. Concentration in logistics hubs is not the structural advantage one might expect.

### Volume and quality: two independent dimensions

High revenue does not predict high quality, but high volume does predict high consistency — and these two findings together reframe how the platform should think about its largest sellers.

GMV and average review score correlate at Spearman r = -0.152 (p < 0.0001) — a weak but real negative relationship. The Top tier holds 19.3% of eligible sellers but only 7.4% of eligible GMV, while the Mid tier carries 81.3% of GMV. The clearest demonstration: the second-largest seller on the entire platform by revenue (Daenerys Targaryen, R$ 237K GMV) sits in the Low tier with a 25% negative review rate. Commercial weight and customer outcomes are largely independent at the seller level — weakly related, but not in any direction that would let revenue serve as a proxy for quality.

At the same time, score standard deviation halves across volume quartiles — from 0.611 in Q1 to 0.295 in Q4. High-volume sellers are significantly more predictable, even when their median score is marginally lower. Scale doesn't degrade quality; it stabilizes it. The implication is that the Seller Success team should treat large sellers as predictable known quantities and reserve high-touch intervention for low-volume sellers, where outcomes are inherently more variable.

### Categories carry two distinct types of problems

Analyzing review scores at the category level surfaces a useful distinction between operational failures and structural ones. The audio category has the third-worst average score (3.84) and simultaneously the highest late-delivery rate among bottom categories (12.9%) — its problem is operational, and the lever is delivery improvement. By contrast, men's fashion clothing scores second-worst (3.82) with a low late-delivery rate of just 4.7% — its problem is structural, likely a mismatch between product expectation and what arrives. Both categories produce equally bad reviews, but they require entirely different interventions: faster dispatch versus better product listings or sizing standards. This distinction is one the dashboard surfaces directly so the team can route problems to the right owner.

### The shape of the problem

The tier segmentation gives the Seller Success team a quantified picture of its workload. Of the 1,766 tier-eligible sellers, 18.0% fall into the Low tier — sellers carrying real reputational risk. They represent 11.4% of eligible GMV, meaning that the bottom-quality cohort isn't trivial commercially: it carries weight worth protecting through intervention rather than written off. A broader view shows that 23.9% of eligible sellers have average scores below 4.0, suggesting that the active monitoring perimeter is roughly a quarter of the seller base, not a small minority. This is the operational scale the dashboard is built to support.

## The Tool in Action

The findings above describe the marketplace as a system. The dashboard built on top of those findings is what makes them operationally useful — it lets the Seller Success team move from systemic patterns to specific sellers, and from observation to decision, in a single session. A typical workflow is to filter the seller table by tier, sort by GMV descending, and let the highest-stakes cases surface to the top. Three examples make the mechanic concrete.

**Filtering Low tier and sorting by GMV puts Daenerys Targaryen at the top of the list.** She is the second-largest seller on the entire platform by revenue, and she is squarely in the Low tier:

| Metric | Value |
|---|---|
| Orders | 973 |
| GMV | R$ 237,807 |
| Avg review score | 3.50 |
| On-time delivery rate | 89.9% |
| Negative review rate | 25.2% |
| Avg dispatch days | 11.4 |
| Freight ratio | 0.290 (normal) |

The diagnosis writes itself: freight is unremarkable and on-time rate is borderline acceptable, but dispatch speed of 11.4 days is roughly six times the platform's top-performer median. One in four customers leaves a negative review. This is the highest-stakes intervention case in the dataset — high commercial weight, consistently poor customer outcomes, a clear operational lever to pull.

**Daenerys is not the only profile worth flagging.** Viserys Targaryen sits much lower on the GMV ranking but is even more extreme on the negative review dimension, demonstrating that the tool surfaces problem patterns at multiple scales:

| Metric | Value |
|---|---|
| Orders | 187 |
| GMV | R$ 42,047 |
| Avg review score | 2.79 |
| On-time delivery rate | 86.1% |
| Negative review rate | **46.5%** |
| Avg dispatch days | 10.8 |

Same operational signature as Daenerys — slow dispatch (10.8 days), borderline OTR — but with nearly half of customers leaving negative reviews. Smaller commercial footprint, higher per-order risk. Without the OR rule in tier assignment, sellers like Viserys would be drowned out by GMV-weighted views; the dashboard surfaces them by design.

**The contrast with a Top-tier seller closes the loop.** Kevan Lannister, in the same São Paulo–Rio de Janeiro logistics corridor, shows what good looks like at small scale:

| Metric | Value |
|---|---|
| Orders | 57 |
| GMV | R$ 53,914 |
| Avg review score | 4.57 |
| On-time delivery rate | 100% |
| Negative review rate | 5.3% |
| Avg dispatch days | 3.2 |

Kevan moves at less than a third of Daenerys' dispatch time, and every other metric follows. Used this way, the dashboard is both a monitoring tool — it surfaces who needs attention — and a benchmarking tool — it shows what attainable looks like in the same operational environment. The Seller Success team can walk into a coaching conversation with Daenerys carrying a specific reference point, not just a generic recommendation.

## Recommendations

The following recommendations are direct translations of the findings into operational decisions for the Seller Success team. Each one is tied to a specific evidence point in the analysis.

**Make dispatch speed the primary monitoring metric.** Dispatch speed is the strongest single predictor of every customer outcome examined in this analysis, and it is fully within the seller's control. It deserves the most prominent position in the dashboard, in the team's weekly review cadence, and in any seller-facing performance summary. Review score is the outcome to optimize, but dispatch speed is the lever to pull.

**Establish a "<3 days dispatch" benchmark in onboarding and coaching.** Top-tier sellers dispatch in a median of 1.74 days, and roughly 75% of them stay below the 3-day mark; the Low tier takes nearly twice as long, with a median of 3.42 days. The "<3 days" threshold is therefore not arbitrary — it sits at the boundary between Top-tier behavior and the rest of the population. Encoding it as an explicit, numerical onboarding standard — communicated upfront and reinforced in coaching conversations — gives new sellers a concrete target rather than a vague "be fast." It also gives the Seller Success team a clean threshold for early intervention before review scores deteriorate.

**Launch a "Critical Accounts" program for high-GMV Low-tier sellers.** Sellers who land in the Low tier while sitting in the top GMV quartile carry both reputational risk and commercial weight — they cannot be written off, and they shouldn't be treated as routine. Daenerys Targaryen is the most extreme example, but a filter on the dashboard surfaces the full cohort. This group warrants dedicated, named account management rather than generic outreach.

**Route category problems to the right owner.** The dashboard distinguishes operational failures (high late-delivery rates) from structural ones (low scores despite on-time delivery). Categories with operational signatures, such as audio, should be routed to logistics partnerships and dispatch coaching. Categories with structural signatures, such as men's fashion clothing, should be routed to catalog and listing-quality teams. Same symptom, different organizational owner.

## Limitations & Future Work

### Limitations

**Association, not causation.** The relationships reported in this analysis — between dispatch speed and on-time delivery, between late delivery and review score, between volume and consistency — are statistical associations measured on observational data. The patterns are robust enough to justify operational decisions, but proving causal mechanisms would require controlled experimentation that is outside the scope of a marketplace dataset.

**Carrier versus seller attribution.** Delivery delay is measured end-to-end, from order approval to customer receipt, but the data does not cleanly separate slow dispatch (the seller's responsibility) from slow transit (the carrier's). The Dispatch Speed metric isolates the seller-controlled portion deliberately, but residual carrier variability is a confounding factor in any seller-level delivery comparison. A future iteration with carrier-level metadata would tighten this separation.

**Static historical snapshot.** The dataset covers September 2016 to October 2018. Thresholds defined here — the 4.5/0.90 Top-tier cutoff, the <3 days dispatch benchmark — were calibrated against that population and should be revalidated against current data before being applied operationally. The analytical logic is portable; the specific numerical cutoffs are not.

### Future work

**Connect the pipeline to live data.** The Python script and Tableau dashboard were designed to accept an updated data export without structural modification. Integrating the tool with Olist's production data infrastructure is the natural next step, transforming this analysis from a methodology prototype into a continuously running monitoring system.

**Apply NLP to review comments.** Roughly 41,000 reviews include written customer comments — a substantial corpus that this analysis did not use. Categorizing complaints by topic (delivery, product quality, packaging, communication) would refine the operational-versus-structural routing recommended above and surface failure modes invisible at the metric level.

**Move from descriptive to predictive monitoring.** The current tool flags sellers who have already declined into the Low tier. A natural extension is a predictive layer that identifies sellers showing early signals of decline — rising dispatch times, falling review scores in recent weeks — before they cross the threshold. This shifts the Seller Success team from reactive intervention to preemptive coaching.
