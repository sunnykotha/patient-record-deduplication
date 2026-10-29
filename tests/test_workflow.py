from datetime import date

from patient_record_deduplication.merge import MergeService
from patient_record_deduplication.patient_record import PatientRecord
from patient_record_deduplication.scoring import MatchDecision
from patient_record_deduplication.workflow import DeduplicationWorkflow


def make_record(record_id, **kwargs):
    return PatientRecord(
        record_id=record_id,
        source_system="hospital",
        **kwargs,
    )


def test_workflow_does_not_merge_records_without_auto_merge_decision():
    first = make_record(
        "r1",
        first_name="Alice",
        last_name="Smith",
        date_of_birth=date(1980, 1, 1),
    )
    second = make_record(
        "r2",
        first_name="Zoe",
        last_name="Jones",
        date_of_birth=date(1990, 2, 2),
    )
    service = MergeService()
    workflow = DeduplicationWorkflow(service)

    result = workflow.run([first, second])

    assert result.merged_golden_record_ids == ()
    assert service.audit_log == ()


def test_workflow_records_evaluations_for_generated_candidates():
    first = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
    )
    second = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 M.G. Rd",
    )

    result = DeduplicationWorkflow().run([first, second])

    assert len(result.evaluations) >= 1
    assert result.evaluations[0].first_record_id in {"r1", "r2"}
    assert result.evaluations[0].second_record_id in {"r1", "r2"}
    assert result.evaluations[0].result.decision in set(MatchDecision)


def test_workflow_preserves_source_records():
    first = make_record(
        "r1",
        first_name="Robert",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 MG Road",
    )
    second = make_record(
        "r2",
        first_name="Bob",
        last_name="Mehta",
        date_of_birth=date(1980, 3, 12),
        address="12 M.G. Rd",
    )

    DeduplicationWorkflow().run([first, second])

    assert first.record_id == "r1"
    assert second.record_id == "r2"

def test_overlapping_auto_merge_candidates_are_routed_to_manual_review(monkeypatch):
    from patient_record_deduplication.safety import SafetyResult
    import patient_record_deduplication.workflow as workflow_module

    records = [
        make_record(
            record_id,
            first_name="Robert",
            last_name="Mehta",
            date_of_birth=date(1980, 3, 12),
        )
        for record_id in ("r1", "r2", "r3")
    ]

    monkeypatch.setattr(
        workflow_module,
        "evaluate_match_safety",
        lambda first, second: SafetyResult(
            MatchDecision.AUTO_MERGE,
            ("Test-approved candidate.",),
        ),
    )

    service = MergeService()
    result = DeduplicationWorkflow(service).run(records)

    assert len(result.evaluations) == 3
    assert len(result.merged_golden_record_ids) == 1
    assert len(service.audit_log) == 1

    manual_reviews = [
        evaluation
        for evaluation in result.evaluations
        if evaluation.result.decision == MatchDecision.MANUAL_REVIEW
    ]
    assert len(manual_reviews) == 2
    assert all(
        "manual review" in reason.lower()
        for evaluation in manual_reviews
        for reason in evaluation.result.reasons
    )