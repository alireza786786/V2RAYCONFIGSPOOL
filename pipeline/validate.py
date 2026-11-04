from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from queue import Queue
from urllib.parse import parse_qsl, unquote, urlsplit

ENV_XRAY = os.environ.get("XRAY_BIN", "bin/xray")
ENV_SINGBOX = os.environ.get("SINGBOX_BIN", "bin/sing-box")
ENV_CONCURRENCY = int(os.environ.get("CONCURRENCY", "64"))
ENV_TIMEOUT = float(os.environ.get("VALIDATE_TIMEOUT", "4.5"))
ENV_PORT_BASE = int(os.environ.get("PORT_BASE", "21000"))
BOOT_DEADLINE = 2.0

PROBE_TARGETS = [
    ("www.gstatic.com", "/generate_204"),
    ("cp.cloudflare.com", "/generate_204"),
]

_XRAY_UNSAFE_NETS = {"kcp", "mkcp", "quic", "domainsocket", "soundsocket"}
_TCP_JUDGED_SCHEMES = ("vless", "vmess", "trojan", "ss")


def _b64(text: str) -> str:
    pad = "=" * (-len(text) % 4)
    return base64.b64decode(text.replace("-", "+").replace("_", "/") + pad).decode("utf-8", "replace")


def _scheme(uri: str) -> str:
    return uri.split("://", 1)[0].lower()


def _query(uri: str) -> dict:
    rest = uri.split("://", 1)[1] if "://" in uri else uri
    _, _, query = rest.partition("?")
    return {k: v for k, v in parse_qsl(query, keep_blank_values=True)}


def _hostport(uri: str) -> tuple[str, int]:
    try:
        u = urlsplit(f"//{uri.split('://', 1)[1].partition('?')[0].partition('#')[0]}")
        return (u.hostname or "").rstrip("."), u.port or 0
    except ValueError:
        return "", 0


