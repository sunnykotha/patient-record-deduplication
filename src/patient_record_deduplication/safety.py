from dataclasses import dataclass

from .comparison import (
    compare_addresses,
    compare_first_names,
    compare_last_names,
)
from .patient_record import PatientRecord
from .scoring import (
    MatchDecision,
    MatchThresholds,
    calculate_match_score,
)


@dataclass(frozen=True)
class SafetyResult:
    """Final matching decision and reasons for safety overrides."""

    decision: MatchDecision
    reasons: tuple[str, ...]


def _has_shared_identifier(
    first: PatientRecord,
    second: PatientRecord,
) -> bool:
    """Check whether records share an identifier type and value."""
    first_ids = {
        (item.identifier_type.strip().casefold(), item.value.strip().casefold())
        for item in first.identifiers
    }
    second_ids = {
        (item.identifier_type.strip().casefold(), item.value.strip().casefold())
        for item in second.identifiers
    }
    return bool(first_ids & second_ids)


def _national_id_suffix(record: PatientRecord) -> str | None:
    """Return the last four digits when an ID contains at least four digits."""
    if not record.national_id:
        return None

    digits = "".join(c for c in record.national_id if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else None


def _is_ambiguous_twin_pair(
    first: PatientRecord,
    second: PatientRecord,
) -> bool:
    """Conservatively flag twin-like records without a shared identifier."""
    if first.date_of_birth is None or second.date_of_birth is None:
        return False

    if first.date_of_birth != second.date_of_birth:
        return False

    if not first.address or not second.address:
        return False

    if compare_addresses(first.address, second.address) < 0.95:
        return False

    if not first.first_name or not second.first_name:
        return False

    if not first.last_name or not second.last_name:
        return False

    first_names_similar = (
        compare_first_names(first.first_name, second.first_name) >= 0.75
    )
    last_names_similar = (
        compare_last_names(first.last_name, second.last_name) >= 0.90
    )

    return (
        first_names_similar
        and last_names_similar
        and not _has_shared_identifier(first, second)
        and not (
            _national_id_suffix(first) is not None
            and _national_id_suffix(second) is not None
            and _national_id_suffix(first) != _national_id_suffix(second)
        )
    )


def evaluate_match_safety(
    first: PatientRecord,
    second: PatientRecord,
    thresholds: MatchThresholds | None = None,
) -> SafetyResult:
    """Apply safety overrides before allowing automatic merging."""
    thresholds = thresholds or MatchThresholds()
    result = calculate_match_score(first, second)

    # Safety checks take priority over a high similarity score.
    if _is_ambiguous_twin_pair(first, second):
        return SafetyResult(
            MatchDecision.MANUAL_REVIEW,
            (
                "Possible twin or indistinguishable patient records: "
                "same date of birth, similar names, and matching address.",
            ),
        )

    if not result.evidence:
        return SafetyResult(
            MatchDecision.NOT_A_MATCH,
            ("Insufficient comparison evidence.",),
        )

    if set(result.evidence) == {"phone"}:
        return SafetyResult(
            MatchDecision.MANUAL_REVIEW,
            ("Phone agreement alone cannot establish identity.",),
        )

    # Check the actual ID suffixes, independently of weighted scoring.
    first_suffix = _national_id_suffix(first)
    second_suffix = _national_id_suffix(second)

    if (
        first_suffix is not None
        and second_suffix is not None
        and first_suffix != second_suffix
    ):
        return SafetyResult(
            MatchDecision.MANUAL_REVIEW,
            ("Conflicting national_id_suffix evidence.",),
        )

    # A disagreement in DOB also blocks automatic merging.
    if (
        first.date_of_birth is not None
        and second.date_of_birth is not None
        and result.evidence.get("date_of_birth") == 0.0
    ):
        return SafetyResult(
            MatchDecision.MANUAL_REVIEW,
            ("Conflicting date_of_birth evidence.",),
        )

    if result.score > thresholds.upper:
        return SafetyResult(
            MatchDecision.AUTO_MERGE,
            ("Score exceeds upper threshold; no safety override triggered.",),
        )

    if result.score >= thresholds.lower:
        return SafetyResult(
            MatchDecision.MANUAL_REVIEW,
            ("Score falls within the manual-review band.",),
        )

    return SafetyResult(
        MatchDecision.NOT_A_MATCH,
        ("Score is below the lower threshold.",),
    )