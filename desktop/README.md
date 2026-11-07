# Experimental desktop build

This is a developer prototype, not an installer or customer release. It launches the existing Streamlit UI on a random loopback port and opens a browser. Keep its console open; Ctrl+C stops the server. It does not provide user authentication or protect against other software running as the same operating-system user.

On macOS ARM64, one local build was exercised with synthetic uploads and exports. Fresh-machine installation, clean shutdown on all exit paths, signed distribution, other architectures and Windows have not been verified. Do not distribute this build as secure or customer-ready.

Build on the target OS from the repository root with Python 3.13:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock pyinstaller==6.22.3
PYTHONPATH=. .venv/bin/pyinstaller --noconfirm --clean MarketPrice.spec
```

The output is `dist/MarketPrice/MarketPrice` on macOS. Run it from a terminal; Ctrl+C stops it. On Windows the commands and resulting executable have not yet been tested. Build dependencies are version-pinned at the top level only; the PyInstaller dependency closure is not locked or hash-verified. Build only from reviewed source in a trusted environment.

For tests, `MarketPrice --serve 8505` starts the prototype server without opening a browser; `MARKETPRICE_TEST_PORT=8505 python scripts/browser_session_isolation.py` exercises it locally. Keep test files synthetic.

Before a release, provide a normal graphical launcher and reliable quit behavior, address startup time, verify clean installation and offline behavior, test each supported platform, and sign and notarize as appropriate. See [hosting and downloads](../HOSTING_AND_DOWNLOADS.md).