def _bool(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes")


def valid_reality(pbk: str, sid: str) -> bool:
    if not pbk or not (40 <= len(pbk) <= 44):
        return False
    try:
        raw = base64.urlsafe_b64decode(pbk.replace("-", "+").replace("_", "/") + "=" * (-len(pbk) % 4))
        if len(raw) != 32:
            return False
    except Exception:
        return False
    if sid and (len(sid) > 16 or any(c not in "0123456789abcdefABCDEF" for c in sid)):
        return False
    return True


def tcp_reachable(uri: str) -> bool | None:
    if _scheme(uri) not in _TCP_JUDGED_SCHEMES:
        return None
    host, port = _hostport(uri)
    if not host or not (0 < port < 65536):
        return False
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except (OSError, UnicodeError):
        return False


def tcp_prefilter(uris: list[str]) -> tuple[list[str], dict]:
    keep = [False] * len(uris)
    stats = {"input": len(uris), "tcp_open": 0, "tcp_closed": 0, "pass_through": 0}
    with ThreadPoolExecutor(max_workers=128) as pool:
        for i, verdict in enumerate(pool.map(tcp_reachable, uris)):
            if verdict is True:
                keep[i] = True
                stats["tcp_open"] += 1
            elif verdict is None:
                keep[i] = True
                stats["pass_through"] += 1
            else:
                stats["tcp_closed"] += 1
    kept = [u for u, k in zip(uris, keep) if k]
    stats["output"] = len(kept)
    return kept, stats


def engine_for(uri: str) -> str | None:
    scheme = _scheme(uri)
    if scheme in ("vless", "trojan"):
        q = _query(uri)
        net = (q.get("net") or q.get("type") or "tcp").lower()
        if net in _XRAY_UNSAFE_NETS:
            return None
        return "xray"
    if scheme == "vmess":
        try:
            d = json.loads(_b64(uri.split("://", 1)[1].strip()))
            net = str(d.get("net") or "tcp").lower()
            if net in _XRAY_UNSAFE_NETS:
                return None
            return "xray"
        except Exception:
            return None
    if scheme == "ss":
        q = _query(uri)
        if "plugin=" in uri.split("?", 1)[-1]:
            return "sing-box"
        return "xray"
    if scheme in ("hysteria2", "hy2", "tuic"):
        return "sing-box"
    return None


def _xray_stream(q: dict, default_host: str, is_vmess: bool = False) -> dict | None:
    # اصلاح باگ هم‌پوشانی net و type در VMess
    if is_vmess:
        net = str(q.get("net") or "tcp").lower()
    else:
        net = str(q.get("net") or q.get("type") or "tcp").lower()

    st: dict = {"network": "tcp"}
    if net == "ws":
        ws = {"path": q.get("path") or "/"}
        if q.get("host"):
            ws["headers"] = {"Host": q["host"]}
        st["network"], st["wsSettings"] = "ws", ws
    elif net == "httpupgrade":
        st["network"], st["httpupgradeSettings"] = "httpupgrade", {
            "path": q.get("path") or "/", "host": q.get("host") or ""}
    elif net in ("grpc", "gun"):
        st["network"], st["grpcSettings"] = "grpc", {
            "serviceName": q.get("serviceName") or q.get("path") or "", "multiMode": False}
    elif net in ("h2", "http"):
        st["network"], st["httpSettings"] = "h2", {
            "path": q.get("path") or "/", "host": [q["host"]] if q.get("host") else []}
    elif net == "tcp":
        hdr_type = (q.get("headerType") or q.get("type") or "").lower()
        if hdr_type == "http":
            hdr = {"type": "http", "path": q.get("path") or "/"}
            if q.get("host"):
                hdr["host"] = [q["host"]]
            st["tcpSettings"] = {"header": hdr}
    else:
        return None

    sec = (q.get("security") or "").lower()
    if sec == "tls" or (sec == "" and net == "h2"):
        st["security"] = "tls"
        st["tlsSettings"] = {
            "serverName": q.get("sni") or q.get("host") or default_host,
            "allowInsecure": _bool(q.get("allowInsecure") or q.get("insecure")),
            "fingerprint": q.get("fp") or "chrome"
        }
    elif sec == "reality":
        pbk = q.get("pbk") or ""
        sid = q.get("sid") or ""
        if not valid_reality(pbk, sid):
            return None
        st["security"] = "reality"
        st["realitySettings"] = {
            "serverName": q.get("sni") or default_host,
            "fingerprint": q.get("fp") or "chrome",
            "publicKey": pbk, "shortId": sid, "spiderX": q.get("spx") or "/"
        }
    return st


def _xray_outbound(uri: str) -> dict | None:
    scheme = _scheme(uri)
    host, port = _hostport(uri)
    q = _query(uri)
    out: dict = {"tag": "out"}

    if scheme == "vless":
        user = {"id": unquote(uri.split("://", 1)[1].split("@", 1)[0]), "encryption": "none", "level": 0}
        if q.get("flow"):
            user["flow"] = q["flow"]
        out["protocol"] = "vless"
        out["settings"] = {"vnext": [{"address": host, "port": port, "users": [user]}]}
        stream = _xray_stream(q, host, is_vmess=False)

    elif scheme == "vmess":
        try:
            data = json.loads(_b64(uri.split("://", 1)[1].strip()))
        except Exception:
            return None
        host, port = str(data.get("add", "")), int(str(data.get("port", "0")) or 0)
        if not host or not port:
            return None
        q = {k: str(data.get(k, "") or "") for k in ("net", "type", "host", "path", "tls", "sni", "alpn", "fp", "scy")}
        q["security"] = "tls" if str(data.get("tls", "")).lower() == "tls" else ""
        out["protocol"] = "vmess"
        out["settings"] = {"vnext": [{"address": host, "port": port, "users": [{
            "id": str(data.get("id", "")), "alterId": int(str(data.get("aid", "0")) or 0),
            "security": q.get("scy") or "auto", "level": 0}]}]}
        stream = _xray_stream(q, host, is_vmess=True)

    elif scheme == "trojan":
        out["protocol"] = "trojan"
        out["settings"] = {"servers": [{"address": host, "port": port, "password": unquote(uri.split("://", 1)[1].split("@", 1)[0])}]}
        if "security=" not in q:
            q["security"] = "tls"
        stream = _xray_stream(q, host, is_vmess=False)

    elif scheme == "ss":
        try:
            userinfo = uri.split("://", 1)[1].split("@", 1)[0]
            try:
                method, _, password = _b64(userinfo).partition(":")
            except Exception:
                method, _, password = unquote(userinfo).partition(":")
            if not password:
                return None
        except Exception:
            return None
        out["protocol"] = "shadowsocks"
        out["settings"] = {"servers": [{"address": host, "port": port, "method": method.strip(), "password": password}]}
        stream = _xray_stream(q, host, is_vmess=False)
    else:
        return None

    if stream is None:
        return None
    out["streamSettings"] = stream
    return out


def _singbox_outbound(uri: str) -> dict | None:
    scheme = _scheme(uri)
    host, port = _hostport(uri)
    if not host or not port:
        return None
    q = _query(uri)
    if scheme in ("hysteria2", "hy2"):
        pwd = unquote(uri.split("://", 1)[1].split("@", 1)[0].partition("?")[0])
        tls = {"enabled": True, "insecure": _bool(q.get("insecure") or q.get("allowInsecure")),
               "server_name": q.get("sni") or q.get("peer") or "", "alpn": ["h3"]}
        return {"type": "hysteria2", "tag": "out", "server": host, "server_port": port,
                "password": pwd, "tls": tls}
    if scheme == "tuic":
        cred = unquote(uri.split("://", 1)[1].split("@", 1)[0].partition("?")[0])
        uuid, _, pwd = cred.partition(":")
        return {"type": "tuic", "tag": "out", "server": host, "server_port": port,
                "uuid": uuid, "password": pwd, "congestion_control": q.get("congestion_control") or "bbr",
                "tls": {"enabled": True, "insecure": _bool(q.get("insecure") or q.get("allowInsecure")),
                        "server_name": q.get("sni") or "", "alpn": q.get("alpn", "h3").split(",")}}
    return None


def socks5_probe(port: int, target: tuple[str, str], deadline: float) -> tuple[bool, float, str]:
    host, path = target
    t0 = time.perf_counter()
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=deadline)
        s.settimeout(deadline)
        s.sendall(b"\x05\x01\x00")
        if s.recv(2)[:2] != b"\x05\x00":
            return False, 0.0, "socks-auth"
        hb = host.encode("idna" if host.isascii() else "utf-8")
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + struct.pack(">H", 80))
        reply = s.recv(4)
        if len(reply) < 4 or reply[1] != 0:
            return False, 0.0, "socks-connect"
        s.recv(64)
        req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        buf = b""
        while b"\r\n" not in buf:
            chunk = s.recv(256)
            if not chunk:
                break
            buf += chunk
        ms = (time.perf_counter() - t0) * 1000.0
        parts = buf.split(b"\r\n", 1)[0].split(b" ", 2)
        ok = len(parts) > 1 and parts[1] == b"204"
        s.close()
        return ok, ms, "ok" if ok else "http-status"
    except socket.timeout:
        return False, (time.perf_counter() - t0) * 1000.0, "timeout"
    except Exception as exc:
        return False, (time.perf_counter() - t0) * 1000.0, str(exc)[:32]


