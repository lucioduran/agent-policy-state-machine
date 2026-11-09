"""Serialized execution with capability identity and accepted-event deduplication."""

from dataclasses import dataclass
from threading import Lock

KINDS = frozenset(
    {"plan", "authorize", "execute", "succeed", "fail", "compensate", "compensation_fail", "cancel"}
)
TERMINAL = frozenset({"done", "rolled_back", "cancelled"})


@dataclass(frozen=True)
class Event:
    key: str
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key or len(self.key) > 128:
            raise ValueError("event key must contain 1 through 128 characters")
        if self.kind not in KINDS:
            raise ValueError("unknown event kind")


@dataclass(frozen=True)
class Snapshot:
    phase: str
    authorized: bool
    applied: int
    reverted: int
    balance: int
    seen: tuple[str, ...]


class Policy:
    """One operation; approval is an opaque object supplied by the trusted caller.

    The synthetic ledger is internal, so rejected calls cannot trigger an effect.
    This is not a security boundary against code with access to Python internals.
    """

    def __init__(self, approval: object) -> None:
        if approval is None:
            raise ValueError("approval capability cannot be None")
        self._approval = approval
        self._lock = Lock()
        self._phase = "new"
        self._authorized = False
        self._applied = 0
        self._reverted = 0
        self._seen: dict[str, str] = {}

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(
                self._phase,
                self._authorized,
                self._applied,
                self._reverted,
                self._applied - self._reverted,
                tuple(sorted(self._seen)),
            )

    def dispatch(self, event: Event, *, approval: object = None) -> str:
        with self._lock:
            # Authenticate even a duplicate, before consulting the accepted journal.
            if event.kind == "authorize" and approval is not self._approval:
                return "rejected"
            if event.key in self._seen:
                return "duplicate" if self._seen[event.key] == event.kind else "conflict"
            if self._phase in TERMINAL:
                return "rejected"
            phase, kind = self._phase, event.kind
            if kind == "plan" and phase == "new":
                self._phase = "planned"
            elif kind == "authorize" and phase == "planned":
                self._authorized = True
                self._phase = "authorized"
            elif kind == "execute" and phase == "authorized" and self._authorized:
                self._applied += 1
                self._phase = "executing"
            elif kind == "succeed" and phase == "executing":
                self._phase = "done"
            elif kind == "fail" and phase == "executing":
                self._phase = "compensating"
            elif kind == "compensation_fail" and phase == "compensating":
                self._phase = "compensation_failed"
            elif kind == "compensate" and phase in {"compensating", "compensation_failed"}:
                self._reverted += 1
                self._phase = "rolled_back"
            elif kind == "cancel" and phase in {"new", "planned", "authorized"}:
                self._phase = "cancelled"
            else:
                return "rejected"
            self._seen[event.key] = kind
            return "accepted"
