# Product facts and conservative listing checks

This is stage 1 inside MarketPrice, for both Amazon.com and Amazon.ae. It adds structured seller evidence to the existing catalog review. It does not yet produce publish-ready copy or independently verify sources.

## Use the workflow

1. Open Listing analysis from Home, select the store and upload the catalog.
2. Confirm the worksheet, separators/encoding and mapped columns. Keep each variant's SKU unique and stored as text.
3. Expand Product facts and sources. Download the synthetic template, replace it with the exact product's specifications, then upload CSV or XLSX. Facts CSV uses UTF-8; separators can be comma, semicolon or tab. Select the correct worksheet for XLSX.
4. Review the status and source for each fact, then select the fact-review checkbox. Only confirmed facts with a source and an unambiguous SKU are eligible. Conflicting/disputed attributes remain blocked.
5. Run the review, inspect issues and claim evidence, and download the workbook. Re-run after changing evidence. Review every listing before use.

The included examples are synthetic, not supplier evidence. Uploading a source name does not prove that the source exists or is accurate; a human must inspect it. No source URLs are fetched and no uploaded data is sent to an external research or AI service by this workflow.

## Facts format

Each row describes one attribute of one product or component:

| Column | Meaning |
| --- | --- |
| fact_id | Unique reference used in claim results |
| sku | Exact text SKU from the catalog; leading zeros matter |
| subject | Component, such as `bottle` or `cap` |
| attribute | Supported attribute name below |
| value | Ungrouped numeric value, `true`/`false`, or text |
| unit | Supported metric unit for measurements; otherwise empty |
| status | `confirmed`, `unverified`, or `disputed` |
| source | Supplier/specification reference; required for confirmed facts |
| source_locator | Optional page, cell or section to locate the evidence |

Supported stored attributes: capacity, height, width, length, weight, pack_count, insulated, dishwasher_safe, leakproof, material, compatibility, product_type, brand, model and color. Attribute/status names use the exact lowercase values. Units include ml/l, mm/cm/m and g/kg. No imperial conversion is implemented in structured checks. Numeric values must be positive, finite, at most 1e12, with no more than 18 significant digits or 12 decimal places; pack_count must be an integer.

Unknown columns/attributes, malformed values, duplicate fact IDs and facts for SKUs absent from the catalog cause an error instead of silently discarding evidence. Duplicate or numeric catalog SKUs cannot support structured claims. Different confirmed values for the same SKU/component/attribute, or a disputed fact in that group, prevent support. Equivalent metric values such as 20 cm and 200 mm are not conflicts.

## What the checks establish

- A small English vocabulary recognizes insulated, dishwasher safe and leakproof assertions. Conservative explicit component wording can be compared against source-linked boolean facts. Negation, uncertainty and component ambiguity can require review.
- Explicit forms such as `Bottle height 20 cm` preserve component/attribute relationships. Swapping bottle and cap heights produces contradictions instead of matching a pooled set of measurements.
- Unreviewed/unverified facts cannot support a claim. Opposition in free-text reference specifications produces a review warning; that reference is not a structured semantic proof.
- Keyword word overlap is labeled `WORDS_PRESENT_REVIEW_REQUIRED`. It does not establish relevance, demand or factual correctness.
- Missing highlights, bullets or description trigger completeness review; whether a field is required depends on category rules not yet implemented.

`SUPPORTED_FACT` means that one recognized assertion matched the supplied, reviewed evidence under these limited rules. It does not validate the whole sentence or listing. The rule system can miss or misunderstand natural language; `Check_Coverage` and every listing summary continue to require human review. Numbers also trigger broad scope review because counts, ranges, variants and unknown units need inspection.

## Export and privacy

The workbook retains Original_Listings and adds Product_Facts, Claim_Checks and Check_Coverage. Claim rows link fact IDs; evidence rows include source/status and eligibility. The UI adds input hashes and fact-file metadata to Sources. All exported values remain literal spreadsheet cells, including formula-looking source references. Changing file/worksheet/separator/review state hides stale downloads; Clear session removes the retained report. Already downloaded files remain with the recipient.

Hosted uploads are processed on the hosting server. Use a local launch for confidential data. The feature does not fetch references, call a model or publish listings.

## Remaining stages and acceptance evidence

1. **Facts foundation — implemented:** constrained source-linked checks, import validation and conservative reporting. Synthetic regression coverage is recorded in GUIDED_WORKSPACE.md.
2. **Marketplace policy registry — pending:** dated, source-linked product-type/store/language rules. Unknown or inaccessible requirements must remain unvalidated.
3. **Keyword evidence — pending:** preserve marketplace, category, observation date, source and metric meaning for every keyword/comparable product. Keep BSR, search position, suggestions and measured demand distinct. Missing data stays unavailable; Google Ads is not a prerequisite.
4. **Constrained writing — pending:** both improvement and new-field workflows, with each factual claim linked to a product fact and each keyword justified. Reject unsupported assertions and require reviewer approval.
5. **Accuracy and outcome benchmark — pending:** held-out, human-labeled listings for claim/relevance errors plus timed seller trials. Measure US/UAE and English/Arabic separately. Code tests and public research papers do not establish this product's real-world accuracy or conversion lift.

The next implementation should not bypass these gates merely because text sounds professional. Material/compatibility semantics, pack-count assertions, Arabic understanding, current Amazon category policies, live keyword/competitor research, ranking forecasts and copy generation are not implemented in this stage.
