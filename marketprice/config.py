import json
from pathlib import Path

from .models import Profile


def load_profiles(path: Path | None = None) -> dict[str, Profile]:
    raw = json.loads((path or Path(__file__).with_name("rules") / "profiles.json").read_text())
    profiles = [Profile.model_validate(p) for p in raw]
    if len({p.id for p in profiles}) != len(profiles):
        raise ValueError("duplicate profile IDs")
    return {p.id: p for p in profiles}
