from datetime import date

from patient_record_deduplication.identifier import Identifier
from patient_record_deduplication.patient_record import PatientRecord
from patient_record_deduplication.safety import evaluate_match_safety
from patient_record_deduplication.scoring import MatchDecision


def make_record(record_id, **kwargs):
    return PatientRecord(
        record_id=record_id,
        source_system=f"system_{record_id}",
        **kwargs,
    )


def test_twin_like_records_are_sent_to_manual_review():
    first = make_record(
        "r1",
        first_name="Anna",
        last_name="Mehta",
        date_of_birth=date(2000, 5, 10),
        address="12 MG Road",
    )
    second = make_record(
        "r2",
        first_name="Anya",
        last_name="Mehta",
        date_of_birth=date(2000, 5, 10),
        address="12 M.G. Rd.",
    )

    result = evaluate_match_safety(first, second)

    assert result.decision == MatchDecision.MANUAL_REVIEW
    assert any("twin" in reason.lower() for reason in result.reasons)


def test_shared_family_phone_alone_never_auto_merges():
    first = make_record("r1", phone="9876543210")
    second = make_record("r2", phone="9876543210")

    result = evaluate_match_safety(first, second)

    assert result.decision == MatchDecision.MANUAL_REVIEW
    assert any("phone" in reason.lower() for reason in result.reasons)


def test_dob_conflict_prevents_automatic_merge():
    first = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
        phone="9876543210",
    )
    second = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1981, 3, 12),
        address="12 MG Road",
        phone="9876543210",
    )

    result = evaluate_match_safety(first, second)

    assert result.decision != MatchDecision.AUTO_MERGE
    assert any("date_of_birth" in reason for reason in result.reasons)


def test_national_id_suffix_conflict_prevents_auto_merge():
    first = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
        national_id="12345678",
    )
    second = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
        national_id="87654321",
    )

    result = evaluate_match_safety(first, second)

    assert result.decision != MatchDecision.AUTO_MERGE
    assert any("national_id_suffix" in reason for reason in result.reasons)


def test_matching_identifier_can_resolve_twin_ambiguity_rule():
    shared_identifier = Identifier("MRN", "12345", "hospital")

    first = make_record(
        "r1",
        first_name="Anna",
        last_name="Mehta",
        date_of_birth=date(2000, 5, 10),
        address="12 MG Road",
        identifiers=[shared_identifier],
    )
    second = make_record(
        "r2",
        first_name="Anya",
        last_name="Mehta",
        date_of_birth=date(2000, 5, 10),
        address="12 MG Road",
        identifiers=[shared_identifier],
    )

    result = evaluate_match_safety(first, second)

    assert not any("twin" in reason.lower() for reason in result.reasons)


def test_exact_worked_example_is_flagged_as_ambiguous_without_identifier():
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

    result = evaluate_match_safety(first, second)

    assert result.decision == MatchDecision.MANUAL_REVIEW


def test_different_dob_does_not_trigger_twin_ambiguity():
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
        date_of_birth=date(1981, 3, 12),
        address="12 MG Road",
    )

    result = evaluate_match_safety(first, second)

    assert not any("twin" in reason.lower() for reason in result.reasons)


def test_unrelated_empty_records_are_not_a_match():
    first = make_record("r1")
    second = make_record("r2")

    result = evaluate_match_safety(first, second)

    assert result.decision == MatchDecision.NOT_A_MATCH