from __future__ import annotations

import base64
import bisect
import datetime as dt
import gzip
import hashlib
import io
import ipaddress
import json
import os
import socket
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from . import exports as E

REPO_RAW_URL = "https://raw.githubusercontent.com/alireza786786/V2RAYCONFIGSPOOL/main"

COUNTRY_NAMES_FA = {
    "DE": "آلمان", "US": "آمریکا", "FR": "فرانسه", "NL": "هلند",
    "GB": "انگلیس", "UK": "انگلیس", "FI": "فنلاند", "TR": "ترکیه",
    "SG": "سنگاپور", "CA": "کانادا", "PL": "لهستان", "RU": "روسیه",
    "AE": "امارات", "IR": "ایران", "SE": "سوئد", "CH": "سوئیس",
    "IT": "ایتالیا", "ES": "اسپانیا", "AT": "اتریش", "JP": "ژاپن",
    "KR": "کره‌جنوبی", "IN": "هند", "RO": "رومانی", "BG": "بلغارستان",
    "NO": "نروژ", "DK": "دانمارک", "BE": "بلژیک", "HK": "هنگ‌کنگ"
}

ASN_DC_MAP = {
    24940: "Hetzner", 13335: "Cloudflare", 16276: "OVH", 14061: "DigitalOcean",
    20473: "Vultr", 8075: "Microsoft", 15169: "Google", 16509: "Amazon",
    31898: "Oracle", 51167: "Contabo", 212238: "Datacamp", 200019: "Alexhost",
    202422: "G-Core", 58224: "TCI", 197207: "MCI", 44244: "Irancell", 43395: "Shatel"
}

_GEO_TABLE = None
_IP_CACHE: dict[str, str] = {}


def _get_geo_table() -> dict | None:
    global _GEO_TABLE
    if _GEO_TABLE is not None:
        return _GEO_TABLE
    try:
        from . import geo
        _GEO_TABLE = geo.load_table()
        if _GEO_TABLE:
            return _GEO_TABLE
    except Exception:
        pass
    try:
        url = "https://iptoasn.com/data/ip2asn-v4-u32.tsv.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=30).read()
        starts, ends, asn, cc = [], [], [], []
        with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 4:
                    starts.append(int(parts[0]))
                    ends.append(int(parts[1]))
                    asn.append(int(parts[2]) if parts[2].isdigit() else 0)
                    cc.append(parts[3].strip().upper())
        _GEO_TABLE = {"starts": starts, "ends": ends, "asn": asn, "cc": cc}
        return _GEO_TABLE
    except Exception:
        return None


def _resolve_ip(host: str) -> str:
    if not host:
        return ""
    if host in _IP_CACHE:
        return _IP_CACHE[host]
    try:
        ipaddress.ip_address(host)
        _IP_CACHE[host] = host
        return host
    except ValueError:
        pass
    try:
        ip = socket.gethostbyname(host)
        _IP_CACHE[host] = ip
        return ip
    except Exception:
        _IP_CACHE[host] = host
        return host


def _lookup_geo(ip: str, table: dict | None) -> tuple[str, str]:
    if not table or not ip:
        return "DE", "Cloud"
    try:
        ipi = int(ipaddress.IPv4Address(ip))
    except Exception:
        return "DE", "Cloud"
    idx = bisect.bisect_right(table["starts"], ipi) - 1
    if idx >= 0 and table["ends"][idx] >= ipi:
        cc = table["cc"][idx]
        as_num = table["asn"][idx]
        dc = ASN_DC_MAP.get(as_num, f"AS{as_num}" if as_num else "Cloud")
        return cc, dc
    return "DE", "Cloud"


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


def _get_flag(cc: str) -> str:
    if not cc or len(cc) != 2:
        return "🌐"
    return "".join(chr(127397 + ord(c)) for c in cc.upper())


def _extract_host(uri: str) -> str:
    try:
        if uri.startswith("vmess://"):
            data = json.loads(base64.b64decode(uri[8:].strip() + "==").decode("utf-8", "ignore"))
            return str(data.get("add", ""))
        u = urlsplit(f"//{uri.split('://', 1)[1].partition('?')[0].partition('#')[0]}")
        return (u.hostname or "").rstrip(".")
    except Exception:
        return ""


def _parse_cap_and_proto(uri: str) -> tuple[str, str]:
    scheme = uri.split("://", 1)[0].lower()
    low = uri.lower()

    if "security=reality" in low or "pbk=" in low:
        cap = "Reality"
    elif "type=ws" in low or "net=ws" in low or '"net":"ws"' in low:
        cap = "WebSocket"
    elif "type=grpc" in low or "net=grpc" in low:
        cap = "gRPC"
    elif scheme in ("hysteria2", "hy2"):
        cap = "QUIC-UDP"
    elif "security=tls" in low:
        cap = "TLS"
    else:
        cap = "Direct"

    host = _extract_host(uri)
    is_ipv6 = ":" in host
    ip_ver = "IPv6" if is_ipv6 else "IPv4"

    proto_names = {
        "vless": "VLESS", "vmess": "VMess", "trojan": "Trojan",
        "ss": "Shadowsocks", "ssr": "SSR", "hysteria2": "Hysteria2",
        "hy2": "Hysteria2", "tuic": "TUIC"
    }
    proto_title = proto_names.get(scheme, scheme.upper())
    return cap, f"{proto_title} {ip_ver}"


