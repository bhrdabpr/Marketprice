# Public repository review — 2026-11-04

Reviewed public main at `6ef8ea2a81e7c1cd05181a9f28c201434c41b007` and all fetched remote history before this update. This is a maintainer review, not an external privacy audit.

- Scanned 228 reachable historical file blobs for local home paths, selected known merchant markers and common GitHub/private-key credential patterns. The only marker hit was an exclusion rule in `.gitignore`.
- No merchant-directory/workbook paths or Excel/ZIP/PDF binaries appeared in fetched remote history. Public text examples are synthetic; this does not prove that every possible confidential value could be recognized automatically.
- Visually inspected all three existing public PNGs: they show the synthetic sample workflow. They are older UI captures, not proof of current visual behavior.
- Public API listings showed one branch (`main`), no tags/releases, no issues/PRs returned by the issues endpoint, no issue/commit comments and zero downloadable Actions artifacts.
- Private workbooks, generated merchant results and the declined final screenshots remain local and excluded. No new screenshots were published.

Limits: deleted/unreachable commits, third-party clones, caches, every historic Actions log and non-repository GitHub surfaces were not exhaustively inspected. No absolute “nothing private anywhere on GitHub” guarantee is made. Historical filenames may mention an excluded sample workbook; a filename is not its contents.

## Preventing accidental publication

Run `python scripts/check_publication.py` **after staging** and before publishing. CI also checks the tracked index. The guard rejects private directories, workbook/archive files, environment files, declined screenshot filenames and selected credential/path patterns. It reports paths and categories, never matched secret values. It is a heuristic: review CSV/JSON/text contents and every newly proposed image manually. A CI rejection happens after push; local review remains essential.

Generate public Excel examples from synthetic source. Keep merchant inputs/results under ignored `private/` or outside the repository. Never attach them to issues, PRs or Actions artifacts. If sensitive information is found later, remove it from current files, assess history/copies and rotate any exposed credentials; deletion alone does not revoke a credential.
