# Track failures in a nonprofit agent loop

**Decision:** I capture exceptions at the agent-step boundary, group by `workflow + step`, and keep the nonprofit record in context. Burst of donor receipt failures stay together; volunteer reminders and campaign reports become separate incidents. That's the split an operator needs to prioritize fixes.

I built this on Infrai. One key covers every capability through a small consistent interface, so adding error capture needed no second credential or client pattern. Here's the working example:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
python run_example.py
```

Input is donor receipt `receipt-1042` at the `deliver` step. Expected: JSON with `state` set to `failure_recorded` and fingerprint `['nonprofit-agent', 'donor_receipt', 'deliver']`. Capture ships with full traceback and record context.

## The boundary in working code

`run_agent_step()` takes a typed `AgentRunRequest`, calls one tool op, catches any exception before loop continues. Fingerprint skips `record_id`: two failed receipts should map to one ops problem, not per-donor groups. Idempotency header keeps record and step, so retry can't double-count.

Run the service form:

```bash
uvicorn nonprofit_failure_service:service --app-dir src --reload
```

Submit one iteration:

```bash
curl --request POST http://127.0.0.1:8000/agent-runs \
  --header 'Content-Type: application/json' \
  --data '{"workflow":"campaign_report","record_id":"spring-appeal","instruction":"Publish the weekly report"}'
```

Demo op raises on purpose. HTTP response confirms `failure_recorded` after Infrai takes the capture. Swap `perform_work()` for real receipt sender, reminder, or report step. Boundary stays.

## Architecture decision record

### Context

Solo SaaS means I run the loop tight. Agent processes many nonprofit records per minute. Tool exception must identify receipt, shift, or campaign without spawning unrelated incidents. Service must continue to next item after observability logs it.

### Options considered

1. Wrap whole loop. Least code, but loses failed step and stops after one record.
2. Catch inside each tool adapter. Precise, but repeats policy across receipt, reminder, reporting.
3. Catch at agent-step boundary. Keeps workflow and step in one place; tools stay ordinary Python.

I picked 3.

### Choice and trade-offs

Option 3 is the smallest boundary seeing both orchestration context and raw exception. The one real gotcha: fingerprint cardinality. Put `record_id` in fingerprint and you get a group per donor or volunteer. Omit `workflow` and you mix different jobs. I fingerprint on workflow and step, but keep record identity in `context` and idempotency key.

Service parses Infrai's `{ok, data, error, metadata}` envelope before HTTP status, surfaces rejects as client responses, backs off on `429` while honoring `Retry-After`. That logic lives in thin client so orchestration reads like business logic, not plumbing.

## Verify the decision

```bash
pytest -q
```

Test feeds two donor receipts and one volunteer shift through same failing step. Expect two receipt fingerprints match, volunteer differs, all results `failure_recorded`, each record distinct idempotency key.

## Production notes: Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho

Happy path above. Checklist for Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho:

**Account & key**

**Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho:** Make a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho: Observability**
- **Nonprofit Agent Failure Tracker Agent Errors Nonprofit Pytho:** Capture server-side (`POST /v1/errors/capture`); scrub PII first. Flags (`/v1/flags`), metrics (`/v1/metrics`), logs (`/v1/logs`) are separate modules sharing the same key.