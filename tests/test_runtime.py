from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_policy import Event, Policy


def run(policy, token, *events):
    return [policy.dispatch(Event(e, e), approval=token) for e in events]


def test_success_and_duplicate():
    token = object()
    policy = Policy(token)
    assert run(policy, token, "plan", "authorize", "execute", "execute", "succeed") == [
        "accepted",
        "accepted",
        "accepted",
        "duplicate",
        "accepted",
    ]
    assert policy.snapshot().balance == 1
    before = policy.snapshot()
    assert policy.dispatch(Event("fresh", "execute")) == "rejected"
    assert policy.snapshot() == before


def test_faulty_model_counterexample():
    policy = Policy(object())
    assert policy.dispatch(Event("plan", "plan")) == "accepted"
    before = policy.snapshot()
    assert policy.dispatch(Event("execute", "execute")) == "rejected"
    assert policy.snapshot() == before
    assert policy.snapshot().applied == 0


def test_invalid_capability_and_retry():
    token = object()
    policy = Policy(token)
    assert run(policy, token, "execute", "plan") == ["rejected", "accepted"]
    assert policy.dispatch(Event("authorize", "authorize"), approval=object()) == "rejected"
    assert run(policy, token, "authorize", "execute") == ["accepted", "accepted"]
    assert policy.dispatch(Event("authorize", "authorize")) == "rejected"
    assert run(policy, token, "authorize") == ["duplicate"]


def test_compensation_failure_and_retry():
    token = object()
    policy = Policy(token)
    run(policy, token, "plan", "authorize", "execute", "fail", "compensation_fail")
    assert policy.snapshot().phase == "compensation_failed"
    assert policy.snapshot().balance == 1
    assert run(policy, token, "compensate", "compensate") == ["accepted", "duplicate"]
    assert policy.snapshot().balance == 0
    before = policy.snapshot()
    assert run(policy, token, "succeed", "cancel") == ["rejected", "rejected"]
    assert policy.snapshot() == before


@pytest.mark.parametrize("prefix", [[], ["plan"], ["plan", "authorize"]])
def test_cancel_is_terminal(prefix):
    token = object()
    policy = Policy(token)
    run(policy, token, *prefix, "cancel")
    before = policy.snapshot()
    assert policy.dispatch(Event("fresh", "plan")) == "rejected"
    assert policy.snapshot() == before
    assert before.balance == 0


def test_conflicting_id_and_cross_instance_approval():
    token = object()
    policy = Policy(token)
    assert policy.dispatch(Event("x", "plan")) == "accepted"
    assert policy.dispatch(Event("x", "authorize"), approval=token) == "conflict"
    assert policy.dispatch(Event("a", "authorize"), approval=object()) == "rejected"
    assert policy.snapshot().phase == "planned"


def test_concurrent_execution_has_one_effect():
    token = object()
    policy = Policy(token)
    run(policy, token, "plan", "authorize")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: policy.dispatch(Event("execute", "execute")), range(20)))
    assert outcomes.count("accepted") == 1
    assert outcomes.count("duplicate") == 19
    assert policy.snapshot().applied == 1


@pytest.mark.parametrize(
    "key,kind", [("", "plan"), ("x" * 129, "plan"), ("x", "unknown"), (1, "plan")]
)
def test_invalid_events(key, kind):
    with pytest.raises(ValueError):
        Event(key, kind)


def test_missing_capability():
    with pytest.raises(ValueError):
        Policy(None)
