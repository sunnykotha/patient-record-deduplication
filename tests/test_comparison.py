from datetime import date

from patient_record_deduplication.comparison import (
    compare_addresses,
    compare_dates_of_birth,
    compare_first_names,
    compare_last_names,
    compare_national_id_suffixes,
    compare_phones,
    compare_records,
    normalize_address,
)
from patient_record_deduplication.patient_record import PatientRecord


def test_bob_matches_robert_through_nickname_table():
    assert compare_first_names("Bob", "Robert") == 1.0


def test_case_does_not_affect_first_name_comparison():
    assert compare_first_names("ROBERT", "Robert") == 1.0


def test_typo_in_first_name_gets_similarity_score():
    score = compare_first_names("Jon", "John")

    assert 0.0 < score < 1.0


def test_last_names_use_jaro_winkler_similarity():
    assert compare_last_names("Mehta", "Mehta") == 1.0
    assert compare_last_names("Mehta", "Mehata") > 0.8


def test_exact_date_of_birth_matches():
    dob = date(1980, 3, 12)

    assert compare_dates_of_birth(dob, dob) == 1.0


def test_day_month_transposition_is_recognized():
    assert compare_dates_of_birth(
        date(1980, 3, 12),
        date(1980, 12, 3),
    ) == 0.9


def test_adjacent_date_digit_transposition_is_recognized():
    assert compare_dates_of_birth(
        date(1980, 3, 12),
        date(1980, 3, 21),
    ) == 0.85


def test_unrelated_dates_do_not_match():
    assert compare_dates_of_birth(
        date(1980, 3, 12),
        date(1985, 7, 25),
    ) == 0.0


def test_missing_date_is_not_a_disagreement():
    assert compare_dates_of_birth(None, date(1980, 3, 12)) is None


def test_address_abbreviations_and_punctuation_are_normalized():
    assert normalize_address("12 MG Road") == normalize_address("12 M.G. Rd.")
    assert compare_addresses("12 MG Road", "12 M.G. Rd.") == 1.0


def test_address_case_and_whitespace_are_normalized():
    assert compare_addresses("12 MG ROAD", " 12 mg road ") == 1.0


def test_phone_formatting_does_not_change_match():
    assert compare_phones("+91 98765-43210", "919876543210") == 1.0


def test_different_phone_numbers_do_not_match():
    assert compare_phones("9876543210", "9876543211") == 0.0


def test_national_id_compares_only_last_four_digits():
    assert compare_national_id_suffixes("AB-1234-5678", "99995678") == 1.0


def test_national_id_suffix_disagreement():
    assert compare_national_id_suffixes("12345678", "87654321") == 0.0


def test_national_id_requires_at_least_four_digits():
    assert compare_national_id_suffixes("123", "123") == 0.0


def test_compare_records_returns_field_evidence():
    first = PatientRecord(
        record_id="r1",
        source_system="hospital_a",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
        phone="9876543210",
        national_id="AB12345678",
    )
    second = PatientRecord(
        record_id="r2",
        source_system="clinic_b",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 M.G. Rd.",
        phone="9876543210",
        national_id="XY98785678",
    )

    evidence = compare_records(first, second)

    assert evidence["first_name"] == 1.0
    assert evidence["last_name"] == 1.0
    assert evidence["date_of_birth"] == 1.0
    assert evidence["address"] == 1.0
    assert evidence["phone"] == 1.0
    assert evidence["national_id_suffix"] == 1.0


def test_missing_fields_are_omitted_from_evidence():
    first = PatientRecord("r1", "hospital_a")
    second = PatientRecord("r2", "clinic_b")

    assert compare_records(first, second) == {}


def test_shared_family_phone_is_only_phone_evidence():
    first = PatientRecord(
        "r1",
        "hospital_a",
        first_name="Robert",
        last_name="Mehta",
        phone="9876543210",
    )
    second = PatientRecord(
        "r2",
        "clinic_b",
        first_name="Anita",
        last_name="Mehta",
        phone="9876543210",
    )

    evidence = compare_records(first, second)

    assert evidence["phone"] == 1.0
    assert evidence["first_name"] < 1.0