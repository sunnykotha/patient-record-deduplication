from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from collections.abc import Sequence

from .golden_record import create_golden_record
from .patient_record import PatientRecord


class MergeAction(str, Enum):
    MERGE = "merge"
    UNMERGE = "unmerge"


@dataclass(frozen=True)
class MergeAuditEvent:
    action: MergeAction
    golden_record_id: str
    source_record_ids: tuple[str, ...]
    timestamp: datetime
    reason: str


class MergeService:
    """Manage reversible merges, cross-references, and audit history."""

    def __init__(self) -> None:
        self._active_merges: dict[str, tuple[PatientRecord, ...]] = {}
        self._cross_references: dict[str, str] = {}
        self._audit_log: list[MergeAuditEvent] = []

    @property
    def audit_log(self) -> tuple[MergeAuditEvent, ...]:
        """Return the audit history as an immutable sequence."""
        return tuple(self._audit_log)

    @property
    def cross_references(self) -> dict[str, str]:
        """Return a copy mapping source record IDs to golden record IDs."""
        return dict(self._cross_references)

    def merge(
        self,
        records: Sequence[PatientRecord],
        golden_record_id: str,
        reason: str,
        merged_at: datetime | None = None,
    ) -> PatientRecord:
        """Create a golden record and retain snapshots for reversal."""
        if not records:
            raise ValueError("At least one patient record is required")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Merge reason must be non-empty")

        source_ids = tuple(record.record_id for record in records)

        if len(set(source_ids)) != len(source_ids):
            raise ValueError("Source record IDs must be unique")

        if golden_record_id in source_ids:
            raise ValueError("Golden record ID must differ from source record IDs")

        if golden_record_id in self._active_merges:
            raise ValueError("Golden record already has an active merge")

        if any(record_id in self._cross_references for record_id in source_ids):
            raise ValueError("A source record is already part of an active merge")

        timestamp = merged_at or datetime.now(timezone.utc)
        snapshots = tuple(deepcopy(record) for record in records)

        golden_record = create_golden_record(
            records,
            golden_record_id=golden_record_id,
        )

        self._active_merges[golden_record_id] = snapshots
        for record_id in source_ids:
            self._cross_references[record_id] = golden_record_id

        self._audit_log.append(
            MergeAuditEvent(
                action=MergeAction.MERGE,
                golden_record_id=golden_record_id,
                source_record_ids=source_ids,
                timestamp=timestamp,
                reason=reason.strip(),
            )
        )
        return golden_record

    def unmerge(
        self,
        golden_record_id: str,
        reason: str,
        unmerged_at: datetime | None = None,
    ) -> list[PatientRecord]:
        """Restore original records and retain both audit events."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Unmerge reason must be non-empty")

        snapshots = self._active_merges.get(golden_record_id)
        if snapshots is None:
            raise ValueError("No active merge exists for this golden record")

        restored_records = deepcopy(snapshots)
        source_ids = tuple(record.record_id for record in restored_records)

        del self._active_merges[golden_record_id]
        for record_id in source_ids:
            self._cross_references.pop(record_id, None)

        self._audit_log.append(
            MergeAuditEvent(
                action=MergeAction.UNMERGE,
                golden_record_id=golden_record_id,
                source_record_ids=source_ids,
                timestamp=unmerged_at or datetime.now(timezone.utc),
                reason=reason.strip(),
            )
        )
        return restored_records