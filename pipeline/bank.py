from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

BANK_VERSION = 1
BANK_TTL_HOURS = float(os.environ.get("BANK_TTL", "36"))
RESCUE_MIN_STREAK = 3
RESCUE_MAX = 1000


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def empty_bank() -> dict:
    return {"version": BANK_VERSION, "entries": {}, "meta": {"updated_at": _now()}}


def load_bank(path: str) -> dict:
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict) and "entries" in data:
                    return data
        except Exception:
            pass
    return empty_bank()


def bank_good_hashes(bank: dict) -> dict[str, int]:
    out = {}
    for h, e in (bank.get("entries") or {}).items():
        s = int(e.get("streak", 0) or 0)
        if s >= 1:
            out[h] = s
    return out


def prioritized(uris: list[str], bank: dict) -> list[str]:
    good = bank_good_hashes(bank)
    if not good or not uris:
        return uris
    head, tail = [], []
    for i, u in enumerate(uris):
        h = hashlib.sha256(u.encode()).hexdigest()[:16]
        s = good.get(h)
        if s:
            head.append((-s, i, u))
        else:
            tail.append(u)
    head.sort()
    return [u for _, _, u in head] + tail


def resurrect(bank: dict, collected_uris: set[str]) -> list[str]:
    collected_hashes = {hashlib.sha256(u.encode()).hexdigest()[:16] for u in collected_uris}
    cands = []
    for h, e in (bank.get("entries") or {}).items():
        uri = e.get("uri")
        if not uri or h in collected_hashes:
            continue
        s = int(e.get("streak", 0) or 0)
        if s >= RESCUE_MIN_STREAK:
            cands.append((-s, uri))
    cands.sort()
    return [u for _, u in cands[:RESCUE_MAX]]


def merge_run(bank: dict, results: dict, alive_hashes: set[str], alive_now: int | None, uris: dict[str, str]) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    prev = bank.get("entries") or {}
    entries = {}
    for h in set(prev) | set(results):
        old = prev.get(h, {})
        res = results.get(h, {})
        if h in alive_hashes:
            streak = int(old.get("streak", 0)) + 1
            entry = {
                "streak": streak,
                "fails": 0,
                "last_ok": _now(),
                "ms": res.get("latency_ms") or old.get("ms"),
                "uri": uris.get(h) or old.get("uri")
            }
            entries[h] = entry
        elif h in prev:
            entries[h] = {**old, "streak": 0, "fails": int(old.get("fails", 0)) + 1}

    kept = {}
    for h, e in entries.items():
        lo = e.get("last_ok")
        if lo:
            try:
                age_h = (now - dt.datetime.fromisoformat(lo)).total_seconds() / 3600.0
                if age_h <= BANK_TTL_HOURS:
                    kept[h] = e
            except Exception:
                pass
    bank["entries"] = kept
    bank["meta"] = {
        "updated_at": _now(),
        "last_alive": alive_now,
        "prev_alive": bank.get("meta", {}).get("last_alive")
    }
    return bank
