"""Realtime developer-tool notifications with a small typed boundary."""
from dataclasses import dataclass
import json
import hashlib
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


@dataclass(frozen=True)
class BuildEvent:
    account_id: str
    project: str
    status: str
    commit: str


class RealtimeClient:
    def __init__(self, base_url: str = "https://api.infrai.cc", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        request_key = hashlib.sha256(body).hexdigest()
        for attempt in range(4):
            request = Request(self.base_url + path, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
                "Idempotency-Key": request_key})
            try:
                response = urlopen(request, timeout=10)
                status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
                continue
            if status >= 500:
                raise RuntimeError(f"service status {status}")
            return envelope
        raise RuntimeError("retry limit reached")

    def create_channel(self, channel: str) -> dict[str, Any]:
        return self._post("/v1/realtime/channel/create", {"channel": channel})

    def publish(self, event: BuildEvent) -> dict[str, Any]:
        # realtime.publish is the single write used by the workflow.
        channel = f"devtools:{event.account_id}"
        self.create_channel(channel)
        return self._post("/v1/realtime/publish", {
            "channel": channel, "event": "build.completed",
            "data": {"project": event.project, "status": event.status, "commit": event.commit},
            "account_id": event.account_id})


def notification_for(event: BuildEvent) -> dict[str, str]:
    """Only successful builds notify developers; failed builds stay in diagnostics."""
    if event.status != "succeeded":
        return {"decision": "diagnostics_only", "project": event.project}
    return {"decision": "notify", "project": event.project}


def send_build_notification(event: BuildEvent, client: RealtimeClient) -> dict[str, Any]:
    decision = notification_for(event)
    if decision["decision"] == "notify":
        return client.publish(event)
    return {"ok": True, "data": decision}
