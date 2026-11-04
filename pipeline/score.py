from __future__ import annotations

WEIGHTS = {"latency": 0.40, "success": 0.30, "freshness": 0.15, "protocol": 0.15}

PROTOCOL_BONUS = {
    "hysteria2": 90, "hy2": 90, "hysteria": 85, "tuic": 85,
    "vless": 60, "vmess": 55, "trojan": 55, "ss": 40, "ssr": 20,
}


def latency_score(ms: float) -> float:
    if ms <= 150:
        return 100.0
    if ms <= 300:
        return 80.0
    if ms <= 600:
        return 55.0
    if ms <= 1000:
        return 30.0
    return 10.0


def protocol_score(uri: str) -> float:
    scheme = uri.split("://", 1)[0].lower()
    base = PROTOCOL_BONUS.get(scheme, 20.0)
    if scheme == "vless" and "security=reality" in uri.lower():
        base = 100.0
    elif scheme == "vless" and "security=tls" in uri.lower():
        base = 60.0
    return float(base)


def total(latency_ms: float | None, success_rate: float | None, streak: int, uri: str) -> float:
    parts = {}
    if latency_ms is not None:
        parts["latency"] = latency_score(latency_ms)
    rate = success_rate if (success_rate is not None and success_rate > 0) else 1.0
    parts["success"] = max(0.0, min(1.0, rate)) * 100.0
    parts["freshness"] = 100.0
    parts["protocol"] = protocol_score(uri)

    wsum = sum(WEIGHTS[k] for k in parts)
    return round(sum(WEIGHTS[k] * v for k, v in parts.items()) / wsum, 1)


def tier(score: float) -> str:
    if score >= 80.0:
        return "gold"
    if score >= 55.0:
        return "silver"
    return "bronze"
