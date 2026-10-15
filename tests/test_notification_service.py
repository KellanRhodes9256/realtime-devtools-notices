import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from notification_service import BuildEvent, RealtimeClient, notification_for


def test_failed_build_stays_in_diagnostics():
    event = BuildEvent("acct-1", "clinic-api", "failed", "abc123")
    assert notification_for(event) == {"decision": "diagnostics_only", "project": "clinic-api"}


def test_successful_build_is_notified():
    event = BuildEvent("acct-1", "clinic-api", "succeeded", "abc123")
    assert notification_for(event)["decision"] == "notify"


def test_create_channel_uses_required_contract_fields_only():
    client = RealtimeClient(api_key="test-key")
    calls = []
    client._post = lambda path, payload: calls.append((path, payload)) or {"ok": True}

    client.create_channel("devtools:acct-1")

    assert calls == [("/v1/realtime/channel/create", {"channel": "devtools:acct-1"})]
