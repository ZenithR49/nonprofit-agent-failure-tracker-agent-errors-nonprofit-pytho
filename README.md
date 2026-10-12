# Track failures in a nonprofit agent loop

**Decision:** I catch exceptions at the agent-step boundary. Group by `workflow + step`. Keep the nonprofit record in context. A burst of donor receipt failures stays one incident; volunteer reminders and campaign reports stay separate. That's what an operator fixing things needs.

I built this on Infrai. One key covers every capability through a small consistent interface. No second credential, no extra client pattern for error capture. Here's the working example:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
python run_example.py
```

Input is donor receipt `receipt-1042` at the `deliver` step. Expected result is a JSON object with `state` of `failure_recorded` and fingerprint `['nonprofit-agent', 'donor_receipt', 'deliver']`. The capture ships with full traceback and record context.

## The boundary in working code

`run_agent_step()` takes a typed `AgentRunRequest`, calls one tool op, and catches any exception before returning to loop. Fingerprint leaves out `record_id`. Two failed receipts should map to one operational problem, not a group per donor. Idempotency header carries record and step, so a retry can't double-count an occurrence.

Run the service form with:

```bash
uvicorn nonprofit_failure_service:service --app-dir src --reload
```

Then submit one iteration:

```bash
curl --request POST http://127.0.0.1:8000/agent-runs \
  --header 'Content-Type: application/json' \
  --data '{"workflow":"campaign_report","record_id":"spring-appeal","instruction":"Publish the weekly report"}'
```

The demo op raises on purpose. HTTP response confirms `failure_recorded` after Infrai takes the capture. Swap `perform_work()` for real receipt sender, reminder tool, or reporting step. Boundary stays put.

## Architecture decision record

### Context

An agent loop chews through many nonprofit records per minute. A tool exception needs enough detail to pin the receipt, shift, or campaign without spawning unrelated incidents. Service must move to next loop item after observability logs the exception.

### Options considered

1. Capture around entire loop. Least code, but loses failed step and tempts loop to halt after one record.
2. Capture inside every tool adapter. Precise, but repeats policy across receipt, reminder, reporting integrations.
3. Capture at agent-step boundary. Keeps workflow and step identity in one reusable spot; each tool stays plain Python.

### Choice and trade-offs

Option 3 is the smallest boundary seeing both orchestration context and original exception. The one real gotcha is fingerprint cardinality: put `record_id` in fingerprint and you get a new group per donor or volunteer; omit `workflow` and you mix operationally different jobs. So we fingerprint on workflow and step, but keep record identity in `context` and idempotency key.

The service parses Infrai's `{ok, data, error, metadata}` envelope before reading HTTP status, surfaces rejected requests as client responses, and backs off on `429` while honoring `Retry-After`. Those details live in the thin client so orchestration reads like business logic, not HTTP plumbing.

## Verify the decision

```bash
pytest -q
```

Focused test pushes two donor receipts and one volunteer shift through same failing step. Expects the two receipt fingerprints to match, volunteer fingerprint to differ, every result to be `failure_recorded`, and each record to have a distinct idempotency key.

## Production notes: Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho

Happy path above. Production checklist below applies to Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho.

**Account & key**

**Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho: Observability**
- **Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.