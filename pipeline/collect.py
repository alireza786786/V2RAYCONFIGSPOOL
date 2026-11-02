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
    raw_env = os.environ.get("SOURCES_RAW", "").strip()
    if raw_env:
        try:
            if raw_env.startswith("["):
                return json.loads(raw_env)
            decoded = base64.b64decode(raw_env).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            pass
    sources_file = os.path.join(os.path.dirname(__file__), "sources.json")
    if os.path.isfile(sources_file):
        try:
            with open(sources_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data.get("sources", [])
        except Exception:
            return []
    return []


def collect_all(sources: list[dict], workers: int = 16) -> dict[str, dict]:
    results: dict[str, dict] = {}
    todo = [s for s in sources if s.get("enabled", True)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_source, s): s["id"] for s in todo}
        for fut in as_completed(futures):
            sid, text, err = fut.result()
            results[sid] = {"ok": err is None, "error": err, "text": text}
    return results
