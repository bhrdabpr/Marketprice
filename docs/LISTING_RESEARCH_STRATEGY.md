# Listing Intelligence: evidence, creation and improvement

Research updated: 18 November 2026. Markets: Amazon.com and Amazon.ae.
Status: implementation specification; proposed quality targets are not achieved results.

MarketPrice stays one project. The guided workspace and deterministic listing preview were merged in PR #4 (main commit aaa03619f7757e20addd509f723cbc735cbf4d01). Its 287 passing software tests establish implemented behavior, not semantic quality, keyword coverage or sales improvement. The preview currently checks wording, identities and explicit quantities. It does not implement the research or drafting system specified below.

## 1. Two workflows, one evidence system

| Workflow | Input | Reviewable output |
|---|---|---|
| Improve an existing listing | Original listing, exact variant facts, marketplace/category/language, available research and performance evidence | Field-by-field findings; keep/change/remove decisions; before/after copy; explanation and sources for each change |
| Create a new listing | Verified product facts, supported benefits, included items, marketplace/category/language | Item name, Item Highlights, bullets, description, permitted search terms and required structured attributes; unresolved fields remain explicit |

Shared sequence: identify product → validate facts → research market → review keywords → allocate fields → draft → independently validate → seller review → export → measure outcomes.

No current price or purchase-cost data is required for content-only work. A future standalone interface can reuse these modules, but there is no reason to duplicate the financial application.

## 2. What the evidence can establish

| Signal | Legitimate use | Must not be interpreted as |
|---|---|---|
| Product specifications and supporting documents | Identity, material, dimensions, capacity, compatibility and supported claims for this exact variant | Automatically verified because an old listing or supplier used the wording |
| Amazon BSR | Category-relative sales position; help identify relevant comparison products | Keyword rank, keyword volume, absolute unit sales or proof that wording caused sales |
| Amazon autocomplete | Observed candidate phrases under a recorded search context | An exhaustive list or numerical monthly search volume |
| Visible competitor listing text | Vocabulary, information structure and claims made by that competitor | Hidden backend keywords, search demand or facts about our product |
| Organic search positions | Observed visibility for a specific query, store and context | A stable universal rank or proof of keyword causality |
| Product Opportunity Explorer | Amazon niche/query/product demand evidence within its reported scope | All searches, all purchases or an unrestricted public API |
| Search Query Performance | Authorized query funnel evidence, when eligible | Guaranteed availability to generic sellers or interchangeable advertising metrics |
| Third-party keyword volumes/ranks | Provider measurements or estimates with provenance | Official Amazon counts unless explicitly sourced and entitled as such |
| Google keyword metrics | Approximate Google demand for specified geography, language, network and period | Amazon demand or guaranteed clicks/sales |
| Google Trends | Relative interest, direction and seasonality under its scale/context | Absolute searches; missing/low-volume zero is not proof of no demand |

