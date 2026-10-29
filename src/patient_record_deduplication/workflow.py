from collections.abc import Sequence
from dataclasses import dataclass

from .blocking import candidate_pairs
from .merge import MergeService
from .patient_record import PatientRecord
from .safety import SafetyResult, evaluate_match_safety
from .scoring import MatchDecision


@dataclass(frozen=True)
class PairEvaluation:
    first_record_id: str
    second_record_id: str
    result: SafetyResult


@dataclass(frozen=True)
class WorkflowResult:
    evaluations: tuple[PairEvaluation, ...]
    merged_golden_record_ids: tuple[str, ...]


class DeduplicationWorkflow:
    """Connect candidate generation, safety evaluation, and merge management."""

    def __init__(self, merge_service: MergeService | None = None) -> None:
        self.merge_service = merge_service or MergeService()

    def run(
        self,
        records: Sequence[PatientRecord],
        reason: str = "Approved by deduplication workflow",
    ) -> WorkflowResult:
        evaluations: list[PairEvaluation] = []
        merged_ids: list[str] = []
        already_merged_ids: set[str] = set()

        for first, second in candidate_pairs(list(records)):
            result = evaluate_match_safety(first, second)

            if result.decision == MatchDecision.AUTO_MERGE:
                if (
                    first.record_id in already_merged_ids
                    or second.record_id in already_merged_ids
                ):
                    result = SafetyResult(
                        MatchDecision.MANUAL_REVIEW,
                        (
                            "A source record already participates in an active "
                            "merge; manual review is required.",
                        ),
                    )
                else:
                    golden_id = f"golden:{first.record_id}:{second.record_id}"

                    self.merge_service.merge(
                        [first, second],
                        golden_record_id=golden_id,
                        reason=reason,
                    )
                    merged_ids.append(golden_id)
                    already_merged_ids.update(
                        (first.record_id, second.record_id)
                    )

            evaluations.append(
                PairEvaluation(
                    first_record_id=first.record_id,
                    second_record_id=second.record_id,
                    result=result,
                )
            )

        return WorkflowResult(
            evaluations=tuple(evaluations),
            merged_golden_record_ids=tuple(merged_ids),
        )