# Security policy

Treat seller costs and pricing as confidential. Report vulnerabilities privately to the repository maintainer using GitHub's private vulnerability reporting once the repository owner enables it. Do not publish customer workbooks or exploit data in public issues. There is no invented support address or response-time guarantee.

Controls implemented: 25 MiB CSV / 50 MiB XLSX upload limits, bounded archive entry count/expanded bytes, 100,000 rows and 80 columns, explicit input schema, no formula evaluation, no macros; external-link workbooks only in explicit cached-value mode without fetching links, literal spreadsheet text, defusedxml dependency, no product-data API calls, disabled Streamlit telemetry, localhost launch, generic UI exception boundary and no hardcoded secrets.

Dependency versions and scan evidence are in requirements files and reports/dependency-audit.json. A clean vulnerability database result is not proof of absence of vulnerabilities. Re-run before deployment. Original code is not independently penetration-tested.

The UI is intended for a trusted local or authenticated private environment. Configure TLS, authentication, rate limits, protected temporary storage and resource limits before remote use. Streamlit sessions and OS temporary storage are not a secure multi-tenant storage system. Do not expose the app publicly without an appropriate deployment review.

Never add untrusted code execution, Excel formula evaluation, pickle loading or arbitrary URL fetching to import paths. New fee rules must remain declarative. Review third-party dependencies, lock changes and upload boundary tests together.
