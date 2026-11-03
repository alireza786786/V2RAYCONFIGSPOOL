from __future__ import annotations

import base64
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

from . import exports as E

REPO_RAW_URL = "https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main"


def write_b64(path: Path, text: str) -> None:
    path.write_bytes(base64.b64encode(text.encode("utf-8")))


def to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    jy = 979 if gy > 1600 else 0
    gy -= 1600 if gy > 1600 else 621
    gy2 = (gm > 2) and (gy + 1) or gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    jy += (days - 1) // 365
    if days > 0:
        days = (days - 1) % 365
    jm = (days < 186) and (1 + (days // 31)) or (7 + ((days - 186) // 30))
    jd = 1 + ((days < 186) and (days % 31) or ((days - 186) % 30))
    return jy, jm, jd


def remark_uri(uri: str, ping_ms: float | None, tier_name: str | None = None) -> str:
    base = uri.split("#", 1)[0]
    ms_txt = f"{int(round(ping_ms))}ms" if (ping_ms and ping_ms > 0) else "Node"
    if tier_name == "gold":
        tag = f"V2Pool-GOLD-{ms_txt}"
    elif tier_name == "silver":
        tag = f"V2Pool-SILVER-{ms_txt}"
    else:
        tag = f"V2Pool-{ms_txt}"
    return f"{base}#{tag}"


def publish_outputs(dist: Path, rows: list[dict], all_unique: list[str]) -> None:
    dist.mkdir(exist_ok=True, parents=True)
    alive = [r for r in rows if r["alive"]]

    # 1. فایل همه کانفیگ‌ها
    all_branded = [remark_uri(u, None) for u in all_unique]
    all_txt = "\n".join(all_branded) + "\n"
    (dist / "all.txt").write_text(all_txt, encoding="utf-8")
    write_b64(dist / "all.b64", all_txt)

    # 2. فایل پایدار (تمام زنده‌ها)
    val_branded = [remark_uri(r["uri"], r.get("latency_ms")) for r in alive]
    val_txt = "\n".join(val_branded) + "\n"
    (dist / "validated.txt").write_text(val_txt, encoding="utf-8")
    write_b64(dist / "validated.b64", val_txt)

    # 3. فایل رده طلا
    gold_rows = [r for r in alive if r["tier"] == "gold"]
    gold_branded = [remark_uri(r["uri"], r.get("latency_ms"), "gold") for r in gold_rows]
    gold_txt = "\n".join(gold_branded) + "\n"
    (dist / "gold.txt").write_text(gold_txt, encoding="utf-8")
    write_b64(dist / "gold.b64", gold_txt)

    # 4. فایل رده نقره
    silver_rows = [r for r in alive if r["tier"] == "silver"]
    silver_branded = [remark_uri(r["uri"], r.get("latency_ms"), "silver") for r in silver_rows]
    silver_txt = "\n".join(silver_branded) + "\n"
    (dist / "silver.txt").write_text(silver_txt, encoding="utf-8")
    write_b64(dist / "silver.b64", silver_txt)

    # 5. خروجی کلاینت‌ها
    (dist / "clash.yaml").write_text(E.to_mihomo(alive), encoding="utf-8")
    (dist / "singbox.json").write_text(E.to_singbox(alive), encoding="utf-8")


def publish_telegram(alive_count: int, gold_count: int, silver_count: int) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    # وقت تهران (UTC + 3:30)
    tehran_dt = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3, minutes=30)
    jy, jm, jd = to_jalali(tehran_dt.year, tehran_dt.month, tehran_dt.day)
    jalali_str = f"{jy}/{jm:02d}/{jd:02d} - {tehran_dt.strftime('%H:%M')}"

    # الگوی ۵ خطی استاندارد Goodbaye
    msg = (
        f"🛰 <b>پایگاه کانفیگ‌های تست‌شده و پایدار V2Pool</b>\n"
        f"📅 آخرین پایش: <code>{jalali_str}</code>\n"
        f"📊 وضعیت شبکه: <b>{alive_count:,}</b> گره فعال و پاسخ‌گو\n"
        f"🏅 تفکیک کیفیت: <b>{gold_count} طلا</b> | <b>{silver_count} نقره</b>\n"
        f"⚡️ اتصال هوشمند: ترافیک داخلی ایران کاملاً مستقیم (DIRECT)"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "🥇 اشتراک رده طلا (ویژه)", "url": f"{REPO_RAW_URL}/gold.txt"},
                {"text": "🥈 اشتراک رده نقره", "url": f"{REPO_RAW_URL}/silver.txt"}
            ],
            [
                {"text": "🔰 اشتراک کل گره‌های سالم", "url": f"{REPO_RAW_URL}/validated.txt"},
                {"text": "📱 اشتراک کلش (Clash)", "url": f"{REPO_RAW_URL}/clash.yaml"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
        "disable_web_page_preview": True
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=12)
        print("[Telegram] Published message with 4 inline buttons successfully.")
    except Exception as exc:
        print(f"[Telegram] Failed to send message: {exc}")
