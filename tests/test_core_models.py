from datetime import date, datetime

import pytest

from patient_record_deduplication.block_key import BlockKey
from patient_record_deduplication.identifier import Identifier
from patient_record_deduplication.match_score import MatchScore
from patient_record_deduplication.patient_record import PatientRecord


def test_identifier_stores_source_and_value():
    identifier = Identifier("MRN", "12345", "hospital_a")

    assert identifier.identifier_type == "MRN"
    assert identifier.value == "12345"
    assert identifier.source_system == "hospital_a"


@pytest.mark.parametrize(
    "args",
    [
        ("", "12345", "hospital_a"),
        ("MRN", " ", "hospital_a"),
        ("MRN", "12345", ""),
    ],
)
def test_identifier_rejects_empty_required_values(args):
    with pytest.raises(ValueError):
        Identifier(*args)


def test_patient_record_stores_demographics_identifiers_and_verification():
    identifier = Identifier("MRN", "12345", "hospital_a")
    verified_at = datetime(2026, 1, 10, 9, 0)

    record = PatientRecord(
        record_id="record-1",
        source_system="hospital_a",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        identifiers=[identifier],
        field_verification={"first_name": verified_at},
    )

    assert record.first_name == "Robert"
    assert record.date_of_birth == date(1980, 3, 12)
    assert record.identifiers == [identifier]
    assert record.field_verification["first_name"] == verified_at


def test_patient_record_allows_missing_demographic_values():
    record = PatientRecord(record_id="record-2", source_system="clinic_b")

    assert record.first_name is None
    assert record.date_of_birth is None
    assert record.identifiers == []


def test_patient_record_rejects_empty_record_id():
    with pytest.raises(ValueError):
        PatientRecord(record_id=" ", source_system="hospital_a")


def test_patient_record_rejects_invalid_identifier_entries():
    with pytest.raises(ValueError):
        PatientRecord(
            record_id="record-3",
            source_system="hospital_a",
            identifiers=["not-an-identifier"],
        )


def test_patient_record_rejects_unknown_verified_field():
    with pytest.raises(ValueError):
        PatientRecord(
            record_id="record-4",
            source_system="hospital_a",
            field_verification={"unknown_field": datetime.now()},
        )


def test_block_key_stores_birth_year_and_soundex():
    key = BlockKey(1980, "M500")

    assert key.birth_year == 1980
    assert key.last_name_soundex == "M500"


def test_block_key_rejects_invalid_birth_year():
    with pytest.raises(ValueError):
        BlockKey(0, "M500")


def test_block_key_rejects_empty_soundex():
    with pytest.raises(ValueError):
        BlockKey(1980, " ")


def test_match_score_stores_score_and_evidence():
    result = MatchScore(
        score=0.95,
        evidence={"name": 0.98, "address": 0.90},
    )

    assert result.score == 0.95
    assert result.evidence["name"] == 0.98


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf"), True])
def test_match_score_rejects_invalid_score(score):
    with pytest.raises(ValueError):
        MatchScore(score=score)


def test_match_score_rejects_invalid_evidence_value():
    with pytest.raises(ValueError):
        MatchScore(score=0.8, evidence={"name": 1.5})