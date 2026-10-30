from datetime import datetime

from app import models

RISK_WEIGHTS = {
    "TAB_SWITCH": 6,
    "WINDOW_BLUR": 5,
    "LOCALHOST_ACCESS": 18,
    "LOCAL_IP_ACCESS": 20,
    "AI_WEBSITE_ACCESS": 24,
    "BROWSER_FOCUS_LOST": 8,
    "APP_SWITCH": 10,
    "FILE_EXPLORER_OPENED": 12,
    "TERMINAL_OPENED": 16,
    "IDE_OPENED": 14,
    "EXTENSION_DISCONNECTED": 10,
    "DESKTOP_AGENT_DISCONNECTED": 10,
}

SUSPICIOUS_EVENT_TYPES = {
    "LOCALHOST_ACCESS",
    "LOCAL_IP_ACCESS",
    "AI_WEBSITE_ACCESS",
    "TERMINAL_OPENED",
    "IDE_OPENED",
    "FILE_EXPLORER_OPENED",
    "APP_SWITCH",
}


def _risk_level(score: int) -> str:
    if score >= 60:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def calculate_interview_risk(db, interview_id: int):
    events = (
        db.query(models.InterviewEvent)
        .filter(models.InterviewEvent.interview_id == interview_id)
        .order_by(models.InterviewEvent.created_at.asc())
        .all()
    )

    score = 0
    reasons = []
    timeline = []
    suspicious_count = 0

    for event in events:
        event_weight = RISK_WEIGHTS.get(event.event_type, 3)
        if event.event_type in SUSPICIOUS_EVENT_TYPES:
            event_weight += 4
        event.risk_score = event_weight
        event.is_suspicious = "true" if event_weight >= 10 else "false"
        score += event_weight
        timeline.append(f"{event.created_at.isoformat()} :: {event.event_type}")
        if event.event_type in SUSPICIOUS_EVENT_TYPES:
            suspicious_count += 1
            reasons.append(f"{event.event_type} occurred at {event.created_at.isoformat()}")

    for idx in range(len(events) - 1):
        current = events[idx]
        nxt = events[idx + 1]
        if current and nxt:
            delta = (nxt.created_at - current.created_at).total_seconds()
            if delta <= 45 and (
                current.event_type in SUSPICIOUS_EVENT_TYPES or nxt.event_type in SUSPICIOUS_EVENT_TYPES
            ):
                score += 12
                reasons.append(
                    f"Correlated risk cluster within 45s: {current.event_type} -> {nxt.event_type}"
                )

    db.commit()
    return {
        "interview_id": interview_id,
        "score": score,
        "level": _risk_level(score),
        "reasons": reasons[:8],
        "suspicious_event_count": suspicious_count,
        "event_count": len(events),
        "timeline": timeline[:12],
    }
