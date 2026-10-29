from datetime import date

import pytest

from patient_record_deduplication.match_score import MatchScore
from patient_record_deduplication.patient_record import PatientRecord
from patient_record_deduplication.scoring import (
    MatchDecision,
    MatchThresholds,
    calculate_match_score,
    classify_match,
)


def make_record(record_id, **kwargs):
    return PatientRecord(
        record_id=record_id,
        source_system="test",
        **kwargs,
    )


def test_worked_example_scores_above_auto_merge_threshold():
    first = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
    )
    second = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 M.G. Rd.",
    )

    result = calculate_match_score(first, second)

    assert result.score == pytest.approx(1.0)
    assert classify_match(result) == MatchDecision.AUTO_MERGE


def test_rare_agreement_gets_more_relative_weight():
    first = make_record(
        "r1",
        first_name="Anita",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
    )
    second = make_record(
        "r2",
        first_name="Anita",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
    )

    common = calculate_match_score(first, second)
    frequencies = {
        "first_name": {"anita": 1, "other": 99},
        "last_name": {"mehta": 50, "other": 50},
        "date_of_birth": {"1980-03-12": 50, "other": 50},
    }
    rarity_adjusted = calculate_match_score(
        first,
        second,
        value_frequencies=frequencies,
    )

    assert rarity_adjusted.score == pytest.approx(common.score)


def test_no_available_evidence_scores_zero():
    first = make_record("r1")
    second = make_record("r2")

    result = calculate_match_score(first, second)

    assert result.score == 0.0
    assert result.evidence == {}
    assert classify_match(result) == MatchDecision.NOT_A_MATCH


def test_high_similarity_is_auto_merge_only_above_upper_threshold():
    assert classify_match(MatchScore(0.95)) == MatchDecision.AUTO_MERGE


def test_exact_upper_threshold_goes_to_manual_review():
    assert classify_match(MatchScore(0.90)) == MatchDecision.MANUAL_REVIEW


def test_middle_band_goes_to_manual_review():
    assert classify_match(MatchScore(0.80)) == MatchDecision.MANUAL_REVIEW


def test_exact_lower_threshold_goes_to_manual_review():
    assert classify_match(MatchScore(0.70)) == MatchDecision.MANUAL_REVIEW


def test_score_below_lower_threshold_is_not_a_match():
    assert classify_match(MatchScore(0.69)) == MatchDecision.NOT_A_MATCH


def test_custom_thresholds_are_supported():
    thresholds = MatchThresholds(lower=0.60, upper=0.85)

    assert classify_match(MatchScore(0.90), thresholds) == MatchDecision.AUTO_MERGE
    assert classify_match(MatchScore(0.80), thresholds) == MatchDecision.MANUAL_REVIEW
    assert classify_match(MatchScore(0.50), thresholds) == MatchDecision.NOT_A_MATCH


@pytest.mark.parametrize(
    "lower,upper",
    [
        (-0.1, 0.9),
        (0.7, 1.1),
        (0.8, 0.8),
        (0.9, 0.7),
    ],
)
def test_invalid_thresholds_are_rejected(lower, upper):
    with pytest.raises(ValueError):
        MatchThresholds(lower=lower, upper=upper)


def test_score_preserves_field_evidence():
    first = make_record("r1", first_name="Robert", last_name="Mehta")
    second = make_record("r2", first_name="Bob", last_name="Mehta")

    result = calculate_match_score(first, second)

    assert result.evidence["first_name"] == 1.0
    assert result.evidence["last_name"] == 1.0