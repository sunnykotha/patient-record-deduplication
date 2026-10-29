import re
import unicodedata
from datetime import date

from rapidfuzz.distance import JaroWinkler

from .patient_record import PatientRecord


_NICKNAMES = {
    "bob": "robert",
    "bobby": "robert",
    "rob": "robert",
    "robbie": "robert",
    "bill": "william",
    "billy": "william",
    "will": "william",
    "liz": "elizabeth",
    "lizzy": "elizabeth",
    "beth": "elizabeth",
    "kate": "katherine",
    "kathy": "katherine",
    "cathy": "katherine",
    "mike": "michael",
    "mick": "michael",
    "dick": "richard",
    "rick": "richard",
    "jim": "james",
    "jimmy": "james",
}

_ADDRESS_WORDS = {
    "rd": "road",
    "st": "street",
    "str": "street",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "ln": "lane",
    "dr": "drive",
    "apt": "apartment",
    "ste": "suite",
}


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return value.casefold().strip()


def _similarity(first: str, second: str) -> float:
    first = _normalize_text(first)
    second = _normalize_text(second)

    if not first or not second:
        return 0.0

    return JaroWinkler.normalized_similarity(first, second)


def compare_first_names(first: str, second: str) -> float:
    """Compare first names, recognizing configured nickname equivalents."""
    first_normalized = _normalize_text(first)
    second_normalized = _normalize_text(second)

    if not first_normalized or not second_normalized:
        return 0.0

    first_canonical = _NICKNAMES.get(first_normalized, first_normalized)
    second_canonical = _NICKNAMES.get(second_normalized, second_normalized)

    if first_canonical == second_canonical:
        return 1.0

    return _similarity(first_normalized, second_normalized)


def compare_last_names(first: str, second: str) -> float:
    """Compare surnames using Jaro-Winkler similarity."""
    return _similarity(first, second)


def compare_dates_of_birth(
    first: date | None,
    second: date | None,
) -> float | None:
    """Compare dates of birth, including common transposition errors.

    Returns None when either date is missing, 1.0 for exact agreement,
    0.9 for a valid day/month swap, 0.85 for one adjacent digit swap,
    and 0.0 for other disagreements.
    """
    if first is None or second is None:
        return None

    if first == second:
        return 1.0

    if (
        first.year == second.year
        and first.day == second.month
        and first.month == second.day
    ):
        return 0.9

    first_digits = first.strftime("%Y%m%d")
    second_digits = second.strftime("%Y%m%d")

    for index in range(len(first_digits) - 1):
        swapped = (
            first_digits[:index]
            + first_digits[index + 1]
            + first_digits[index]
            + first_digits[index + 2:]
        )

        if swapped != second_digits:
            continue

        try:
            date(
                int(swapped[:4]),
                int(swapped[4:6]),
                int(swapped[6:8]),
            )
        except ValueError:
            continue

        return 0.85

    return 0.0


def normalize_address(address: str) -> str:
    """Normalize punctuation, case, and common street abbreviations."""
    normalized = _normalize_text(address).replace(".", "")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    words = normalized.split()

    return " ".join(_ADDRESS_WORDS.get(word, word) for word in words)


def compare_addresses(first: str, second: str) -> float:
    """Compare normalized addresses using Jaro-Winkler similarity."""
    first_normalized = normalize_address(first)
    second_normalized = normalize_address(second)

    if not first_normalized or not second_normalized:
        return 0.0

    return JaroWinkler.normalized_similarity(
        first_normalized,
        second_normalized,
    )


def normalize_phone(phone: str) -> str:
    """Keep digits only for phone comparison."""
    return "".join(character for character in phone if character.isdigit())


def compare_phones(first: str, second: str) -> float:
    """Compare normalized phone numbers."""
    first_normalized = normalize_phone(first)
    second_normalized = normalize_phone(second)

    if not first_normalized or not second_normalized:
        return 0.0

    if first_normalized == second_normalized:
        return 1.0

    return 0.0


def compare_national_id_suffixes(first: str, second: str) -> float:
    """Compare only the last four digits of two national IDs."""
    first_digits = "".join(c for c in first if c.isdigit())
    second_digits = "".join(c for c in second if c.isdigit())

    if len(first_digits) < 4 or len(second_digits) < 4:
        return 0.0

    return 1.0 if first_digits[-4:] == second_digits[-4:] else 0.0


def compare_records(
    first: PatientRecord,
    second: PatientRecord,
) -> dict[str, float]:
    """Return available field-comparison evidence for two records.

    Missing values are omitted rather than treated as disagreements.
    This function does not decide whether records should be merged.
    """
    evidence: dict[str, float] = {}

    if first.first_name and second.first_name:
        evidence["first_name"] = compare_first_names(
            first.first_name,
            second.first_name,
        )

    if first.last_name and second.last_name:
        evidence["last_name"] = compare_last_names(
            first.last_name,
            second.last_name,
        )

    dob_score = compare_dates_of_birth(
        first.date_of_birth,
        second.date_of_birth,
    )
    if dob_score is not None:
        evidence["date_of_birth"] = dob_score

    if first.address and second.address:
        evidence["address"] = compare_addresses(
            first.address,
            second.address,
        )

    if first.phone and second.phone:
        evidence["phone"] = compare_phones(first.phone, second.phone)

    if first.national_id and second.national_id:
        evidence["national_id_suffix"] = compare_national_id_suffixes(
            first.national_id,
            second.national_id,
        )

    return evidence