"""Run a donor-receipt failure through the same boundary as the service."""

from nonprofit_agent.agent_loop import AgentRunRequest, Workflow, run_agent_step
from nonprofit_agent.infrai_errors import InfraiErrors


def rejected_receipt(_: AgentRunRequest) -> None:
    raise ValueError("receipt delivery address was rejected")


if __name__ == "__main__":
    request = AgentRunRequest(
        workflow=Workflow.DONOR_RECEIPT,
        record_id="receipt-1042",
        instruction="Send the annual donation receipt",
    )
    client = InfraiErrors()
    try:
        result = run_agent_step(request, "deliver", rejected_receipt, client)
        print(result.model_dump_json(indent=2))
    finally:
        client.close()
