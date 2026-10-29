import unicodedata
from itertools import combinations

from .block_key import BlockKey
from .patient_record import PatientRecord


_SOUNDEX_GROUPS = {
    **dict.fromkeys("BFPV", "1"),
    **dict.fromkeys("CGJKQSXZ", "2"),
    **dict.fromkeys("DT", "3"),
    **dict.fromkeys("L", "4"),
    **dict.fromkeys("MN", "5"),
    **dict.fromkeys("R", "6"),
}


def soundex(last_name: str) -> str:
    """Return a four-character Soundex code for a last name."""
    if not isinstance(last_name, str) or not last_name.strip():
        raise ValueError("last_name must be a non-empty string")

    normalized = unicodedata.normalize("NFKD", last_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").upper()
    letters = "".join(character for character in ascii_name if character.isalpha())

    if not letters:
        raise ValueError("last_name must contain at least one ASCII letter")

    first_letter = letters[0]
    digits = []
    previous_code = _SOUNDEX_GROUPS.get(first_letter, "")

    for character in letters[1:]:
        if character in "HW":
            continue

        code = _SOUNDEX_GROUPS.get(character)

        if code is None:
            previous_code = ""
            continue

        if code != previous_code:
            digits.append(code)

        previous_code = code

    return (first_letter + "".join(digits) + "000")[:4]


def create_block_key(record: PatientRecord) -> BlockKey | None:
    """Create a blocking key, or None when required fields are missing."""
    if record.date_of_birth is None:
        return None

    if not record.last_name or not record.last_name.strip():
        return None

    return BlockKey(
        birth_year=record.date_of_birth.year,
        last_name_soundex=soundex(record.last_name),
    )


def build_blocks(
    records: list[PatientRecord],
) -> dict[BlockKey, list[PatientRecord]]:
    """Group records sharing a birth-year and last-name Soundex key."""
    blocks: dict[BlockKey, list[PatientRecord]] = {}

    for record in records:
        key = create_block_key(record)

        if key is not None:
            blocks.setdefault(key, []).append(record)

    return blocks


def candidate_pairs(
    records: list[PatientRecord],
) -> list[tuple[PatientRecord, PatientRecord]]:
    """Return unique record pairs that share a blocking key."""
    pairs = []

    for block_records in build_blocks(records).values():
        pairs.extend(combinations(block_records, 2))

    return pairs