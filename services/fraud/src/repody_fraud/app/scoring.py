"""Deterministic risk scoring and policy escalation thresholds for Fraud Shield."""

from repody_common.contracts import FraudFinding, FraudSeverity

_WEIGHTS: dict[FraudSeverity, int] = {
    "clean": 0,
    "low": 5,
    "medium": 12,
    "high": 25,
    "critical": 50,
}


def compute_risk_summary(
    findings: list[FraudFinding],
    *,
    short_circuit_threshold: int = 80,
    four_eyes_threshold: int = 40,
) -> tuple[int, FraudSeverity, bool, bool]:
    """Compute bounded risk score (0-100), overall severity, short-circuit, and Four-Eyes flags."""
    if not findings:
        return 0, "clean", False, False

    raw = sum(_WEIGHTS.get(item.severity, 0) for item in findings)
    has_critical = any(item.severity == "critical" for item in findings)
    has_high = any(item.severity == "high" for item in findings)
    if has_critical:
        raw = max(raw, 80)
    score = min(100, raw)

    if score == 0:
        severity: FraudSeverity = "clean"
    elif score < 25:
        severity = "low"
    elif score < 50:
        severity = "medium"
    elif score < 80:
        severity = "high"
    else:
        severity = "critical"

    short_circuit = score >= short_circuit_threshold or has_critical
    requires_four_eyes = score >= four_eyes_threshold or has_critical or has_high
    return score, severity, short_circuit, requires_four_eyes
