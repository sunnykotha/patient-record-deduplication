from dataclasses import dataclass, field


@dataclass
class MatchScore:
    """A normalized matching score and the evidence supporting it."""

    score: float
    evidence: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("score must be a number")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")

        for field_name, value in self.evidence.items():
            if not isinstance(field_name, str) or not field_name.strip():
                raise ValueError("Evidence field names must be non-empty strings")

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0.0 <= value <= 1.0
            ):
                raise ValueError(
                    "Evidence values must be numbers between 0.0 and 1.0"
                )