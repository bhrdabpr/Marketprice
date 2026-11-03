# Experimental Excel button companion

The companion calls the same Python engine on the active sheet and adds a new results sheet. It does not upload the workbook, overwrite source cells, automatically save, or publish marketplace prices.

**Status:** matrix validation and calculation are tested; the native Excel button has not yet been end-to-end certified. This is an optional local integration, not a packaged Microsoft Office Store add-in.

## One-time setup

1. Use desktop Excel on macOS or Windows and the project's Python environment.
2. In that environment, install `python -m pip install -e '.[excel]'` and run `xlwings addin install`.
3. Follow xlwings settings to select this environment's Python interpreter; the `marketprice` package must be importable there.
4. In MarketPrice's web app, map one example of your workbook, confirm units and costs, then **Save reusable setup**.
5. Save that JSON beside the workbook with the same base name: `Catalog.xlsx` → `Catalog.marketprice.json`.
6. Import `MarketPrice.bas` into a macro-enabled workbook, then assign `AnalyzeWithMarketPrice` to a form button named **Analyze with MarketPrice**. Use the xlwings add-in's RunPython reference as documented below. The source macro is intentionally small and reviewable.
7. Select the original product sheet and click the button. Its first used row must contain distinct headers, including mapped purchase cost; blank rows remain row errors. Results appear in a new `MP Results …` sheet. Choose whether to save them.

A changed header signature stops the run and asks for mapping review. Unknown costs remain provisional. Re-running on a results sheet is blocked. For another source sheet with different headers, save its own reviewed setup first. This version uses one primary target margin from the saved setup; the web app exposes the extra scenario controls.

The workbook contains a macro only if you choose to install this optional button. The normal web uploader continues to reject macro-enabled files. Do not weaken Excel's macro security globally.

Official setup references: [xlwings RunPython](https://docs.xlwings.org/en/latest/vba.html), [xlwings installation](https://docs.xlwings.org/en/latest/installation.html), [xlwings add-in settings](https://docs.xlwings.org/en/latest/addin.html).
