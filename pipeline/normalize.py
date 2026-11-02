from __future__ import annotations

import base64
import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit

URL_SCHEMES = {"vless", "trojan", "tuic", "hysteria", "hysteria2", "hy2"}
ALL_SCHEMES = URL_SCHEMES | {"vmess", "ss", "ssr"}

_VMESS_KEYS = (
    "v", "add", "port", "id", "aid", "scy", "net", "type",
    "host", "path", "tls", "sni", "alpn", "fp"
)


def _b64decode(text: str) -> str:
    pad = "=" * (-len(text) % 4)
    return base64.b64decode(text.replace("-", "+").replace("_", "/") + pad).decode("utf-8", "replace")


def try_b64_blob(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped or "\n" in stripped[:120] or "://" in stripped[:200]:
        return []
    if not re.fullmatch(r"[A-Za-z0-9+/=_-]+", stripped):
        return []
    try:
        decoded = _b64decode(stripped)
    except Exception:
        return []
    return [ln.strip() for ln in decoded.splitlines() if ln.split("://", 1)[0].lower() in ALL_SCHEMES]


def _canonical_vmess(uri: str) -> tuple[str, str] | None:
    raw = uri[len("vmess://"):].strip()
    try:
        data = json.loads(_b64decode(raw))
        if not isinstance(data, dict):
            return None
    except Exception:
        return None
    add = str(data.get("add", "")).strip()
    try:
        port = str(int(str(data.get("port", "")).strip() or 0))
    except ValueError:
        port = str(data.get("port", "")).strip()
    ident = str(data.get("id", "")).strip().lower()
    if not add or not port or not ident:
        return None
    slim = {}
    for key in _VMESS_KEYS:
        val = data.get(key)
        if val not in (None, ""):
            slim[key] = str(val).strip()
    slim["add"], slim["port"], slim["id"] = add, port, ident
    slim["v"] = slim.get("v", "2")
    enc = base64.b64encode(json.dumps(slim, sort_keys=True, ensure_ascii=False).encode()).decode()
    net = slim.get("net", "tcp").lower()
    path = slim.get("path", "")
    host = slim.get("host", "") or slim.get("sni", "")
    node_key = f"vmess|{add.lower()}|{port}|{ident}|{net}|{host}|{path}"
    return f"vmess://{enc}", node_key


def _canonical_ss(uri: str) -> tuple[str, str] | None:
    body = uri[len("ss://"):].partition("#")[0]
    query = ""
    if "@" in body:
        userinfo, _, rest = body.rpartition("@")
        hostport, _, query = rest.partition("?")
        if not hostport:
            return None
    else:
        try:
            decoded = _b64decode(body)
        except Exception:
            return None
        userinfo, _, hostport = decoded.rpartition("@")
        if not hostport:
            return None
    userinfo = re.sub(r"\s", "", userinfo)
    host = (urlsplit(f"//{hostport}").hostname or "").lower().rstrip(".")
    try:
        port = urlsplit(f"//{hostport}").port
    except ValueError:
        return None
    if not host or not port:
        return None
    enc_user = base64.b64encode(userinfo.encode()).decode().rstrip("=")
    hostpart = f"[{host}]" if ":" in host else host
    qs = urlencode(sorted(parse_qsl(query, keep_blank_values=True)), safe=":/@")
    canon = f"ss://{enc_user}@{hostpart}:{port}" + (f"?{qs}" if qs else "")
    return canon, f"ss|{host}|{port}|{userinfo}"


def _canonical_ssr(uri: str) -> tuple[str, str] | None:
    try:
        decoded = _b64decode(uri[len("ssr://"):].strip())
    except Exception:
        return None
    main, _, params = decoded.partition("/?")
    parts = main.split(":")
    if len(parts) < 6:
        return None
    host = ":".join(parts[:-5]).lower().rstrip(".")
    port, proto, method, obfs, _pass = parts[-5:]
    keep = {}
    for kv in params.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            if k in ("obfsparam", "protoparam"):
                keep[k] = v
    tail = urlencode(sorted(keep.items())) if keep else ""
    inner = f"{host}:{port}:{proto}:{method}:{obfs}:{_pass}"
    if tail:
        inner += f"/?{tail}"
    enc = base64.b64encode(inner.encode()).decode().rstrip("=")
    return f"ssr://{enc}", f"ssr|{host}|{port}|{_pass}"


def _canonical_url(uri: str) -> tuple[str, str] | None:
    scheme, _, rest = uri.partition("://")
    scheme = scheme.lower()
    rest, _, _ = rest.partition("#")
    try:
        u = urlsplit(f"//{rest}")
        hostname = (u.hostname or "").lower().rstrip(".")
        port = u.port
    except ValueError:
        return None
    if not hostname:
        return None
    netloc = u.netloc
    userinfo = netloc.rsplit("@", 1)[0] if "@" in netloc else ""
    hostpart = f"[{hostname}]" if ":" in hostname else hostname
    if port:
        hostpart += f":{port}"
    qs = urlencode(sorted(parse_qsl(u.query, keep_blank_values=True)), safe=":/@+")
    canon = f"{scheme}://{userinfo + '@' if userinfo else ''}{hostpart}" + (f"?{qs}" if qs else "")
    params = dict(parse_qsl(u.query, keep_blank_values=True))
    net = (params.get("type") or params.get("net") or "tcp").lower()
    sec = params.get("security", "").lower()
    path = params.get("path", "")
    sni = params.get("sni", "") or params.get("host", "")
    node = f"{scheme}|{hostname}|{port or ''}|{userinfo}|{net}|{sec}|{sni}|{path}"
    return canon, node


def canonical(uri: str) -> tuple[str, str] | None:
    scheme = uri.split("://", 1)[0].lower()
    try:
        if scheme == "vmess":
            return _canonical_vmess(uri)
        if scheme == "ss":
            return _canonical_ss(uri)
        if scheme == "ssr":
            return _canonical_ssr(uri)
        if scheme in URL_SCHEMES:
            return _canonical_url(uri)
    except Exception:
        return None
    return None


def dedupe(items: list[tuple[str, str]]) -> tuple[list[str], dict]:
    seen_hash: set[str] = set()
    seen_node: dict[str, str] = {}
    uniq: list[str] = []
    dupes_hash = dupes_node = 0
    for canon, node in items:
        h = hashlib.sha256(canon.encode()).hexdigest()[:16]
        if h in seen_hash:
            dupes_hash += 1
            continue
        if node in seen_node:
            dupes_node += 1
            continue
        seen_hash.add(h)
        seen_node[node] = canon
        uniq.append(canon)
    return uniq, {"exact_dupes": dupes_hash, "same_node_dupes": dupes_node}
