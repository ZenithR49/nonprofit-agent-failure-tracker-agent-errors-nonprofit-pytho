from nonprofit_agent.agent_loop import AgentRunRequest, Workflow, run_agent_step


class RecordingErrors:
    def __init__(self) -> None:
        self.captures: list[tuple[dict, str]] = []

    def capture(self, payload: dict, idempotency_key: str) -> dict:
        self.captures.append((payload, idempotency_key))
        return {"event_id": "event-1"}


def fail(_: AgentRunRequest) -> None:
    raise ValueError("downstream delivery rejected")


def test_failures_group_by_workflow_and_step_not_record() -> None:
    errors = RecordingErrors()
    donor_one = AgentRunRequest(
        workflow=Workflow.DONOR_RECEIPT,
        record_id="receipt-1",
        instruction="Send receipt",
    )
    donor_two = donor_one.model_copy(update={"record_id": "receipt-2"})
    volunteer = AgentRunRequest(
        workflow=Workflow.VOLUNTEER_REMINDER,
        record_id="shift-1",
        instruction="Send reminder",
    )

    first = run_agent_step(donor_one, "deliver", fail, errors)  # type: ignore[arg-type]
    second = run_agent_step(donor_two, "deliver", fail, errors)  # type: ignore[arg-type]
    third = run_agent_step(volunteer, "deliver", fail, errors)  # type: ignore[arg-type]

    assert first.state == second.state == third.state == "failure_recorded"
    assert first.fingerprint == second.fingerprint
    assert third.fingerprint != first.fingerprint
    assert errors.captures[0][0]["exception"].startswith("Traceback")
    assert errors.captures[0][1] != errors.captures[1][1]
