from __future__ import annotations

import base64
import os
from pathlib import Path
import urllib.request
import json
from . import exports as E


def write_b64(path: Path, text: str) -> None:
    path.write_bytes(base64.b64encode(text.encode("utf-8")))


def publish_outputs(dist: Path, rows: list[dict], all_unique: list[str]) -> None:
    dist.mkdir(exist_ok=True, parents=True)
    alive = [r for r in rows if r["alive"]]

    (dist / "all.txt").write_text("\n".join(all_unique) + "\n", encoding="utf-8")
    write_b64(dist / "all.b64", "\n".join(all_unique) + "\n")

    val_text = "\n".join(r["uri"] for r in alive) + "\n"
    (dist / "validated.txt").write_text(val_text, encoding="utf-8")
    write_b64(dist / "validated.b64", val_text)

    gold_uris = [r["uri"] for r in alive if r["tier"] == "gold"]
    (dist / "gold.txt").write_text("\n".join(gold_uris) + "\n", encoding="utf-8")
    write_b64(dist / "gold.b64", "\n".join(gold_uris) + "\n")

    (dist / "clash.yaml").write_text(E.to_mihomo(alive), encoding="utf-8")
    (dist / "singbox.json").write_text(E.to_singbox(alive), encoding="utf-8")


def publish_telegram(alive_count: int, gold_count: int) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    msg = (
        f"⚡️ مخزن کانفیگ‌های تست‌شده و پایدار V2Pool\n"
        f"✅ گره‌های فعال: {alive_count}\n"
        f"🥇 رده طلا (ویژه): {gold_count}\n"
        f"🕒 بروزرسانی منظم و پیوسته\n"
        f"🌐 دریافت اشتراک از مخزن اصلی"
    )
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": msg}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