def engines_available() -> bool:
    return os.path.isfile(ENV_XRAY) and os.path.isfile(ENV_SINGBOX)


class _Slot:
    def __init__(self, idx: int, tmpdir: str):
        self.idx = idx
        self.port = ENV_PORT_BASE + idx
        self.path = os.path.join(tmpdir, f"cfg{idx}.json")


def _wait_socks(port: int, proc: subprocess.Popen) -> bool:
    deadline = time.monotonic() + BOOT_DEADLINE
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return True
        except OSError:
            time.sleep(0.04)
    return False


def test_one(uri: str, engine: str, slot: _Slot, target: tuple[str, str], timeout: float | None = None) -> dict:
    t = timeout or ENV_TIMEOUT
    try:
        if engine == "xray":
            outbound = _xray_outbound(uri)
            if not outbound:
                return {"uri": uri, "alive": False, "latency_ms": None, "reason": "bad-config"}
            cfg = {
                "log": {"loglevel": "error"},
                "inbounds": [{"listen": "127.0.0.1", "port": slot.port, "protocol": "socks", "settings": {"udp": False}}],
                "outbounds": [outbound, {"protocol": "freedom", "tag": "direct"}]
            }
            argv = [ENV_XRAY, "run", "-c", slot.path]
        else:
            outbound = _singbox_outbound(uri)
            if not outbound:
                return {"uri": uri, "alive": False, "latency_ms": None, "reason": "bad-config"}
            cfg = {
                "log": {"level": "error"},
                "inbounds": [{"type": "socks", "listen": "127.0.0.1", "listen_port": slot.port}],
                "outbounds": [outbound]
            }
            argv = [ENV_SINGBOX, "run", "-c", slot.path]

        with open(slot.path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)

        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if not _wait_socks(slot.port, proc):
                return {"uri": uri, "alive": False, "latency_ms": None, "reason": "engine-boot"}
            ok, ms, reason = socks5_probe(slot.port, target, t)
            return {"uri": uri, "alive": ok, "latency_ms": round(ms, 1) if ok else None, "reason": reason}
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    except Exception as exc:
        return {"uri": uri, "alive": False, "latency_ms": None, "reason": f"error:{type(exc).__name__}"}


