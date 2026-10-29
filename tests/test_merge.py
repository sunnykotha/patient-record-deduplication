from datetime import date, datetime, timezone

import pytest

from patient_record_deduplication.identifier import Identifier
from patient_record_deduplication.merge import MergeAction, MergeService
from patient_record_deduplication.patient_record import PatientRecord


def make_record(record_id, **kwargs):
    return PatientRecord(
        record_id=record_id,
        source_system=kwargs.pop("source_system", "hospital"),
        **kwargs,
    )


def test_merge_creates_golden_record_and_cross_references():
    first = make_record("r1", first_name="Robert")
    second = make_record("r2", first_name="Bob")
    service = MergeService()

    golden = service.merge([first, second], "gold-1", "Confirmed duplicate")

    assert golden.record_id == "gold-1"
    assert service.cross_references == {
        "r1": "gold-1",
        "r2": "gold-1",
    }


def test_merge_creates_audit_event_with_reason_and_timestamp():
    first = make_record("r1", first_name="Robert")
    second = make_record("r2", first_name="Bob")
    timestamp = datetime(2026, 1, 2, tzinfo=timezone.utc)
    service = MergeService()

    service.merge(
        [first, second],
        "gold-1",
        "Reviewed and confirmed",
        merged_at=timestamp,
    )

    event = service.audit_log[0]
    assert event.action == MergeAction.MERGE
    assert event.source_record_ids == ("r1", "r2")
    assert event.timestamp == timestamp
    assert event.reason == "Reviewed and confirmed"


def test_unmerge_restores_original_records_and_removes_active_references():
    first = make_record("r1", first_name="Robert", phone="111")
    second = make_record("r2", first_name="Bob", phone="222")
    service = MergeService()
    service.merge([first, second], "gold-1", "Confirmed duplicate")

    restored = service.unmerge("gold-1", "Merge was incorrect")

    assert [record.record_id for record in restored] == ["r1", "r2"]
    assert [record.first_name for record in restored] == ["Robert", "Bob"]
    assert [record.phone for record in restored] == ["111", "222"]
    assert service.cross_references == {}


def test_unmerge_keeps_both_merge_and_unmerge_audit_events():
    first = make_record("r1", first_name="Robert")
    second = make_record("r2", first_name="Bob")
    service = MergeService()
    service.merge([first, second], "gold-1", "Confirmed duplicate")
    service.unmerge("gold-1", "Identity conflict found")

    assert [event.action for event in service.audit_log] == [
        MergeAction.MERGE,
        MergeAction.UNMERGE,
    ]
    assert service.audit_log[1].reason == "Identity conflict found"


def test_merge_does_not_modify_original_records():
    first = make_record("r1", first_name="Robert")
    second = make_record("r2", first_name="Bob")
    service = MergeService()

    service.merge([first, second], "gold-1", "Confirmed duplicate")

    assert first.record_id == "r1"
    assert first.first_name == "Robert"
    assert second.record_id == "r2"
    assert second.first_name == "Bob"


def test_unmerge_rejects_unknown_golden_record():
    service = MergeService()

    with pytest.raises(ValueError, match="No active merge"):
        service.unmerge("missing", "Correction")


def test_merge_rejects_empty_reason():
    service = MergeService()
    records = [make_record("r1", first_name="Robert")]

    with pytest.raises(ValueError, match="reason"):
        service.merge(records, "gold-1", "  ")


def test_merge_preserves_identifiers_on_golden_record():
    identifier1 = Identifier("MRN", "111", "hospital")
    identifier2 = Identifier("MRN", "222", "clinic")
    first = make_record("r1", identifiers=[identifier1])
    second = make_record("r2", identifiers=[identifier2])
    service = MergeService()

    golden = service.merge([first, second], "gold-1", "Confirmed duplicate")

    assert golden.identifiers == [identifier1, identifier2]