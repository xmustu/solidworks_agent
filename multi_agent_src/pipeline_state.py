from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PipelineState(str, Enum):
    REQUIREMENT_CLARIFYING = "REQUIREMENT_CLARIFYING"
    PLAN_GENERATING = "PLAN_GENERATING"
    PART_MODELING = "PART_MODELING"
    PART_EXECUTING = "PART_EXECUTING"
    PART_VALIDATING = "PART_VALIDATING"
    ASSEMBLY_MODELING = "ASSEMBLY_MODELING"
    ASSEMBLY_EXECUTING = "ASSEMBLY_EXECUTING"
    FAILED_RECOVERABLE = "FAILED_RECOVERABLE"
    FAILED_FATAL = "FAILED_FATAL"
    DONE = "DONE"


@dataclass(frozen=True)
class StatePolicy:
    state: PipelineState
    inputs: tuple[str, ...]
    success_state: PipelineState
    failure_state: PipelineState
    max_retries: int
    fallback_state: PipelineState | None = None


DEFAULT_STATE_POLICIES: dict[PipelineState, StatePolicy] = {
    PipelineState.REQUIREMENT_CLARIFYING: StatePolicy(
        state=PipelineState.REQUIREMENT_CLARIFYING,
        inputs=("user_requirement",),
        success_state=PipelineState.PLAN_GENERATING,
        failure_state=PipelineState.FAILED_FATAL,
        max_retries=0,
    ),
    PipelineState.PLAN_GENERATING: StatePolicy(
        state=PipelineState.PLAN_GENERATING,
        inputs=("requirement_payload", "workspace"),
        success_state=PipelineState.PART_MODELING,
        failure_state=PipelineState.FAILED_RECOVERABLE,
        max_retries=3,
        fallback_state=PipelineState.REQUIREMENT_CLARIFYING,
    ),
    PipelineState.PART_MODELING: StatePolicy(
        state=PipelineState.PART_MODELING,
        inputs=("full_plan", "part_spec"),
        success_state=PipelineState.PART_VALIDATING,
        failure_state=PipelineState.FAILED_RECOVERABLE,
        max_retries=5,
        fallback_state=PipelineState.PLAN_GENERATING,
    ),
    PipelineState.PART_EXECUTING: StatePolicy(
        state=PipelineState.PART_EXECUTING,
        inputs=("code_file",),
        success_state=PipelineState.PART_VALIDATING,
        failure_state=PipelineState.PART_MODELING,
        max_retries=5,
        fallback_state=PipelineState.PART_MODELING,
    ),
    PipelineState.PART_VALIDATING: StatePolicy(
        state=PipelineState.PART_VALIDATING,
        inputs=("full_plan", "part_spec", "generated_code"),
        success_state=PipelineState.ASSEMBLY_MODELING,
        failure_state=PipelineState.PART_MODELING,
        max_retries=5,
        fallback_state=PipelineState.PART_MODELING,
    ),
    PipelineState.ASSEMBLY_MODELING: StatePolicy(
        state=PipelineState.ASSEMBLY_MODELING,
        inputs=("assembly_plan", "part_results"),
        success_state=PipelineState.ASSEMBLY_EXECUTING,
        failure_state=PipelineState.FAILED_RECOVERABLE,
        max_retries=5,
        fallback_state=PipelineState.PART_MODELING,
    ),
    PipelineState.ASSEMBLY_EXECUTING: StatePolicy(
        state=PipelineState.ASSEMBLY_EXECUTING,
        inputs=("assembly_code_file",),
        success_state=PipelineState.DONE,
        failure_state=PipelineState.ASSEMBLY_MODELING,
        max_retries=5,
        fallback_state=PipelineState.ASSEMBLY_MODELING,
    ),
    PipelineState.FAILED_RECOVERABLE: StatePolicy(
        state=PipelineState.FAILED_RECOVERABLE,
        inputs=("error", "state_context"),
        success_state=PipelineState.PLAN_GENERATING,
        failure_state=PipelineState.FAILED_FATAL,
        max_retries=1,
    ),
    PipelineState.FAILED_FATAL: StatePolicy(
        state=PipelineState.FAILED_FATAL,
        inputs=("error",),
        success_state=PipelineState.FAILED_FATAL,
        failure_state=PipelineState.FAILED_FATAL,
        max_retries=0,
    ),
    PipelineState.DONE: StatePolicy(
        state=PipelineState.DONE,
        inputs=("outputs",),
        success_state=PipelineState.DONE,
        failure_state=PipelineState.DONE,
        max_retries=0,
    ),
}
