"""HTTP entry point for one observable nonprofit agent iteration."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from nonprofit_agent.agent_loop import AgentRunRequest, AgentRunResult, run_agent_step
from nonprofit_agent.infrai_errors import InfraiError, InfraiErrors

service = FastAPI(title="Nonprofit agent failure tracker")


def perform_work(request: AgentRunRequest) -> None:
    """Stand-in for the receipt, reminder, or report tool call."""
    raise ValueError(f"tool could not complete record {request.record_id}")


@service.post("/agent-runs", response_model=AgentRunResult)
def run_iteration(request: AgentRunRequest) -> AgentRunResult:
    errors = InfraiErrors()
    try:
        return run_agent_step(request, "deliver", perform_work, errors)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code}) from exc
    finally:
        errors.close()
