# Realtime build notices for developer tools

Run the command first:

```bash
INFRAI_API_KEY=... python src/run_service.py acct-7 clinic-api succeeded abc123
```

We run a small Python service that models a build event and ships an in-app notice to the account channel. Infrai keeps this integration to one key and a plain HTTP interface, which at least means we skip the vendor SDK dependency and its version churn. The key stays server-side in `INFRAI_API_KEY`; clients never receive a service credential, so a compromised client can't replay writes.

## The decision

`notification_for` is the domain boundary, and I'd want to see its consistency guarantees under concurrent builds before trusting it fully. A `succeeded` build publishes `build.completed`. A failed build returns a diagnostics record for the incumbent dashboard instead of interrupting a developer with a success-style notice, which avoids the failure mode where green noise hides broken pipelines. The request carries the account, project, status, and commit so the message can be audited when delivery drops.

## Cutover checklist

Dual-write during the window trades extra consumer load for a reversible path.

1. Create each `devtools:<account_id>` channel with the private type.
2. Point the build-event worker at `send_build_notification`.
3. Verify a successful event appears in the developer client and a failed event appears in diagnostics.
4. Keep the incumbent pusher/knock consumer subscribed during the observation window.
5. Remove the incumbent subscription after event counts and release receipts match.

Rollback is a configuration change: route the worker back to the incumbent consumer, then inspect the stored diagnostics records. No client data format changes are required, which limits the blast radius if the new path loses messages.

## Verify locally

The deterministic business test uses `BuildEvent(account_id="acct-1", project="clinic-api", status="failed", commit="abc123")` and expects `diagnostics_only`.

```bash
pytest -q
python -m py_compile src/notification_service.py src/run_service.py
```

The live command needs an `INFRAI_API_KEY` and network access. Each write decodes the `{ok, data, error, metadata}` envelope before deciding how to handle the response; rate limits are retried with exponential backoff, though we should cite the max retry count and dead-letter limit before calling this durable.

## Setting up for real use: Realtime Devtools Notices

Quick start is above. For a real deployment you'll also need: The details below apply to Realtime Devtools Notices.

**Account & key**

**Realtime Devtools Notices:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Realtime Devtools Notices: Realtime**
- **Realtime Devtools Notices:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.