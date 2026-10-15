import json
import sys
from notification_service import BuildEvent, RealtimeClient, send_build_notification


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: python src/run_service.py ACCOUNT PROJECT STATUS COMMIT")
    event = BuildEvent(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    result = send_build_notification(event, RealtimeClient())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
