from __future__ import annotations

import base64
import json
from urllib.parse import unquote

from .validate import _b64, _hostport, _query, _scheme, valid_reality

PROBE_URL = "http://www.gstatic.com/generate_204"


def _brand_name(ping_ms: float | None, seen: dict, tier: str | None = None) -> str:
    ms_txt = f"{int(round(ping_ms))}ms" if ping_ms else "alive"
    tag = f"-GOLD" if tier == "gold" else ""
    base = f"V2Pool{tag}-{ms_txt}"
    n = seen.get(base, 0) + 1
    seen[base] = n
    return base if n == 1 else f"{base}-{n}"


def _y(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _mihomo_proxy(uri: str, name: str) -> dict | None:
    scheme = _scheme(uri)
    host, port = _hostport(uri)
    q = _query(uri)
    p: dict = {"name": name, "server": host, "port": port, "udp": True}

    if scheme == "vless":
        net = (q.get("net") or q.get("type") or "tcp").lower()
        p.update({"type": "vless", "uuid": unquote(uri.split("://", 1)[1].split("@", 1)[0]),
                  "cipher": "none", "network": net})
        if q.get("flow"):
            p["flow"] = q["flow"]
    elif scheme == "vmess":
        try:
            d = json.loads(_b64(uri.split("://", 1)[1].strip()))
        except Exception:
            return None
        host, port = str(d.get("add", "")), int(str(d.get("port", "0")) or 0)
        net = str(d.get("net") or "tcp").lower()
        p.update({"type": "vmess", "server": host, "port": port,
                  "uuid": str(d.get("id", "")), "alterId": int(str(d.get("aid", "0")) or 0),
                  "cipher": str(d.get("scy") or "auto"), "network": net})
        q = {k: str(d.get(k, "") or "") for k in ("host", "path", "tls", "sni", "fp", "net", "type")}
    elif scheme == "trojan":
        net = (q.get("net") or q.get("type") or "tcp").lower()
        p.update({"type": "trojan", "password": unquote(uri.split("://", 1)[1].split("@", 1)[0]), "network": net})
    elif scheme in ("hysteria2", "hy2"):
        p.update({"type": "hysteria2", "password": unquote(uri.split("://", 1)[1].split("@", 1)[0].partition("?")[0]),
                  "sni": q.get("sni") or ""})
        return p
    else:
        return None

    sec = (q.get("security") or "").lower()
    net = (q.get("net") or q.get("type") or "tcp").lower()
    if sec == "tls" or scheme == "trojan":
        p["tls"] = True
        sni = q.get("sni") or q.get("host") or host
        if sni:
            p["servername"] = sni
    elif sec == "reality":
        pbk = q.get("pbk") or ""
        sid = q.get("sid") or ""
        if not valid_reality(pbk, sid):
            return None
        p["tls"] = True
        p["servername"] = q.get("sni") or host
        p["reality-opts"] = {"public-key": pbk, "short-id": sid}

    if net == "ws":
        p["network"] = "ws"
        p["ws-opts"] = {"path": q.get("path") or "/", "headers": {"Host": q.get("host") or ""}}
    elif net == "grpc":
        p["network"] = "grpc"
        p["grpc-opts"] = {"grpc-service-name": q.get("serviceName") or q.get("path") or ""}
    return p


def _emit_yaml(p: dict) -> str:
    lines = [f"  - name: {_y(p.pop('name'))}"]
    for k, v in p.items():
        if isinstance(v, dict):
            lines.append(f"    {k}:")
            for kk, vv in v.items():
                lines.append(f"      {kk}: {_y(vv)}")
        else:
            lines.append(f"    {k}: {_y(v)}")
    return "\n".join(lines)


def to_mihomo(rows: list[dict]) -> str:
    proxies, names, seen = [], [], {}
    for r in rows:
        name = _brand_name(r.get("latency_ms"), seen, r.get("tier"))
        p = _mihomo_proxy(r["uri"], name)
        if p:
            names.append(p["name"])
            proxies.append(_emit_yaml(p))

    head = [
        "mixed-port: 7890",
        "mode: rule",
        "log-level: warning",
        "dns:",
        "  enable: true",
        "  nameserver:",
        '    - "8.8.8.8"',
        '    - "1.1.1.1"',
        "proxies:",
    ]
    groups = [
        "proxy-groups:",
        '  - name: "V2Pool"',
        "    type: select",
        "    proxies:",
        '      - "Auto"',
    ] + [f"      - {_y(n)}" for n in names] + [
        '  - name: "Auto"',
        "    type: url-test",
        f'    url: "{PROBE_URL}"',
        "    interval: 300",
        "    proxies:",
    ] + [f"      - {_y(n)}" for n in names]
    rules = [
        "rules:",
        "  - DOMAIN-SUFFIX,ir,DIRECT",
        "  - GEOIP,IR,DIRECT,no-resolve",
        "  - MATCH,V2Pool"
    ]
    return "\n".join(head + proxies + groups + rules)


def to_singbox(rows: list[dict]) -> str:
    outbounds, seen = [], {}
    for r in rows:
        tag = _brand_name(r.get("latency_ms"), seen, r.get("tier"))
        scheme = _scheme(r["uri"])
        host, port = _hostport(r["uri"])
        q = _query(r["uri"])
        if scheme == "vless":
            outbounds.append({
                "type": "vless", "tag": tag, "server": host, "server_port": port,
                "uuid": unquote(r["uri"].split("://", 1)[1].split("@", 1)[0])
            })
    cfg = {
        "inbounds": [{"type": "mixed", "listen": "127.0.0.1", "listen_port": 2080}],
        "outbounds": [{"type": "selector", "tag": "V2Pool", "outbounds": [o["tag"] for o in outbounds]}] + outbounds + [{"type": "direct", "tag": "direct"}],
        "route": {
            "rules": [
                {"domain_suffix": [".ir"], "outbound": "direct"},
                {"geoip": ["ir"], "outbound": "direct"},
                {"outbound": "V2Pool"}
            ]
        }
    }
    return json.dumps(cfg, ensure_ascii=False, indent=2)
