from __future__ import annotations

WEIGHTS = {"latency": 0.40, "success": 0.30, "protocol": 0.15, "streak": 0.15}

PROTOCOL_BONUS = {
    "hysteria2": 100, "hy2": 100, "tuic": 95,
    "vless": 85, "vmess": 70, "trojan": 70, "ss": 50, "ssr": 20
}


def latency_score(ms: float) -> float:
    if ms <= 200:
        return 100.0
    if ms <= 350:
        return 85.0
    if ms <= 600:
        return 65.0
    if ms <= 1000:
        return 40.0
    return 15.0


def protocol_score(uri: str) -> float:
    scheme = uri.split("://", 1)[0].lower()
    score = float(PROTOCOL_BONUS.get(scheme, 40.0))
    if scheme == "vless" and "security=reality" in uri.lower():
        score = 100.0
    return score


def streak_score(streak: int) -> float:
    # پایه امتیاز برای زنده بودن در تست جاری + پاداش سابقه
    return min(100.0, 50.0 + float(streak) * 10.0)


def total(latency_ms: float | None, success_rate: float | None, streak: int, uri: str) -> float:
    parts = {}
    if latency_ms is not None:
        parts["latency"] = latency_score(latency_ms)
    # در تست‌های اولیه موفقیت ۱۰۰٪ در نظر گرفته می‌شود
    rate = success_rate if (success_rate and success_rate > 0) else 1.0
    parts["success"] = max(0.0, min(1.0, rate)) * 100.0
    parts["protocol"] = protocol_score(uri)
    parts["streak"] = streak_score(streak)

    wsum = sum(WEIGHTS[k] for k in parts)
    return round(sum(WEIGHTS[k] * v for k, v in parts.items()) / wsum, 1)


def tier(score: float) -> str:
    if score >= 80.0:
        return "gold"
    if score >= 60.0:
        return "silver"
    return "bronze"