def remark_uri(uri: str, ping_ms: float | None, table: dict | None) -> str:
    host = _extract_host(uri)
    ip = _resolve_ip(host)
    cc, dc_name = _lookup_geo(ip, table)

    flag = _get_flag(cc)
    country_fa = COUNTRY_NAMES_FA.get(cc, cc)
    ping_str = f"{int(round(ping_ms))}ms" if (ping_ms and ping_ms > 0) else "OK"
    cap, proto_ip = _parse_cap_and_proto(uri)

    tag = (
        f"👉🆔@Goodbaye_filtering 📡{flag} {country_fa} ®️{dc_name} "
        f"🅿️ping:{ping_str} ⚡{cap} | {proto_ip}"
    )

    if uri.startswith("vmess://"):
        try:
            data = json.loads(base64.b64decode(uri[8:].strip() + "==").decode("utf-8", "ignore"))
            data["ps"] = tag
            new_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
            return f"vmess://{new_b64}"
        except Exception:
            pass

    base = uri.split("#", 1)[0]
    return f"{base}#{tag}"


def publish_outputs(dist: Path, rows: list[dict], all_unique: list[str]) -> None:
    dist.mkdir(exist_ok=True, parents=True)
    table = _get_geo_table()
    alive = [r for r in rows if r["alive"]]

    all_branded = [remark_uri(u, None, table) for u in all_unique]
    all_txt = "\n".join(all_branded) + "\n"
    (dist / "all.txt").write_text(all_txt, encoding="utf-8")
    write_b64(dist / "all.b64", all_txt)

    val_branded = [remark_uri(r["uri"], r.get("latency_ms"), table) for r in alive]
    val_txt = "\n".join(val_branded) + "\n"
    (dist / "validated.txt").write_text(val_txt, encoding="utf-8")
    write_b64(dist / "validated.b64", val_txt)

    gold_rows = [r for r in alive if r["tier"] == "gold"]
    gold_branded = [remark_uri(r["uri"], r.get("latency_ms"), table) for r in gold_rows]
    gold_txt = "\n".join(gold_branded) + "\n"
    (dist / "gold.txt").write_text(gold_txt, encoding="utf-8")
    write_b64(dist / "gold.b64", gold_txt)

    silver_rows = [r for r in alive if r["tier"] == "silver"]
    silver_branded = [remark_uri(r["uri"], r.get("latency_ms"), table) for r in silver_rows]
    silver_txt = "\n".join(silver_branded) + "\n"
    (dist / "silver.txt").write_text(silver_txt, encoding="utf-8")
    write_b64(dist / "silver.b64", silver_txt)

    (dist / "clash.yaml").write_text(E.to_mihomo(alive), encoding="utf-8")
    (dist / "singbox.json").write_text(E.to_singbox(alive), encoding="utf-8")


def _send_telegram_file(bot_token: str, chat_id: str, file_path: Path, caption: str, reply_markup: dict) -> bool:
    boundary = "----GoodbayeBoundary" + hashlib.md5(os.urandom(16)).hexdigest()
    body = bytearray()

    def add_field(name: str, value: str):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())

    add_field("chat_id", chat_id)
    add_field("caption", caption)
    add_field("parse_mode", "HTML")
    add_field("reply_markup", json.dumps(reply_markup))

    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="document"; filename="{file_path.name}"\r\n'.encode())
    body.extend(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.status == 200
    except Exception as exc:
        print(f"[Telegram] Failed to upload {file_path.name}: {exc}")
        return False


def publish_telegram(dist: Path) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return

    tehran_dt = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3, minutes=30)
    jy, jm, jd = to_jalali(tehran_dt.year, tehran_dt.month, tehran_dt.day)
    jalali_date = f"{jy}/{jm:02d}/{jd:02d}"
    tehran_time = tehran_dt.strftime("%H:%M")

    reply_markup = {
        "inline_keyboard": [
            [{"text": "📢 کانال اصلی Goodbaye_filtering", "url": "https://t.me/Goodbaye_filtering"}],
            [{"text": "⚡ کانال اختصاصی VIP", "url": "https://t.me/CONFIG_V2RAY_VIP"}],
            [{"text": "🔐 کانال خصوصی", "url": "https://t.me/+m4GhEHGLd2k5ZjU0"}],
            [{"text": "🔄 اشتراک‌گذاری با دوستان", "url": "https://t.me/share/url?url=https://t.me/Goodbaye_filtering"}]
        ]
    }

    targets = [
        ("gold.txt", "رده طلایی VIP"),
        ("silver.txt", "رده نقره‌ای باکیفیت"),
    ]

    for fname, package_title in targets:
        fpath = dist / fname
        if fpath.exists() and fpath.stat().st_size > 0:
            lines = [ln for ln in fpath.read_text(encoding="utf-8").splitlines() if ln.strip()]
            caption = (
                f"🚀 <b>مجموعه کانفیگ‌های تست‌شده و زنده ({package_title})</b>\n"
                f"📡 مناسب دوران اختلال، فیلترینگ و شبکه ملی\n\n"
                f"📅 تاریخ شمسی: <code>{jalali_date}</code>\n"
                f"⏰ ساعت تهران: <code>{tehran_time}</code>\n"
                f"📊 شاخص کیفیت: VIP Strict (Ping &lt; 500ms)\n"
                f"🔢 تعداد کانفیگ سالم این فایل: <b>{len(lines):,}</b>"
            )
            _send_telegram_file(bot_token, chat_id, fpath, caption, reply_markup)
            print(f"[Telegram] Uploaded {fname} successfully.")
