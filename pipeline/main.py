from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from . import bank as BK
from . import collect as C
from . import normalize as N
from . import publish as P
from . import score as S
from . import validate as V

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def run_pipeline() -> int:
    DIST.mkdir(exist_ok=True, parents=True)
    bank_path = str(DIST / "bank.json")
    bank = BK.load_bank(bank_path)

    cycle_count = int(bank.get("meta", {}).get("cycle_count", 0)) + 1
    bank.setdefault("meta", {})["cycle_count"] = cycle_count

    sources = C.load_secret_sources()
    print(f"[*] Step 1: Loaded {len(sources)} sources from configuration.")
    if not sources:
        print("[!] Warning: No sources found. Check SOURCES_RAW secret.")

    fetched = C.collect_all(sources)

    raw_uris = []
    for sid, res in fetched.items():
        if res["ok"]:
            uris = C.extract_uris(res["text"])
            if not uris:
                uris = N.try_b64_blob(res["text"])
            raw_uris.extend(uris)
            print(f"    - {sid}: fetched {len(uris)} URIs")
        else:
            print(f"    - {sid}: FAILED ({res.get('error')})")

    print(f"[*] Step 2: Total raw URIs collected: {len(raw_uris)}")

    canon = [c for c in (N.canonical(u) for u in raw_uris) if c]
    uniq, _ = N.dedupe(canon)
    print(f"[*] Step 3: Canonical & Unique URIs: {len(uniq)}")

    rescued = BK.resurrect(bank, set(uniq))
    if rescued:
        uniq.extend(rescued)
        print(f"[*] Bank Resurrected: {len(rescued)} proven configs added.")

    if not V.engines_available():
        print("[!] Engines not available. Exiting safely.")
        return 1

    probe_list, pre = V.tcp_prefilter(uniq)
    print(f"[*] Step 4: TCP Prefilter: {pre.get('tcp_open', 0)} open, {pre.get('tcp_closed', 0)} closed.")
    probe_list = BK.prioritized(probe_list, bank)

    prev_res_file = DIST / "results.json"
    prev_results = {}
    if prev_res_file.exists():
        try:
            prev_results = json.loads(prev_res_file.read_text("utf-8"))
        except Exception:
            pass

    print(f"[*] Step 5: Testing {len(probe_list)} endpoints with dual-engine ...")
    history, summary, per_node = V.validate_all(probe_list, prev_results)

    alive_now = summary.get("alive", 0)
    print(f"[*] Step 6: Test Results: {alive_now} alive, {summary.get('dead', 0)} dead.")

    rows = []
    bank_entries = bank.get("entries", {})
    for uri in uniq:
        h = hashlib.sha256(uri.encode()).hexdigest()[:16]
        info = per_node.get(uri)
        alive = bool(info and info["alive"])
        ms = info["latency_ms"] if alive else None
        rate = info["success_rate"] if info else 0.0
        streak = int(bank_entries.get(h, {}).get("streak", 0))
        sc = S.total(ms, rate, streak, uri)
        rows.append({
            "uri": uri, "hash": h, "score": sc,
            "tier": S.tier(sc) if alive else None,
            "alive": alive, "latency_ms": ms
        })

    rows.sort(key=lambda r: -r["score"])

    alive_hashes = {info["hash"] for info in per_node.values() if info.get("alive")}
    uris_by_hash = {hashlib.sha256(u.encode()).hexdigest()[:16]: u for u in uniq}
    bank = BK.merge_run(bank, history, alive_hashes, alive_now, uris_by_hash)

    # انتشار هر ۴ فایل اصلی و کلاینت‌ها
    P.publish_outputs(DIST, rows, uniq)
    (DIST / "bank.json").write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIST / "results.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

    gold_count = sum(1 for r in rows if r["alive"] and r["tier"] == "gold")
    silver_count = sum(1 for r in rows if r["alive"] and r["tier"] == "silver")

    # انتشار استاندارد تلگرام همراه با دکمه‌های شیشه‌ای
    P.publish_telegram(alive_now, gold_count, silver_count)

    print(f"[*] Done: Published {alive_now} alive nodes (Gold: {gold_count}, Silver: {silver_count}).")
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
