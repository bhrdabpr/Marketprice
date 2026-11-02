# Existing system audit — 2026-11-02

The supplied workspace contained only empty `work/` and `outputs/` directories. There was no Git repository, workbook, Python program, configuration, or prior test evidence. The only supplied source was the mission text attachment. No predecessor formulas or compatibility claims could be verified.

Decision: independent clean implementation. No prior business data was modified. Preserve identifiers as text; numeric Excel SKUs are rejected because lost leading zeros cannot be reconstructed safely. Preserve all imported rows, including blank/invalid rows, in the calculation and error output. Column aliases and explicit mapping support migration without guessing costs. Workbook formulas are not evaluated on import; financial formula cells fail numeric validation.

Initial risks addressed: silent blanks, mixed tax/revenue, hardcoded fees, unsafe discounts, cross-row leakage, numeric precision, malformed archives and spreadsheet formula injection. Tax/fee schedules remain user-owned configuration, not a legal determination.
