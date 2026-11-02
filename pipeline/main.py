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

    sources = C.load_secret_sources()
    fetched = C.collect_all(sources)

    raw_uris = []
    for sid, res in fetched.items():
        if res["ok"]:
            raw_uris.extend(C.extract_uris(res["text"]))

    canon = [c for c in (N.canonical(u) for u in raw_uris) if c]
    uniq, _ = N.dedupe(canon)

    rescued = BK.resurrect(bank, set(uniq))
    if rescued:
        uniq.extend(rescued)

    if not V.engines_available():
        print("Engines not available. Exiting safely without overwriting.")
        return 1

    probe_list, _ = V.tcp_prefilter(uniq)
    probe_list = BK.prioritized(probe_list, bank)

    prev_res_file = DIST / "results.json"
    prev_results = {}
    if prev_res_file.exists():
        try:
            prev_results = json.loads(prev_res_file.read_text("utf-8"))
        except Exception:
            pass

    history, summary, per_node = V.validate_all(probe_list, prev_results)

    alive_now = summary.get("alive", 0)
    last_alive = bank.get("meta", {}).get("last_alive")

    # Sanity Gate: جلوگیری از تخریب خروجی در صورت افت ناگهانی ناشی از قطعی رانر
    if last_alive and last_alive > 50 and alive_now < (last_alive * 0.25):
        print(f"Sanity Gate Triggered! alive_now={alive_now} vs last_alive={last_alive}. Aborting.")
        return 1

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

    P.publish_outputs(DIST, rows, uniq)
    (DIST / "bank.json").write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIST / "results.json").write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

    gold_count = sum(1 for r in rows if r["alive"] and r["tier"] == "gold")
    P.publish_telegram(alive_now, gold_count)

    print(f"Run completed successfully: {alive_now} alive, {gold_count} gold.")
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
