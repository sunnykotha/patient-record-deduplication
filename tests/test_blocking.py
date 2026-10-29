from datetime import date

import pytest

from patient_record_deduplication.blocking import (
    build_blocks,
    candidate_pairs,
    create_block_key,
    soundex,
)
from patient_record_deduplication.patient_record import PatientRecord


def make_record(record_id, last_name, birth_date=date(1980, 3, 12)):
    return PatientRecord(
        record_id=record_id,
        source_system="test_system",
        last_name=last_name,
        date_of_birth=birth_date,
    )


def test_soundex_encodes_mehta():
    assert soundex("Mehta") == "M300"


def test_soundex_groups_similarly_sounding_names():
    assert soundex("Smith") == soundex("Smyth")


def test_soundex_is_case_insensitive():
    assert soundex("Mehta") == soundex("MEHTA")


def test_soundex_rejects_empty_name():
    with pytest.raises(ValueError):
        soundex(" ")


def test_soundex_rejects_name_without_ascii_letters():
    with pytest.raises(ValueError):
        soundex("12345")


def test_create_block_key_uses_birth_year_and_soundex():
    record = make_record("r1", "Mehta")

    key = create_block_key(record)

    assert key.birth_year == 1980
    assert key.last_name_soundex == "M300"


def test_missing_birth_date_cannot_be_blocked():
    record = make_record("r1", "Mehta", birth_date=None)

    assert create_block_key(record) is None


def test_missing_last_name_cannot_be_blocked():
    record = make_record("r1", " ")

    assert create_block_key(record) is None


def test_build_blocks_groups_records_with_same_key():
    first = make_record("r1", "Smith")
    second = make_record("r2", "Smyth")
    third = make_record("r3", "Jones")

    blocks = build_blocks([first, second, third])

    assert len(blocks) == 2
    assert any(first in group and second in group for group in blocks.values())


def test_build_blocks_excludes_records_without_block_keys():
    valid = make_record("r1", "Mehta")
    missing_dob = make_record("r2", "Mehta", birth_date=None)

    blocks = build_blocks([valid, missing_dob])

    assert sum(len(group) for group in blocks.values()) == 1


def test_candidate_pairs_only_include_records_sharing_a_block():
    first = make_record("r1", "Smith")
    second = make_record("r2", "Smyth")
    third = make_record("r3", "Jones")

    pairs = candidate_pairs([first, second, third])

    assert len(pairs) == 1
    assert {pairs[0][0].record_id, pairs[0][1].record_id} == {"r1", "r2"}


def test_candidate_pairs_do_not_duplicate_pairs():
    records = [
        make_record("r1", "Smith"),
        make_record("r2", "Smyth"),
        make_record("r3", "Smythe"),
    ]

    pairs = candidate_pairs(records)
    pair_ids = [
        frozenset((first.record_id, second.record_id))
        for first, second in pairs
    ]

    assert len(pair_ids) == len(set(pair_ids))


def test_different_birth_years_create_different_blocks():
    first = make_record("r1", "Mehta", date(1980, 3, 12))
    second = make_record("r2", "Mehta", date(1981, 3, 12))

    assert candidate_pairs([first, second]) == []