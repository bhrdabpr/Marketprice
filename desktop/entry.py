"""Experimental packaged launcher. Not a signed or customer-ready release."""

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def serve(port: str) -> None:
    from streamlit.web import cli

    os.chdir(root())
    sys.argv = [
        "streamlit", "run", str(root() / "app.py"), "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        f"--server.port={port}", "--server.headless=true", "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(cli.main())


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--serve":
        serve(sys.argv[2])
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = str(listener.getsockname()[1])
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--serve", port]
    else:
        command = [sys.executable, __file__, "--serve", port]
    process = subprocess.Popen(command)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError("MarketPrice failed to start; see the terminal output.")
            try:
                with urllib.request.urlopen(url + "/_stcore/health", timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        print(f"MarketPrice is ready at {url}. Close this window to stop it.", flush=True)
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.2)
        else:
            raise RuntimeError("MarketPrice did not become ready.")
        process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
