from dataclasses import dataclass
from enum import Enum
from math import log2

from .comparison import compare_records
from .match_score import MatchScore
from .patient_record import PatientRecord


class MatchDecision(str, Enum):
    AUTO_MERGE = "auto_merge"
    MANUAL_REVIEW = "manual_review"
    NOT_A_MATCH = "not_a_match"


@dataclass(frozen=True)
class MatchThresholds:
    """Configurable initial decision thresholds."""

    lower: float = 0.70
    upper: float = 0.90

    def __post_init__(self):
        if not 0.0 <= self.lower <= 1.0:
            raise ValueError("lower threshold must be between 0.0 and 1.0")

        if not 0.0 <= self.upper <= 1.0:
            raise ValueError("upper threshold must be between 0.0 and 1.0")

        if self.lower >= self.upper:
            raise ValueError("lower threshold must be less than upper threshold")


FIELD_WEIGHTS = {
    "first_name": 0.20,
    "last_name": 0.20,
    "date_of_birth": 0.25,
    "address": 0.15,
    "phone": 0.10,
    "national_id_suffix": 0.10,
}


def _field_value(record: PatientRecord, field_name: str) -> str | None:
    """Return a comparable field value for frequency lookup."""
    if field_name == "national_id_suffix":
        if not record.national_id:
            return None
        digits = "".join(c for c in record.national_id if c.isdigit())
        return digits[-4:] if len(digits) >= 4 else None

    value = getattr(record, field_name, None)

    if value is None:
        return None

    if field_name == "date_of_birth":
        return value.isoformat()

    if isinstance(value, str):
        normalized = value.strip().casefold()
        return normalized or None

    return str(value)


def _rarity_factor(
    field_name: str,
    value: str | None,
    value_frequencies: dict[str, dict[str, int]] | None,
) -> float:
    """Return a bounded rarity multiplier for an agreed value.

    Frequency dictionaries map field names to normalized values and counts.
    Rare agreements receive a larger multiplier. Missing frequency data
    leaves the base field weight unchanged.
    """
    if not value_frequencies or value is None:
        return 1.0

    frequencies = value_frequencies.get(field_name, {})
    count = frequencies.get(value)

    if count is None:
        return 1.0

    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("Value frequencies must be non-negative integers")

    total = sum(frequencies.values())

    if total <= 0:
        return 1.0

    rarity = log2((total + 1) / (count + 1))
    return min(2.0, 1.0 + max(0.0, rarity) / 4.0)


def calculate_match_score(
    first: PatientRecord,
    second: PatientRecord,
    value_frequencies: dict[str, dict[str, int]] | None = None,
) -> MatchScore:
    """Calculate a weighted score from available field-comparison evidence."""
    evidence = compare_records(first, second)

    if not evidence:
        return MatchScore(score=0.0, evidence={})

    weighted_total = 0.0
    total_weight = 0.0

    for field_name, similarity in evidence.items():
        weight = FIELD_WEIGHTS[field_name]

        # Rarity increases the relative influence of exact agreements.
        if similarity == 1.0:
            first_value = _field_value(first, field_name)
            second_value = _field_value(second, field_name)

            if first_value is not None and first_value == second_value:
                weight *= _rarity_factor(
                    field_name,
                    first_value,
                    value_frequencies,
                )

        weighted_total += weight * similarity
        total_weight += weight

    score = weighted_total / total_weight if total_weight else 0.0

    return MatchScore(
        score=max(0.0, min(1.0, score)),
        evidence=evidence,
    )


def classify_match(
    match_score: MatchScore,
    thresholds: MatchThresholds | None = None,
) -> MatchDecision:
    """Classify a score using the configured three decision bands."""
    thresholds = thresholds or MatchThresholds()

    if match_score.score > thresholds.upper:
        return MatchDecision.AUTO_MERGE

    if match_score.score >= thresholds.lower:
        return MatchDecision.MANUAL_REVIEW

    return MatchDecision.NOT_A_MATCH