"""Freeze the installed runtime dependency closure, excluding development tools."""

from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement

seen = {}


def visit(name):
    dist = distribution(name)
    key = dist.metadata["Name"]
    if key in seen:
        return
    seen[key] = dist.version
    for dependency in dist.requires or []:
        req = Requirement(dependency)
        if req.marker is None or req.marker.evaluate({"extra": ""}):
            visit(req.name)


for root in ["streamlit", "openpyxl", "pydantic", "defusedxml", "pip"]:
    visit(root)
Path("requirements.lock").write_text(
    "".join(f"{k}=={v}\n" for k, v in sorted(seen.items(), key=lambda x: x[0].lower()))
)
