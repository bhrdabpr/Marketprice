# Guided seller workspace

MarketPrice remains one application and repository. Home presents seven tasks, with a return-to-tools button and English/Persian navigation. Pricing and campaign analysis share the existing financial engine and session source; campaign analysis exposes its scenario table and workbook directly.

## Listing review preview

1. Choose Amazon.com or Amazon.ae, then upload Excel/CSV or try the clearly labeled synthetic example.
2. Review the worksheet, encoding/separator and column mapping. Map SKU, title, highlights, bullets, description, keywords and reference facts. Confirm the source of those facts before factual checks.
3. Optionally upload a separate product-facts CSV/XLSX using the downloadable template. Review each fact status and source. Run checks for explicit quantity conflicts, selected source-linked claims, missing/duplicate identifiers, duplicate content, vague wording and keyword evidence. Generic/unbranded identities do not require adding a brand word to the title.
4. Review findings and download the workbook. Sources include input SHA-256, mapping and chosen store. Original mapped text is retained; exported values are literal cells, not executable formulas.

This is a deterministic preview, not a production Amazon optimizer. Lexical overlap is not proof of semantic relevance; synonyms and context need human review. The store selector does not validate Amazon category rules. No keyword volume, BSR, rank, traffic prediction, Google Ads connection, live competitor research, AI writing or direct listing publication is implemented. Every listing remains marked as requiring review. No fabricated demand evidence is substituted for unavailable data.

## Financial guidance and session behavior

Pricing requires column/unit review and explicit currency confirmation. Blank mapped costs remain unknown until corrected; session corrections are included in the exported audit. Percentage commission and fixed commission are distinct fields. A hypothetical campaign based on a proposed price stays provisional.

The pricing source, primary financial settings and confirmations survive navigation to Home and back. Changing calculation assumptions invalidates stale output. Changing listing market, mapping, reference confirmation, facts file or fact confirmation hides the previous listing download until rerun. Clear session data removes retained source and results; existing downloads are unaffected. Other tools may require reselecting uploads after navigation.

Campaign outputs assess discount feasibility and contribution under supplied costs. They do not forecast sales. The hidden-cost scenario covers specified incremental costs, not a complete returns/accounting model.

## Privacy and file handling

Uploaded data is processed in the current server session; these workflows make no external research or AI calls. Hosted use therefore sends files to the hosting server. Use local launch for confidential catalogs. XLSX parsing does not execute formulas or links. Existing size/row limits and publication checks remain in force. Only synthetic examples belong in this public repository.

## Validation for this change

- 287 automated tests passed locally, including bilingual tool navigation, retained pricing settings/source, stale report prevention, store selection, XLSX/CSV parsing, leading-zero identifiers, formula-safe exports and listing findings.
- Ruff and mypy passed for application code, tests and scripts (mypy: application and package).
- Chromium upload/calculation/download tests reconciled the 117.65 USD golden price, settlement scenario, actual-profit demo and two-report comparison.
- Desktop and narrow-screen visual inspection covered Home and the listing review; the synthetic listing example reached findings and download.

These checks use synthetic inputs and establish implemented behavior, not market performance, Amazon certification or an independent security audit. Existing library deprecation warnings remain.

## Structured product facts: stage 1

The facts upload adds an evidence foundation to the existing listing review. See [the facts guide](LISTING_FACTS.md) for its schema, supported checks, limits and the remaining delivery stages.

Validation for this addition: 331 automated tests passed locally, with Ruff and mypy (45 source files) clean. New cases cover source requirements, leading-zero identity protection, conflicting/disputed facts, negation and uncertain wording, component dimensions, equivalent metric units, literal exports, CSV/XLSX uploads and stale-report prevention. These synthetic tests establish code behavior; they are not a measured accuracy benchmark on real Amazon listings. The original 287-test count above records the earlier guided-workspace release.
