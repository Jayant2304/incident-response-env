"""Deterministic grading — scores IncidentAction against GraderKeys.

Weighted combination of exact-match and keyword-match criteria.
Total reward is in [0.0, 1.0].
"""

from __future__ import annotations

from models import IncidentAction
from server.domain import GraderKeys

WEIGHTS: dict[str, float] = {
    "affected_service": 0.25,
    "root_cause": 0.35,
    "remediation": 0.30,
    "blast_radius": 0.10,
}


def _keyword_score(text: str, keywords: list[str], min_matches: int = 2) -> tuple[float, list[str]]:
    """0 hits -> 0.0, < min_matches -> 0.5 (partial), >= min_matches -> 1.0."""
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    if len(matched) == 0:
        return 0.0, matched
    if len(matched) < min_matches:
        return 0.5, matched
    return 1.0, matched


def _exact_match(actual: str, expected: str) -> float:
    return 1.0 if actual.lower().strip() == expected.lower().strip() else 0.0


def _format_exact_feedback(label: str, expected: str, got: str, score: float) -> str:
    symbol = "\u2713" if score == 1.0 else "\u2717"
    return f"[{label}] {symbol} Expected '{expected}', got '{got}'"


def _format_keyword_feedback(label: str, score: float, matched: list[str]) -> str:
    return f"[{label}] score={score:.2f} \u2014 matched keywords: {matched}"


def grade_incident(
    action: IncidentAction,
    grader_keys: GraderKeys,
) -> tuple[float, dict[str, float], str]:
    """Returns ``(total_reward, breakdown, feedback)``."""
    breakdown: dict[str, float] = {}
    feedback_parts: list[str] = []

    svc_score = _exact_match(action.affected_service, grader_keys.affected_service_key)
    breakdown["affected_service"] = round(svc_score * WEIGHTS["affected_service"], 4)
    feedback_parts.append(_format_exact_feedback(
        "service", grader_keys.affected_service_key, action.affected_service, svc_score,
    ))

    rc_score, rc_matched = _keyword_score(action.root_cause, grader_keys.root_cause_keywords)
    breakdown["root_cause"] = round(rc_score * WEIGHTS["root_cause"], 4)
    feedback_parts.append(_format_keyword_feedback("root_cause", rc_score, rc_matched))

    rem_score, rem_matched = _keyword_score(action.remediation, grader_keys.remediation_keywords)
    breakdown["remediation"] = round(rem_score * WEIGHTS["remediation"], 4)
    feedback_parts.append(_format_keyword_feedback("remediation", rem_score, rem_matched))

    br_score = _exact_match(action.blast_radius, grader_keys.blast_radius_key)
    breakdown["blast_radius"] = round(br_score * WEIGHTS["blast_radius"], 4)
    feedback_parts.append(_format_exact_feedback(
        "blast_radius", grader_keys.blast_radius_key, action.blast_radius, br_score,
    ))

    total_reward = round(sum(breakdown.values()), 4)
    feedback = " | ".join(feedback_parts)
    return total_reward, breakdown, feedback
