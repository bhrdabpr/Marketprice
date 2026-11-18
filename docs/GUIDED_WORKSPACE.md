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

Uploaded data is processed in the current server session. Reading public product URLs sends the ASIN to the selected Amazon store over HTTPS. Saved HTML is parsed as text on the server. Hosted use therefore sends files to the hosting server. Use local launch for confidential catalogs. XLSX parsing does not execute formulas or links. Existing size/row limits and publication checks remain in force. Only synthetic examples belong in this public repository.

## Validation for this change

- 287 automated tests passed locally, including bilingual tool navigation, retained pricing settings/source, stale report prevention, store selection, XLSX/CSV parsing, leading-zero identifiers, formula-safe exports and listing findings.
- Ruff and mypy passed for application code, tests and scripts (mypy: application and package).
- Chromium upload/calculation/download tests reconciled the 117.65 USD golden price, settlement scenario, actual-profit demo and two-report comparison.
- Desktop and narrow-screen visual inspection covered Home and the listing review; the synthetic listing example reached findings and download.

These checks use synthetic inputs and establish implemented behavior, not market performance, Amazon certification or an independent security audit. Existing library deprecation warnings remain.

## Structured product facts: stage 1

The facts upload adds an evidence foundation to the existing listing review. See [the facts guide](LISTING_FACTS.md) for its schema, supported checks, limits and the remaining delivery stages.

Validation for this addition: 331 automated tests passed locally, with Ruff and mypy (45 source files) clean. New cases cover source requirements, leading-zero identity protection, conflicting/disputed facts, negation and uncertain wording, component dimensions, equivalent metric units, literal exports, CSV/XLSX uploads and stale-report prevention. These synthetic tests establish code behavior; they are not a measured accuracy benchmark on real Amazon listings. The original 287-test count above records the earlier guided-workspace release.

## Quick review and project history

Choose a service on Home and add an Excel workbook or UTF-8 CSV. The selected sheet runs automatically. For Amazon listings you can also paste up to 20 full Amazon.com or Amazon.ae product links and choose **Read links**. If the site cannot supply a page, the source table records the reason. Text PDFs with a clearly separated table are supported. For scanned pages or complex layouts, use the original spreadsheet.

| Service | What the answer measures |
| --- | --- |
| Pricing | Price floor using supplied costs and target margin. Without a target, the floor covers the supplied costs at break-even. Review omitted fees and taxes. |
| Profit | Gross margin and markup use purchase cost and selling price. Unit contribution uses the pricing engine and supplied fees. ROI requires net profit and invested capital on the same time and currency basis. |
| Campaign | CTR is clicks divided by impressions. Conversion uses attributed orders divided by clicks. Cost per sale here means spend per attributed order. ROAS uses attributed sales divided by spend. Each row must use one currency and reporting period. |
| Storage | Units stored × monthly storage fee per unit × months stored. Use separate rows when the inventory or rate changes. |
| Listing | Review the supplied title, bullets, description and keywords. Independent product facts and measured search demand are separate evidence. |

The dashboard saves each quick review with its source name, parsed input rows, answers and time. Select an earlier review to read it. Compare successive inputs for a service by unique text SKU or ASIN. Use **Download whole project** to keep this history between private sessions, and **Open a saved project** to return to it. The JSON file contains seller data in plain text. Original PDF pages, workbook formatting, other worksheets and detailed-tool sessions are outside this export. The current limit is 10,000 rows per quick review and 32 MiB per project.

### Optional shared project

A private installation can save reviews to one SQLite database on a persistent disk. The standard library provides the database. Configure the path outside the repository and the web-served directory. Configure members in the hosting platform's Streamlit secrets, or in a private local secrets file. Each editor or manager adds a named, timestamped revision. A viewer can read the dashboard and compare product changes. A manager can also download the whole project.

```toml
[team_project]
database = "/private-data/marketprice/team.sqlite3"

[team_project.members.seller]
role = "editor"
token_sha256 = "<SHA-256 digest of this member's random access key>"
```

The server operator creates the directory with private permissions. Generate one long random key per member using a password manager, give it to that member privately, and store its lowercase SHA-256 digest in the configuration. Supported roles are viewer, editor and manager. Serve a shared installation over HTTPS. Back up the SQLite file with SQLite's backup mechanism. Anyone who receives an exported file can read or copy its contents. Keep seller files and access settings outside public GitHub.
