from dataclasses import dataclass


@dataclass(frozen=True)
class BlockKey:
    """A key used to group records that may refer to the same person."""

    birth_year: int
    last_name_soundex: str

    def __post_init__(self):
        if isinstance(self.birth_year, bool) or not isinstance(self.birth_year, int):
            raise ValueError("birth_year must be an integer")

        if not 1 <= self.birth_year <= 9999:
            raise ValueError("birth_year must be between 1 and 9999")

        if not isinstance(self.last_name_soundex, str):
            raise ValueError("last_name_soundex must be a string")

        if not self.last_name_soundex.strip():
            raise ValueError("last_name_soundex must not be empty")