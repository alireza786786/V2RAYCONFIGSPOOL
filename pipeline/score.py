from __future__ import annotations

WEIGHTS = {"latency": 0.35, "success": 0.25, "streak": 0.25, "protocol": 0.15}

PROTOCOL_BONUS = {
    "hysteria2": 100, "hy2": 100, "tuic": 90,
    "vless": 80, "vmess": 65, "trojan": 65, "ss": 50, "ssr": 20
}


def latency_score(ms: float) -> float:
    if ms <= 180:
        return 100.0
    if ms <= 350:
        return 80.0
    if ms <= 700:
        return 55.0
    if ms <= 1100:
        return 30.0
    return 10.0


def protocol_score(uri: str) -> float:
    scheme = uri.split("://", 1)[0].lower()
    score = float(PROTOCOL_BONUS.get(scheme, 30.0))
    if scheme == "vless" and "security=reality" in uri.lower():
        score = 95.0
    return score


def streak_score(streak: int) -> float:
    return min(100.0, float(streak) * 10.0)


def total(latency_ms: float | None, success_rate: float | None, streak: int, uri: str) -> float:
    parts = {}
    if latency_ms is not None:
        parts["latency"] = latency_score(latency_ms)
    if success_rate is not None:
        parts["success"] = max(0.0, min(1.0, success_rate)) * 100.0
    parts["streak"] = streak_score(streak)
    parts["protocol"] = protocol_score(uri)

    wsum = sum(WEIGHTS[k] for k in parts)
    return round(sum(WEIGHTS[k] * v for k, v in parts.items()) / wsum, 1)


def tier(score: float) -> str:
    if score >= 80.0:
        return "gold"
    if score >= 55.0:
        return "silver"
    return "bronze"
