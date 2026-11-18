"""Portable review history and optional server-owned team storage."""

import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from .quick_review import TASKS

FORMAT = "marketprice.project.v1"
LIMIT = 32 * 1024**2
ROLES = {"viewer", "editor", "manager"}


def encode(value):
    return json.dumps(value, ensure_ascii=False, default=str, allow_nan=False, separators=(",", ":")).encode()


def revision(task, name, rows, report):
    payload = {"task": task, "source": name, "inputs": rows, "report": report}
    payload["fingerprint"] = hashlib.sha256(encode(payload)).hexdigest()
    payload["time"] = datetime.now(UTC).isoformat(timespec="seconds")
    return json.loads(encode(payload))


def export_project(history):
    data = encode({"format": FORMAT, "history": history})
    if len(data) > LIMIT:
        raise ValueError("Project exceeds 32 MiB. Start a separate project for the next report.")
    return data


def restore_project(data):
    if len(data) > LIMIT:
        raise ValueError("Project exceeds 32 MiB.")
    try:
        obj = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if obj["format"] != FORMAT or not isinstance(obj["history"], list):
            raise ValueError
        for rev in obj["history"]:
            if (rev["task"] not in TASKS or not isinstance(rev["source"], str)
                    or not isinstance(rev["inputs"], list) or not isinstance(rev["report"], dict)
                    or not isinstance(rev["time"], str) or not isinstance(rev.get("author", ""), str)):
                raise ValueError
            for table in [rev["inputs"], *rev["report"].values()]:
                if not isinstance(table, list) or any(not isinstance(row, dict) for row in table):
                    raise ValueError
            fields = {k: rev[k] for k in ("task", "source", "inputs", "report")}
            if rev["fingerprint"] != hashlib.sha256(encode(fields)).hexdigest():
                raise ValueError
        return obj["history"]
    except (ValueError, KeyError, TypeError, RecursionError) as exc:
        raise ValueError("This file is not a valid MarketPrice project.") from exc


def next_revision(history, rev):
    previous = next((r for r in reversed(history) if r["task"] == rev["task"]), None)
    return previous is None or previous["fingerprint"] != rev["fingerprint"]


def changes(before, after):
    def indexed(rows):
        index = {}
        for row in rows:
            keys = {str(k).strip().lower(): v for k, v in row.items()}
            sku = keys.get("sku") or keys.get("asin") or keys.get("کد کالا")
            if not isinstance(sku, str) or not sku.strip() or sku.strip() in index:
                return None
            index[sku.strip()] = row
        return index

    old, new = indexed(before), indexed(after)
    if old is None or new is None:
        return [{"Check": "A unique text SKU or ASIN is required on every row to compare these files."}]
    result = []
    for sku in sorted(old.keys() | new.keys()):
        if sku not in new or sku not in old:
            result.append({"SKU": sku, "Change": "Only in earlier input" if sku not in new else "Only in later input"})
        else:
            for key in sorted(old[sku].keys() | new[sku].keys()):
                a, b = old[sku].get(key), new[sku].get(key)
                if a != b:
                    result.append({"SKU": sku, "Field": key, "Earlier": a, "Later": b})
    return result


def sign_in(members, user, token):
    member = members.get(user, {})
    expected = member.get("token_sha256", "")
    match = hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), expected)
    if match and member.get("role") in ROLES and token:
        return member["role"]
    raise ValueError("The name or access key did not match.")


def team_history(path, role, *, new=None, user=""):
    if role not in ROLES or (new is not None and (role == "viewer" or not user)):
        raise PermissionError("Your account can view saved reports.")
    with closing(sqlite3.connect(path, timeout=10)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, data TEXT NOT NULL)")
        if new is not None:
            db.execute("BEGIN IMMEDIATE")
        records = [json.loads(row[0]) for row in db.execute("SELECT data FROM reviews ORDER BY id")]
        if new is not None and next_revision(records, new):
            saved = dict(new, author=user)
            export_project([*records, saved])
            db.execute("INSERT INTO reviews(data) VALUES (?)", (encode(saved).decode(),))
            records.append(saved)
        return records

