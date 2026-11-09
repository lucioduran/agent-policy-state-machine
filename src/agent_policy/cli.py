"""Run owned synthetic traces. CLI authorization is a demonstration only."""

import argparse
import json
from dataclasses import asdict

from .runtime import Event, Policy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", nargs="+", help="event kinds; forge tests invalid approval")
    args = parser.parse_args()
    approval = object()
    policy = Policy(approval)
    for name in args.events:
        try:
            event = Event(name, "authorize" if name == "forge" else name)
        except ValueError as exc:
            parser.error(str(exc))
        result = policy.dispatch(event, approval=None if name == "forge" else approval)
        print(json.dumps({"event": name, "result": result, **asdict(policy.snapshot())}))


if __name__ == "__main__":
    main()