def validate_all(uris: list[str], prev: dict | None = None) -> tuple[dict, dict, dict]:
    prev = prev or {}
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    concurrency = max(1, ENV_CONCURRENCY)
    with tempfile.TemporaryDirectory(prefix="pool-") as tmpdir:
        slots: Queue = Queue()
        for i in range(concurrency):
            slots.put(_Slot(i, tmpdir))

        outcomes = [None] * len(uris)
        routable = [(i, u, engine_for(u)) for i, u in enumerate(uris) if engine_for(u)]

        def worker(job):
            idx, u, eng = job
            slot = slots.get()
            try:
                target = PROBE_TARGETS[idx % len(PROBE_TARGETS)]
                outcomes[idx] = test_one(u, eng, slot, target)
            finally:
                slots.put(slot)

        if routable:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                list(pool.map(worker, routable))

    results, per_node = {}, {}
    alive_count = dead_count = 0
    latencies = []

    for i, uri in enumerate(uris):
        eng = engine_for(uri)
        res = outcomes[i]
        if not eng or not res:
            continue
        h = hashlib.sha256(uri.encode()).hexdigest()[:16]
        old = prev.get(h, {})
        ok = bool(res["alive"])
        ok_n = int(old.get("ok", 0)) + (1 if ok else 0)
        fail_n = int(old.get("fail", 0)) + (0 if ok else 1)
        ema = 1.0 if ok else 0.0
        if "ema" in old:
            ema = 0.7 * float(old["ema"]) + 0.3 * ema

        results[h] = {
            "ok": ok_n, "fail": fail_n, "latency_ms": res["latency_ms"],
            "ema": round(ema, 3), "last_tested": now_iso,
            "last_ok": now_iso if ok else old.get("last_ok")
        }
        per_node[uri] = {
            "hash": h, "alive": ok, "latency_ms": res["latency_ms"],
            "ema": ema, "success_rate": (ok_n + 1) / (ok_n + fail_n + 2)
        }
        if ok:
            alive_count += 1
            latencies.append(float(res["latency_ms"]))
        else:
            dead_count += 1

    summary = {
        "probed": len(routable), "alive": alive_count, "dead": dead_count,
        "latency_ms": {"avg": round(sum(latencies) / len(latencies), 1) if latencies else None}
    }
    return results, summary, per_node
