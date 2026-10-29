from datetime import date, datetime

import pytest

from patient_record_deduplication.golden_record import create_golden_record
from patient_record_deduplication.identifier import Identifier
from patient_record_deduplication.patient_record import PatientRecord


def make_record(record_id, **kwargs):
    return PatientRecord(
        record_id=record_id,
        source_system=kwargs.pop("source_system", "hospital"),
        **kwargs,
    )


def test_selects_most_recently_verified_value_per_field():
    older = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        field_verification={
            "first_name": datetime(2024, 1, 1),
            "last_name": datetime(2025, 1, 1),
        },
    )
    newer = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        field_verification={
            "first_name": datetime(2025, 1, 1),
            "last_name": datetime(2024, 1, 1),
        },
    )

    golden = create_golden_record([older, newer], "gold-1")

    assert golden.first_name == "Bob"
    assert golden.last_name == "Mehta"
    assert golden.field_verification["first_name"] == datetime(2025, 1, 1)


def test_empty_value_does_not_replace_nonempty_value():
    first = make_record("r1", phone="555-0100")
    second = make_record(
        "r2",
        phone="   ",
        field_verification={"phone": datetime(2026, 1, 1)},
    )

    golden = create_golden_record([first, second], "gold-2")

    assert golden.phone == "555-0100"


def test_unverified_values_are_fallback_when_no_verified_value_exists():
    first = make_record("r1", address="12 MG Road")
    second = make_record("r2", address="18 Park Street")

    golden = create_golden_record([first, second], "gold-3")

    assert golden.address == "12 MG Road"
    assert "address" not in golden.field_verification


def test_preserves_identifiers_without_duplicates():
    shared = Identifier("MRN", "12345", "hospital")
    other = Identifier("MRN", "67890", "clinic")
    first = make_record("r1", identifiers=[shared, other])
    second = make_record("r2", identifiers=[shared])

    golden = create_golden_record([first, second], "gold-4")

    assert golden.identifiers == [shared, other]


def test_does_not_modify_original_records():
    first = make_record(
        "r1",
        first_name="Robert",
        field_verification={"first_name": datetime(2024, 1, 1)},
    )
    second = make_record(
        "r2",
        first_name="Bob",
        field_verification={"first_name": datetime(2025, 1, 1)},
    )

    create_golden_record([first, second], "gold-5")

    assert first.first_name == "Robert"
    assert second.first_name == "Bob"


def test_requires_at_least_one_record():
    with pytest.raises(ValueError, match="At least one"):
        create_golden_record([], "gold-empty")