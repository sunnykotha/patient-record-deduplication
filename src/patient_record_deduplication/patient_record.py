from dataclasses import dataclass, field
from datetime import date, datetime

from .identifier import Identifier


@dataclass
class PatientRecord:
    """A patient record received from one source system."""

    record_id: str
    source_system: str
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    phone: str | None = None
    national_id: str | None = None
    identifiers: list[Identifier] = field(default_factory=list)
    field_verification: dict[str, datetime] = field(default_factory=dict)

    def __post_init__(self):
        for field_name in ("record_id", "source_system"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.date_of_birth is not None and not isinstance(
            self.date_of_birth, date
        ):
            raise ValueError("date_of_birth must be a date or None")

        if not all(isinstance(item, Identifier) for item in self.identifiers):
            raise ValueError("identifiers must contain only Identifier objects")

        for field_name, verified_at in self.field_verification.items():
            if field_name not in {
                "first_name",
                "last_name",
                "date_of_birth",
                "address",
                "phone",
                "national_id",
            }:
                raise ValueError(f"Unsupported verified field: {field_name}")

            if not isinstance(verified_at, datetime):
                raise ValueError(
                    f"Verification timestamp for {field_name} must be a datetime"
                )