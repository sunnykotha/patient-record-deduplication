from dataclasses import dataclass


@dataclass(frozen=True)
class Identifier:
    """Identifier assigned to a patient by a source system."""

    identifier_type: str
    value: str
    source_system: str

    def __post_init__(self):
        for field_name in ("identifier_type", "value", "source_system"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")