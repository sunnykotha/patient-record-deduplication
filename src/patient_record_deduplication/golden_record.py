from collections.abc import Sequence

from .identifier import Identifier
from .patient_record import PatientRecord


SURVIVORSHIP_FIELDS = (
    "first_name",
    "last_name",
    "date_of_birth",
    "address",
    "phone",
    "national_id",
)


def _has_value(value: object) -> bool:
    """Return whether a field contains a usable, nonempty value."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def create_golden_record(
    records: Sequence[PatientRecord],
    golden_record_id: str,
    source_system: str = "MPI",
) -> PatientRecord:
    """Build a golden record using field-level verification timestamps.

    For each field, the latest verified nonempty value wins. If no
    nonempty candidate has a verification timestamp, the first
    nonempty value in the input order is used.

    Identifiers are combined in input order without duplicates.
    The input records are not modified.
    """
    if not records:
        raise ValueError("At least one patient record is required")

    if not all(isinstance(record, PatientRecord) for record in records):
        raise ValueError("records must contain only PatientRecord objects")

    selected_values: dict[str, object] = {}
    selected_verification: dict[str, object] = {}

    for field_name in SURVIVORSHIP_FIELDS:
        candidates = [
            (
                record,
                getattr(record, field_name),
                record.field_verification.get(field_name),
            )
            for record in records
            if _has_value(getattr(record, field_name))
        ]

        if not candidates:
            selected_values[field_name] = None
            continue

        verified_candidates = [
            candidate for candidate in candidates if candidate[2] is not None
        ]

        if verified_candidates:
            selected_record, selected_value, verified_at = max(
                verified_candidates,
                key=lambda candidate: candidate[2],
            )
            selected_values[field_name] = selected_value
            selected_verification[field_name] = verified_at
        else:
            selected_record, selected_value, _ = candidates[0]
            selected_values[field_name] = selected_value

    identifiers: list[Identifier] = []
    seen_identifiers: set[Identifier] = set()

    for record in records:
        for identifier in record.identifiers:
            if identifier not in seen_identifiers:
                identifiers.append(identifier)
                seen_identifiers.add(identifier)

    return PatientRecord(
        record_id=golden_record_id,
        source_system=source_system,
        **selected_values,
        identifiers=identifiers,
        field_verification=selected_verification,
    )