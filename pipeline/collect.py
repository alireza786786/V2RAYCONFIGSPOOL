from __future__ import annotations

import base64
import json
import os
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "35"))
MAX_BYTES = int(os.environ.get("FETCH_MAX_BYTES", str(32 * 1024 * 1024)))

SCHEME_RE = r"(?:vmess|vless|trojan|ss|ssr|hysteria2?|hy2|tuic)"
URI_RE = re.compile(SCHEME_RE + r"://[^\s<>\"'\\]+", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[\s()\[\]{};:'\"<>]+$")


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
        return resp.read(MAX_BYTES).decode("utf-8", "replace")


def _clean(uri: str) -> str:
    uri = uri.replace("&amp;", "&")
    return TRAILING_PUNCT_RE.sub("", uri.strip())


def extract_uris(text: str) -> list[str]:
    found = URI_RE.findall(text)
    return [_clean(u) for u in found if u]


def fetch_source(src: dict) -> tuple[str, str, str | None]:
    """دانلود با تاب‌آوری کامل؛ در صورت خطا کل خط لوله متوقف نمی‌شود."""
    try:
        url = src.get("url", "")
        if src.get("type") == "telegram":
            channel = src.get("channel", "").lstrip("@")
            url = f"https://t.me/s/{channel}"
        if not url:
            return src.get("id", "unknown"), "", "empty-url"
        text = _fetch(url)
        return src["id"], text, None
    except Exception as exc:
        return src.get("id", "unknown"), "", f"{type(exc).__name__}: {exc}"


def load_secret_sources() -> list[dict]:
    """خواندن منعطف SOURCES_RAW از گیت‌هاب (خط‌به‌خط، جیسون، یا بیس۶۴)"""
    raw_env = os.environ.get("SOURCES_RAW", "").strip()
    sources = []

    if raw_env:
        text_to_parse = raw_env
        if not raw_env.startswith(("{", "[", "http", "@")):
            try:
                text_to_parse = base64.b64decode(raw_env).decode("utf-8")
            except Exception:
                pass

        try:
            data = json.loads(text_to_parse)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "sources" in data:
                return data["sources"]
        except Exception:
            pass

        lines = [line.strip() for line in text_to_parse.splitlines() if line.strip() and not line.startswith("#")]
        for idx, line in enumerate(lines):
            if "t.me/" in line:
                channel = line.split("t.me/")[-1].replace("s/", "").split("/")[0].split("?")[0]
                sources.append({"id": f"tg_{idx}", "type": "telegram", "channel": channel})
            elif line.startswith("@"):
                sources.append({"id": f"tg_{idx}", "type": "telegram", "channel": line.lstrip("@")})
            elif line.startswith(("http://", "https://")):
                sources.append({"id": f"src_{idx}", "type": "url", "url": line})
        if sources:
            return sources

    for p in ["sources.json", "pipeline/sources.json"]:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "sources" in data:
                        return data["sources"]
            except Exception:
                pass
    return sources


def collect_all(sources: list[dict], workers: int = 16) -> dict[str, dict]:
    results: dict[str, dict] = {}
    todo = [s for s in sources if s.get("enabled", True)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_source, s): s["id"] for s in todo}
        for fut in as_completed(futures):
            sid, text, err = fut.result()
            results[sid] = {"ok": err is None, "error": err, "text": text}
    return results
