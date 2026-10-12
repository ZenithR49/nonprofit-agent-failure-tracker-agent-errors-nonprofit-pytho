"""Run one nonprofit agent step and turn exceptions into grouped incidents."""

from __future__ import annotations

import hashlib
import traceback
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from .infrai_errors import InfraiErrors


class Workflow(str, Enum):
    DONOR_RECEIPT = "donor_receipt"
    VOLUNTEER_REMINDER = "volunteer_reminder"
    CAMPAIGN_REPORT = "campaign_report"


class AgentRunRequest(BaseModel):
    workflow: Workflow
    record_id: str = Field(min_length=1, max_length=120)
    instruction: str = Field(min_length=1, max_length=500)


class AgentRunResult(BaseModel):
    workflow: Workflow
    record_id: str
    state: str
    fingerprint: list[str]


def failure_fingerprint(workflow: Workflow, step: str) -> list[str]:
    """Group operationally identical failures without mixing workflows."""
    return ["nonprofit-agent", workflow.value, step]


def run_agent_step(
    request: AgentRunRequest,
    step: str,
    operation: Callable[[AgentRunRequest], Any],
    errors: InfraiErrors,
) -> AgentRunResult:
    """Run a step; capture a failure once and let the loop move to its next item."""
    fingerprint = failure_fingerprint(request.workflow, step)
    try:
        operation(request)
    except Exception as exc:
        incident_id = hashlib.sha256(
            f"{request.workflow.value}:{request.record_id}:{step}".encode()
        ).hexdigest()
        errors.capture(
            {
                "title": f"{request.workflow.value}/{step} failed",
                "message": f"{type(exc).__name__}: {exc}",
                "level": "error",
                "fingerprint": fingerprint,
                "exception": traceback.format_exc(),
                "context": {
                    "workflow": request.workflow.value,
                    "record_id": request.record_id,
                    "instruction": request.instruction,
                    "step": step,
                },
            },
            idempotency_key=incident_id,
        )
        return AgentRunResult(
            workflow=request.workflow,
            record_id=request.record_id,
            state="failure_recorded",
            fingerprint=fingerprint,
        )

    return AgentRunResult(
        workflow=request.workflow,
        record_id=request.record_id,
        state="completed",
        fingerprint=fingerprint,
    )