Amazon describes BSR as sales-based and distinguishes it from search rank. Compare BSR only within the same store/category context; keep category identifiers and observation time. [Amazon BSR](https://sell.amazon.com/blog/amazon-best-sellers-rank).

Google explicitly describes monthly search counts as approximate and may group close variants. Never add grouped variants together as independent demand. Google and Amazon metrics must stay in separate columns. [Google historical metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics).

Google autocomplete considers context and is not simply a most-searched list. Apply the conservative rule to suggestion imports: only claim the observed phrase and context, without inventing popularity. [Google autocomplete](https://blog.google/products-and-platforms/products/search/how-google-autocomplete-predictions-work/).

## 3. Practical acquisition without a Google Ads account or registered brand

Start with source exports and permitted observations. Add automation only where access, coverage and usage rights have been verified.

1. **Product truth:** catalog/supplier documents, seller-confirmed specifications and evidence references. Confirm generic versus branded status independently of Brand Registry membership. Do not fabricate branding or imply compatibility from a popular query.
2. **Amazon first-party research:** Product Opportunity Explorer is the first eligibility check for a Professional seller. UAE guidance explicitly confirms Professional-seller access and describes downloads. Verify the actual account, store and export fields before building an import mapping. US guidance also describes niche demand and purchasing insights. [UAE FAQ](https://sellercentral.amazon.ae/help/hub/reference/external/G7G4RNVTPQ9CWV39), [UAE research/download announcement](https://sellercentral.amazon.ae/seller-forums/discussions/t/1084cdf2-750a-4e57-b674-72b6388e9036), [US tool](https://sell.amazon.com/tools/product-opportunity-explorer/).
3. **Comparable listings and suggestions:** import permitted public observations or licensed exports. Store ASIN, product family, category, BSR, price/pack, copy, context and timestamp. Do not depend on undocumented autocomplete endpoints, intercepted seller sessions or bypassing access controls. Authorized Catalog Items API reads can supply available attributes, relationships and sales ranks; they are not consumer search-result rankings. [Catalog Items](https://developer-docs.amazon/sp-api/docs/catalog-items-api-v2022-04-01-reference).
4. **Google without personal Ads access:** Google Trends exports provide relative evidence. A commercial Google keyword-data API can provide provider-supplied demand metrics without connecting the seller's Google Ads account. DataForSEO documents Google Ads-derived volume, location/language parameters and separate provider credentials. This is a candidate integration, not a tested connection or a free service. [DataForSEO API](https://docs.dataforseo.com/v3/keyword_data-google_ads-search_volume-task_post/), [provider access example](https://dataforseo.com/help-center/build-a-keyword-research-template-with-search-volume-data-api).
5. **Optional Amazon keyword provider:** Helium 10's coverage page lists Cerebro and Magnet for both US and UAE. Start by validating permitted exports; the coverage table does not establish a public embedding API or redistribution rights. Keyword Tool documents suggestions and explicitly estimated Amazon volume via API. Test its specific country/language endpoint behavior before selecting it for UAE. [Helium 10 coverage](https://kb.helium10.com/hc/en-us/articles/360036359334-Which-Tools-Are-Supported-in-Which-Markets), [Keyword Tool API](https://keywordtool.io/api).
6. **Optional privileged analytics:** SP-API Search Query Performance lists US and AE, but requires Brand Analytics role and Brand Registry. It cannot be the default dependency for this user's generic products. [Amazon Analytics reports](https://developer-docs.amazon/sp-api/docs/report-type-values-analytics).

No supplier has been connected, purchased or independently accuracy-certified. Validate providers with the same representative US-English, UAE-English and UAE-Arabic query sets: coverage, correct store attribution, timestamps, unknowns versus zeros, repeated-request stability, provenance, estimates, cost, latency, quotas, export/API rights and allowed retention. Check source lineage: two vendors using the same upstream dataset are not independent corroboration. Reject silent worldwide/US fallbacks for UAE requests.

Google Trends website data is normalized; separate exports cannot be naively compared. Preserve the comparison set, region, category, search type and time range. Its official API remains an access-limited alpha and uses a different scaling model, so it is not an assumed production dependency. [Trends interpretation](https://support.google.com/trends/answer/4365533?hl=en), [Trends API](https://developers.google.com/search/apis/trends).

If measured demand is unavailable, the application must still offer a factual draft labeled **Demand unmeasured**. It must not label its selected terms “most searched.”

## 4. Product facts before keyword selection

Represent each fact separately: fact ID, attribute, value/unit, variant, source, source location, verification method, reviewer and status (confirmed, contradicted, unknown). An uploaded listing is a set of claims to assess, not its own proof.

Required identity includes SKU, ASIN when available, market, product type/category, language, parent/child variant, brand status, pack count and included items. Category-specific facts include material, dimensions, capacity, intended use, compatibility and supported differentiators. Required facts depend on product type; missing certification, safety, durability or performance evidence must not be filled by model inference.

Detect conflicts between file columns, product documents and images. Images may suggest an attribute for confirmation but cannot establish hidden material, certification or performance. Benefits must follow supported facts without strengthening them: a listed material alone cannot establish “leakproof,” “food safe,” “medical grade,” or a promised service life.

## 5. Comparable products and keyword decisions

Use two comparison groups: products satisfying the same buying intent, and products similar enough for attribute/wording comparison. Keep substitutes and accessories labeled separately.

A proposed starting cohort is 10–20 independent product families per category/store, subject to available evidence. This is a research design, not a universal optimal count. Include relevant bestsellers and ordinary competitors; avoid bestseller-only selection bias. Match use, material, size/pack and price tier where relevant, deduplicate variants/sellers, label sponsored observations, and preserve why each product was included or excluded. BSR helps select and describe the cohort; it never becomes a multiplier that makes a keyword factually acceptable.

Generate candidate phrases from confirmed product identity, relevant autocomplete observations, first-party queries, comparable copy and Google research. Generated synonyms are candidates requiring evaluation; they are not observed searches.

For each phrase, perform this decision sequence:

1. Resolve meaning, product intent and language; retain the raw phrase alongside normalization.
2. Classify the relationship: exact product intent, plausible synonym, substitute, accessory/complement, irrelevant or uncertain.
3. Check every attribute implied by the phrase against this variant's facts. Wrong capacity, material, audience, compatibility or pack size blocks placement, regardless of volume.
4. Check applicability of marketplace/category rules and branding restrictions.
5. Attach comparable evidence, direct demand or estimates, trend context and freshness separately.
6. Choose a destination and explain include/exclude/needs-review. An accessory phrase can be useful research yet unsuitable as a main-product keyword.

Rank only eligible phrases. Prefer exact product identity and buyer intent, then comparable Amazon demand where actually available, specificity and coverage; use Google evidence as a secondary signal. Avoid redundancy and preserve readability. Compare metrics only when provider, definition, scope and period are compatible. Do not invent weighted SEO scores or claim calibrated confidence from an LLM's self-rating. If weights are introduced later, fit and validate them on held-out decisions and test sensitivity.

Illustrative reasoning only, not measured keyword demand: for a confirmed non-insulated 500 ml steel bottle, “500 ml steel water bottle” can be eligible; “1 litre insulated bottle” conflicts with facts; “bottle cleaning brush” is an accessory intent. “Water flask” needs semantic/local-language review rather than automatic rejection for word mismatch. “Best water bottle” may reveal research intent without making “best” acceptable listing copy.

The keyword table should show phrase, market/language, semantic decision, supporting/conflicting fact IDs, observed source, Amazon demand/rank, Google demand/trend, freshness, proposed placement and reason. Missing measurements stay null.

## 6. Field-specific writing and policy checks

Amazon's official US and UAE announcements both state a July 27, 2026 change to 75-character titles for non-media categories and an additional 125-character searchable Item Highlights field. These are distinct fields. The linked detailed UAE help page required sign-in during this review; category-specific schemas and applicability still need authenticated verification. [US announcement](https://sellercentral.amazon.com/seller-forums/discussions/t/145b6d0f-999c-4555-896c-c694bda2e470), [UAE announcement](https://sellercentral.amazon.ae/seller-forums/discussions/t/2f40628c-eb97-4b24-b983-cb1e331e06dc).

| Field | Writing responsibility |
|---|---|
| Item name | Accurately identify the product with the strongest eligible core phrase and essential variant distinction; include brand only when appropriate |
| Item Highlights | Concise, supported differentiators/material/use details that complement the title |
| Bullet points | Answer purchase questions with evidence-backed features, benefits, size/fit, compatibility, included items and relevant limitations; avoid repeating one keyword list |
| Description | Coherent explanation of use, fit, care and specifications supported by facts; resolve likely buyer uncertainty |
| Backend search terms | Eligible synonyms/alternate vocabulary under current field rules; no hidden competitor-brand targeting or keyword stuffing |
| Structured attributes | Correct category, material, dimensions, color, capacity and variation fields; prose does not replace these |

Do not hard-code universal bullet counts/limits or assume US rules apply to UAE. Fetch and version product-type requirements per marketplace and validate destination attributes. Distinguish UI labels from API fields, count characters/bytes according to the actual constraint, and retain schema/rule versions. [Amazon listing schemas](https://developer-docs.amazon/sp-api/lang-en_US/docs/manage-product-listings-guide).

For UAE, research English and Arabic separately, including local synonyms and relevant transliteration; bilingual reviewers decide whether phrasing is natural. Do not transfer US volumes or mechanically translate a US keyword list. Keep output locales separately reviewable.

Generate a structured draft with claim-to-fact and phrase-to-evidence references. Then run independent deterministic checks for identity, values, units, contradictions, field limits, duplicates and prohibited content, plus semantic review. A second model can flag issues but cannot be the sole certification mechanism. Reject unexpected fields and instructions embedded in documents. A failed check returns a correction request, not silently rewritten facts.

## 7. Site experience and trust status

Home → Listing Intelligence → **Improve listing** or **Create listing**.

1. Product: upload/map files or enter facts; select store/category/language.
2. Facts: resolve contradictions and missing attributes once for the exact variant.
3. Research: show available sources, dates and missing coverage; allow cohort review.
4. Keywords: include/exclude decisions with reasons, demand source and field placement.
5. Draft: editable field cards, before/after changes for improvement, length indicators and clickable supporting evidence.
6. Review/export: show blocking issues and warnings separately, then export the draft plus evidence workbook. Save versioned review decisions.
7. Results: optionally import authorized performance reports and compare outcomes with uncertainty.

Use separate indicators for factual coverage, keyword relevance, market-data coverage, rule coverage and measured business outcomes. Do not compress them into one “95/100 optimized” badge.

Statuses: NEEDS_FACTS → RESEARCH_INCOMPLETE or READY_FOR_REVIEW → APPROVED_FOR_EXPORT. Approval belongs to a person and a fixed content/evidence/rule snapshot. Changed inputs invalidate approval. A limited-data draft may be reviewed/exported with its explicit limitations, but it must not receive a demand-validated label. Publishing is a separate later capability requiring approval and post-submission checks.

## 8. Benchmarks and release gates

Use public research to design evaluation, not to claim that another system's result is MarketPrice's result.

- **ESCI:** Amazon Science supplies real human-labeled query/product pairs for Exact, Substitute, Complement and Irrelevant relevance, including US English. Use its held-out queries to test candidate relevance and accessory/wrong-product mistakes. It does not supply UAE/Arabic coverage, current demand, current policies or evidence that generated listing copy increases conversion. [Official dataset and baseline](https://github.com/amazon-science/esci-data).
- **2026 PRECISE research:** combines human labels with model judgments to reduce evaluation bias. The design implication is to retain human gold labels and uncertainty estimates rather than letting a writer model approve itself. Its performance results do not transfer to our drafts. [AAAI 2026 paper](https://cdn.amazon.science/45/33/92bf4af4492e8d058045c19bd5f9/precise-aaai-2026-camera-ready.pdf), [June 2026 follow-up](https://arxiv.org/abs/2606.05308).
- **Our own gold set:** product facts, permitted market observations, accepted/rejected keywords and reviewed field drafts for US English, UAE English and UAE Arabic. Two independent qualified reviewers, blind comparisons and adjudication of disagreements. Keep product families and queries separate across development/test splits; include temporal holdouts. Public benchmarks may have appeared in model training, so retain fresh private cases.

Compare current lexical baseline, semantic relevance plus hard constraints, and constrained drafting using the same cases. Evaluate keyword precision/recall, Precision@5, graded ranking quality where applicable, contradiction detection, unsupported-claim rate, policy violations, appropriate abstention, reviewer edits, source coverage, cost, p50/p95 latency and total active seller time. An abstaining system cannot pass on precision alone: report coverage and missed useful terms too.

Proposed initial gates, to be validated with the pilot rather than advertised as achieved:

| Gate | Proposed requirement |
|---|---|
| Evidence | Every factual addition and every numerical demand claim has a traceable source and correct scope |
| Critical defects | No observed invented safety/certification claims or wrong-product/variant additions in the release test set; report sample size and confidence bounds, not “zero risk” |
| Keyword quality | Target at least 98% precision among accepted core phrases, with coverage and uncertainty reported separately per market/language |
| Deterministic checks | All applicable tested rules pass; unknown applicability remains unresolved |
| Robustness | Missing/stale data, provider outages, wrong geography and malicious content never produce fabricated success |
| Efficiency | Proposed median active preparation under 10 minutes for evidence-complete routine SKUs, including review; measure cold-start gathering separately and report p95 |
| Business effect | No claimed conversion/sales uplift until an appropriately designed study supports it |

Start a reviewed pilot with 50 product families per market/language track; this is discovery, not enough to prove rare-error safety. Expand sample sizes according to observed errors and the required confidence. Account for repeated queries/variants when calculating uncertainty. Do not choose the model from a generic chatbot leaderboard.

## 9. Learn from actual market response

Freeze content version and deployment time. Where data permits, measure query-level impressions, clicks and purchases using the report's own definitions, plus sessions, ordered units, returns and profit context. CTR is clicks/impressions only when both use the same scope. Orders/clicks and units/sessions are different measures; label denominators and attribution windows. Do not infer organic CTR from BSR or invent it when reports are unavailable.

Record price, promotions, ad spend, stock, delivery terms, reviews and seasonality because they can change performance independently of text. Predefine primary metric, minimum detectable change, duration and stopping rule. Prefer randomized listing experiments when actually eligible. Amazon Manage Your Experiments requires Brand Registry representation and eligible ASINs; generic products cannot assume access. [Amazon experiments](https://sell.amazon.com/tools/manage-your-experiments).

For ineligible products, use staged rollout and comparable unchanged controls where feasible. Report results as observational unless the design justifies a causal claim. Do not present a one-week before/after sales increase as proof. Keep rollback snapshots, monitor factual complaints/returns, and require adequate evidence before promoting a new keyword/writing policy.

## 10. Engineering, privacy and delivery order

Separate modules: product facts, source adapters, competitor cohorts, keyword decisions, marketplace policies, drafts, review snapshots, exports and outcomes. Reuse MarketPrice's file safety and evidence exports. Keep listing logic isolated from monetary calculations.

Core records: ProductFact; ResearchObservation (provider and upstream source, source type/URL or file hash+cell, market, language, category, query/ASIN, metric definition/unit, period, observed time, estimate flag, coverage and access rights); KeywordDecision; DraftClaim; RuleSnapshot; ReviewSnapshot; OutcomeObservation.

Source adapters return explicit COMPLETE/PARTIAL/UNAVAILABLE states. Enforce timeouts, retry budgets, pagination completeness, quotas, bounded responses, cancellation and per-tenant cache keys. Use provider allowlists and SSRF defenses for URL imports. Store secrets server-side, exclude them from logs, and define retention/deletion for files, text, embeddings and exports. Models receive only approved product fields; financial/customer data and ignored workbook columns are excluded. Never execute workbook formulas/macros or instructions embedded in retrieved text. Generated text cannot choose outbound destinations or publish listings.

Build in this order:

1. Evidence/fact contracts and mapped source imports; tests for units, provenance, stale/wrong-market data and null metrics.
2. Comparable cohort and keyword decision table; public ESCI baseline and fresh US/UAE reviewer cases.
3. Marketplace/category policy registry; verify current schemas and export targets.
4. Constrained creation and improvement workflows with claim checks, revision diffs and approval invalidation.
5. Provider integrations selected through documented coverage/rights/cost validation, tested with failure fixtures and authorized live reads.
6. Timed seller pilot and performance-report feedback; public release claims limited to measured evidence.

This research pass reviewed official documentation and research papers. No live seller dataset, authenticated keyword API, model benchmark or market experiment was run. The next engineering milestone is the evidence and keyword-decision layer, followed by drafting; the existing lexical checker is not a substitute for either.
