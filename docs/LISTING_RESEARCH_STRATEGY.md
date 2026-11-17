# Evidence-backed listing research for Amazon.com and Amazon.ae

Status: proposed implementation strategy, not a production-readiness claim.
Research date: 17 November 2026.
Baseline: a3fd42d87928cfa50daa0c04501b3b7752462c7f.
Selected markets: Amazon.com and Amazon.ae. English first for US; separate English and Arabic research tracks for UAE, with reviewed locale-specific copy.

## Architecture decision

Keep one MarketPrice repository and add an independently testable Listing Intelligence workspace. Reuse identity, file safety, audit exports and optional pricing context. Isolate listing models, evidence, policy rules, keyword selection and drafting from the Decimal pricing engine. A content-only job requires no purchase cost.

A future standalone listing interface can use the same library. Split repositories only if deployment, ownership, permission boundaries or release cadence justify the maintenance cost. Do not fork the financial code or mix listing quality into margin calculations.

The local prototype is an offline lexical checker. It is not a semantic relevance engine, competitor researcher or production copy generator. The prior local full suite reported nine UI failures, while GitHub main had passing CI. Reconcile the local/GitHub difference before promoting prototype code.

Suggested module boundaries (proposed, not implemented): listings/contracts, imports, evidence, competitors, keywords, policies, drafting, review, exports; connectors/amazon and connectors/google. Prefer one deployable application with clear internal modules initially.

## Outcome and trust contract

Goal: reduce active seller preparation time from hours to minutes for routine, evidence-complete products. Measure preparation, data gathering, waiting, review and corrections separately. Do not hide work in manual preprocessing. Cold-start authorization or missing specifications cannot be promised as a minutes-long job.

The system should produce an editable, evidence-backed draft, not a guarantee of accuracy, rankings or increased sales. It must abstain on unsupported facts. Commercial keyword signals can prioritize supported terms but cannot make a false product claim acceptable.

Statuses: NEEDS_FACTS, RESEARCH_INCOMPLETE, READY_FOR_REVIEW, APPROVED. Only an authorized reviewer can set APPROVED for a specific content/evidence/rule snapshot. A changed input invalidates approval. No automatic publishing in the initial release.

## Source matrix: what each signal means

| Source | Use | Access and limits |
|---|---|---|
| Manufacturer/merchant specifications | Product identity, variant, dimensions, materials, included items, supported benefits | Evidence reference per fact; distinguish seller assertion from verified documentation; competitor text is not proof about our product |
| Amazon Search Query Performance | Marketplace-specific query funnel evidence for eligible brands/products | Authorized SP-API Brand Analytics role and Brand Registry; validate availability/report periods for each marketplace |
| Amazon advertising search-term exports | Observed paid queries and attributed outcomes | Seller-authorized exports or Ads API access; retain attribution window, match type and sample size; not organic demand |
| Amazon Catalog Items | Comparable product attributes and available sales ranks | Authorized API; salesRanks are category sales positions, not keyword ranks or monthly unit estimates |
| Amazon product pages/autocomplete | Buyer vocabulary and possible candidates | Only permitted access or supplied/licensed exports; autocomplete ordering is not search volume; no undocumented endpoint dependency |
| Google Ads Keyword Planner | Regional keyword ideas and approximate Google search demand | OAuth, Ads account and developer-token access; retain geography, language, network, period and close-variant grouping |
| Google Trends | Direction, seasonality and regional interest | UI exports use relative normalization; separate exports may not be comparable. Official API is alpha with access application and different scaling |
| Google Search Console | Actual query performance for an authorized owned site | Not competitor queries; top-row/privacy limitations and attribution differences |
| Google search observations | Search intent, category vocabulary and page patterns | Timestamped locale/device observations through permitted access; a search snippet is not a complete or unbiased competitor dataset |

Do not sum Google and Amazon volumes, treat Ads competition as organic difficulty, convert BSR into unit sales without an explicitly labeled calibrated model, or infer keyword causality from a successful competitor.

