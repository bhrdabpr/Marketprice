"""Start local Streamlit, wait for readiness, then open the browser."""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

port = os.environ.get("MARKETPRICE_PORT", "8501")
url = f"http://127.0.0.1:{port}"
process = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        port,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
)
try:
    for _ in range(100):
        if process.poll() is not None:
            raise SystemExit(process.returncode)
        try:
            with urllib.request.urlopen(url + "/_stcore/health", timeout=1) as response:
                if response.status == 200:
                    if "--no-browser" not in sys.argv:
                        webbrowser.open(url)
                    print(f"MarketPrice ready at {url}", flush=True)
                    break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    else:
        raise RuntimeError("Application did not become ready")
    raise SystemExit(process.wait())
except KeyboardInterrupt:
    pass
finally:
    process.terminate()
    process.wait(timeout=10)
