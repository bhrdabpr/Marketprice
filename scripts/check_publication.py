"""Check tracked publication files. Heuristic guard, not a confidentiality certification."""

import re
import subprocess
from pathlib import PurePosixPath


def violations(path: str, data: bytes) -> list[str]:
    p = PurePosixPath(path)
    reasons = []
    if any(part.lower() in {"private", "merchant-data"} for part in p.parts):
        reasons.append("private directory")
    if p.suffix.lower() in {".xlsx", ".xls", ".xlsm", ".zip"}:
        reasons.append("binary workbook/archive: publish a synthetic generator instead")
    if p.name == ".env" or p.name.startswith(".env.") and p.name != ".env.example":
        reasons.append("environment file")
    if p.name.startswith("screenshot-final-"):
        reasons.append("unapproved local screenshot")
    patterns = {
        "local home path": rb"/" + rb"Users/[^\s\"<>]+",
        "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "GitHub credential": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    }
    if b"\x00" not in data:
        reasons.extend(label for label, pattern in patterns.items() if re.search(pattern, data))
    return reasons


def main() -> int:
    entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"]).split(b"\x00")
    failed = []
    count = 0
    for entry in filter(None, entries):
        metadata, path = entry.split(b"\t", 1)
        _, sha, stage = metadata.split()
        if stage != b"0":
            failed.append("Unresolved index entry")
            continue
        count += 1
        reasons = violations(path.decode(), subprocess.check_output(["git", "cat-file", "blob", sha]))
        if reasons:
            failed.append(f"{path.decode()}: {', '.join(reasons)}")
    print("\n".join(failed) if failed else f"Publication guard passed: {count} tracked files.")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