Official evidence:
- [Google historical metrics](https://developers.google.com/google-ads/api/docs/keyword-planning/generate-historical-metrics)
- [Google Ads authorization](https://developers.google.com/google-ads/api/rest/auth)
- [Google Trends alpha](https://developers.google.com/search/apis/trends)
- [Trends data interpretation](https://support.google.com/trends/answer/4365533?hl=en)
- [Search Console data limitations](https://support.google.com/webmasters/answer/96568)
- [Amazon Analytics reports](https://developer-docs.amazon/sp-api/docs/report-type-values-analytics)
- [Amazon Catalog Items](https://developer-docs.amazon/sp-api/lang-en_us/reference/searchcatalogitems)
- [Amazon BSR explanation](https://sell.amazon.com/blog/amazon-best-sellers-rank)

## Workflow: analyze before drafting

### 1. Establish the product truth

Import catalog text separately from reference facts. Required identity: marketplace, seller/account context, SKU, ASIN if available, parent/child variant, product type and language. Gather brand, model, use case, material, dimensions/capacity, compatibility, pack count, included/excluded items and evidence-backed differentiators.

Highlight missing or contradictory facts. Never turn an existing marketing claim or competitor assertion into verified evidence. Existing listing text is a claim to review. Preserve original values, source file hash and sheet/cell or JSON pointer.

### 2. Build a comparable competitor cohort

Filter by marketplace, leaf category, actual product type, intended use, compatibility, pack size, condition and comparable price tier. Separate parent/child records and deduplicate families. Include varied sellers and performance levels to reduce bestseller-only selection bias.

Record ASIN, title/highlights/bullets, attributes, price/currency, availability, rating count, category path, BSR category/value, observation time and source. Record organic keyword position separately, with query, locale, device and sponsored status when available. Missing fields remain missing. Do not compare BSR numbers across categories/stores.

Start with a reviewed small cohort (e.g. 10–20 comparable families) as a pilot design, not a statistical standard. Report exclusions and coverage. Extract recurring buyer concepts and potential information gaps without copying distinctive competitor wording or borrowing competitor brand terms.

### 3. Create the keyword evidence ledger

Collect candidate phrases from product facts, eligible Amazon query reports, ads exports, competitor concepts, permitted suggestions and Google research. Analyze phrases individually; do not select single words in isolation when intent depends on the full phrase.

Each candidate needs:
- Original phrase, normalized phrase, language and marketplace.
- Intent label: exact product, valid use case, substitute, accessory/complement, incompatible, ambiguous.
- Matched product facts, contradictory facts and evidence IDs.
- Source-specific metrics, units, periods, geography, retrieval time and missingness.
- Policy/trademark/unsupported-claim flags.
- Decision: INCLUDE, EXCLUDE or REVIEW, with reason and reviewer.
- Proposed placement and what information the phrase adds.

A phrase such as “1 litre insulated bottle” fails if the product is documented as 500 ml and insulation is unverified, regardless of search demand. “Water flask” may be a valid synonym despite poor lexical overlap, so it needs semantic review rather than automatic rejection.

First apply hard factual/policy filters. Then compare relevant phrases within the same source/market/period using buyer intent, observed demand, conversion evidence, seasonality, distinct coverage and readability. Do not assign arbitrary universal weights or display an uncalibrated confidence percentage. Preserve raw metrics and explain tie-breaks. Deduplicate close variants without double-counting grouped Google metrics.

### 4. Build a field placement brief

Title: product identity, primary relevant phrase and distinguishing variant facts, within the applicable rule pack.
Item highlights: complementary supported attributes; not a duplicate keyword list.
Bullets: one buyer question/benefit per point, backed by specifications; include compatibility, use, construction and included items where relevant.
Description: coherent explanation, appropriate use, limitations and details not clearly covered elsewhere.
Backend search terms: only permitted relevant terms under current field limits; do not expose or infer competitor private terms.

Every selected phrase has a placement rationale. Not every accepted keyword must appear verbatim. Natural language and factual clarity take priority over repeated exact matches. Preserve negation (“not compatible”) and conditional claims.

### 5. Draft, validate and review

Generate a small number of bounded alternatives from approved facts and the placement brief. Every new factual claim must link to evidence. A separate validation pass checks brand/model/variant, numbers/units, pack counts, exclusions, prohibited claims, current schema limits, repetition, translation drift and unsupported additions.

US and UAE drafts are separate. Arabic requires native-language evaluation, RTL preview and mixed-script/model-number tests. Translating US keywords is not UAE keyword research. Do not mix languages into an Amazon field without verified support.

Amazon's 2026 public FAQ describes 75-character Item name and 125-character Item highlights. Resolve store/product-type applicability and exceptions using current schemas/help before enforcing these on UAE. Do not silently apply the old universal 200-character title rule or assert UAE rollout from US guidance alone.
Sources: [title update](https://sellercentral.amazon.com/seller-forums/discussions/t/4ba9a173-d896-4b69-81fb-57e148f98356), [Product Type Definitions](https://developer-docs.amazon/sp-api/lang-en_EN/docs/product-type-definitions-api), [validation preview](https://developer-docs.amazon/sp-api/lang-en_us/docs/preview-errors-before-creating-a-listing).

Present original versus proposed text, included/excluded keyword reasons, unresolved risks and data freshness. Preview validation is useful but does not prove eventual publication or search performance.

### 6. Export and learn

Export a review workbook: Product_Facts, Evidence, Competitor_Cohort, Keyword_Decisions, Placement_Plan, Drafts, Validation, Approvals and Sources. A separate platform upload artifact is generated only after validation against the actual destination schema. Never treat a generic audit workbook as an Amazon upload template.

Retain content versions and subsequent outcomes. Where the store/account/product is eligible, use Amazon Manage Your Experiments; otherwise call observational before/after comparisons observational and track price, stock, ads and seasonality confounders. Check UAE availability independently. [Amazon experiments](https://sell.amazon.com/tools/manage-your-experiments).

## Evidence contract and safety

An evidence record requires: evidence_id, product_id/query, provider, source_reference, marketplace, country, language, observed_at, period_start/end if relevant, metric_name, value or explicit unavailable status, unit/currency, collection_method, source_hash, usage_rights, and any sampling/grouping limitations.

Never compare values with incompatible units or time/geography contexts. Null is not zero. Store USD and AED separately. Snapshot policy, prompt, model and evidence versions for reproducibility. Source freshness is metric-specific and shown to users; choose refresh schedules from pilot needs rather than pretending one universal TTL is valid.

No costs, customer/order PII, tokens or ignored spreadsheet columns are sent to a content model by default. External providers receive an allowlisted payload after configuration review. Secrets remain in tenant-scoped secure storage. Protect logs, caches, embeddings and exports; define retention and deletion.

Process files with resource limits; never execute formulas/macros. Export literal spreadsheet text. Treat all product/competitor content as untrusted input, not instructions. Models have no publishing permissions. Permit only authorized outbound providers; enforce SSRF protections, timeouts, response limits, retry budgets and cancellation. OAuth failures and partial pagination produce incomplete research, not fabricated evidence.

Initial connectors may use verified source exports. Live automation requires legitimate provider credentials/eligibility and a successful authorized smoke test. No proxy-based bypass, scraped seller sessions or unapproved paid services.

## Phased implementation and acceptance

1. Foundation/reconciliation: integrate the existing listing prototype into a clean branch from GitHub main, resolve UI regressions, and establish separate listing/evidence contracts. Gate: full suite plus no-loss CSV/XLSX mapping and export tests.
2. Evidence imports: product facts, Amazon research exports and Google exports with user-visible mapping and provenance. Gate: totals/units/periods reconcile with source; malformed and missing evidence never silently becomes zero.
3. Research brief: comparable cohort, phrase-level relevance decisions and placement rationale. Establish a lexical baseline and adjudicated semantic test set. Gate: publish false-inclusion/false-exclusion results per market/language and unsupported-claim counts.
4. Draft/review workflow: constrained copy variants, independent validators, reviewer decisions and invalidation. Gate: every factual addition has evidence; tested critical mismatches block approval; unknown applicability stays unresolved.
5. Authorized API reads: validate quotas, 429/timeouts, token revocation, pagination, incomplete data and account separation with mocks, followed by authorized live smoke tests. Gate: no silent incomplete catalogs or cross-tenant access.
6. Seller pilot and optional publishing: benchmark active end-to-end time and correction rate against existing workflow. Add publishing separately with explicit approval, stale-content checks, bounded updates and post-submit reconciliation.

A proposed pilot goal is median active review-ready preparation under 10 minutes per evidence-complete routine SKU, with no worse expert-rated factual quality than the manual baseline. This is a target, not a measured result. Record p50/p95 active and wall time, setup costs, reviewer edits and severe errors; do not claim success from model latency alone.

Use ESCI for public query–product relevance sanity checks, not current marketplace policy or conversion prediction. Add independently reviewed English/Arabic UAE cases, product-family holdouts and adversarial examples. Evaluation must include tempting high-volume irrelevant phrases, wrong variants, misleading compatibility, stale data and malicious spreadsheet content.

## Initial backlog

- [ ] Reconcile local prototype and GitHub; repair the nine known local UI-test mismatches.
- [ ] Define ListingRecord, ProductFact, ResearchEvidence, KeywordDecision and Approval contracts.
- [ ] Add US/UAE marketplace profiles with unresolved rules visible.
- [ ] Add source-export mapping, evidence coverage and freshness reports.
- [ ] Build competitor cohort review and keyword include/exclude ledger.
- [ ] Build bilingual evaluation corpus and frozen holdout.
- [ ] Add placement brief, evidence-constrained drafts and edit comparison.
- [ ] Validate source API access per account; integrate read-only connectors incrementally.
- [ ] Run timed seller pilot and publish limitations alongside results.

## Work completed for this proposal

Reviewed current main, the local prototype and official Google/Amazon documentation. Defined the market scope, architecture, evidence workflow and release gates. This draft contains no merchant data, credentials or performance claims.

No live Ads, Trends, SP-API or seller account was connected. Postman discovery status failed with a local keychain error; Orbit discovery could not resolve its host. Official provider documentation was used as fallback. These discovery failures do not establish anything about provider availability to an authorized production account.

Product category, evidence availability, seller API eligibility and pilot catalogs remain needed before a product-specific research pass. Obtain secrets only through secure configuration, not chat or spreadsheets.
