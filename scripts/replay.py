"""Replay every saved TLC graph edge through the runtime, without Java or network."""

import argparse
import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import asdict
from pathlib import Path

from agent_policy import Event, Policy

ROOT = Path(__file__).resolve().parents[1]
EVENTS = {
    "plan",
    "authorize",
    "forge",
    "execute",
    "succeed",
    "fail",
    "compensate",
    "compensation_fail",
    "cancel",
}


def parse_graph(path):
    nodes, edges = {}, []
    for line in path.read_text().splitlines():
        edge = re.fullmatch(r"(-?\d+) -> (-?\d+) \[.*\];", line)
        node = re.fullmatch(r'(-?\d+) \[label=("(?:\\.|[^"\\])*")(?:,style = filled)?\];?', line)
        if edge:
            edges.append(edge.groups())
        elif node:
            fields = {}
            for item in json.loads(node[2]).split("\n"):
                key, value = item.removeprefix("/\\ ").split(" = ", 1)
                if value.startswith("{"):
                    fields[key] = sorted(json.loads("[" + value[1:-1] + "]"))
                else:
                    fields[key] = json.loads(value.lower() if value in {"TRUE", "FALSE"} else value)
            if set(fields) != {
                "phase",
                "authorized",
                "applied",
                "reverted",
                "seen",
                "event",
                "result",
            }:
                raise ValueError("unexpected model state fields")
            if node[1] in nodes:
                raise ValueError("duplicate graph node")
            nodes[node[1]] = fields
        elif re.fullmatch(r"\{rank = same; (?:-?\d+;)+\}", line):
            continue
        elif line not in {
            "strict digraph DiskGraph {",
            "nodesep=0.35;",
            "subgraph cluster_graph {",
            'color="white";',
            "}",
            "",
        }:
            raise ValueError(f"unrecognized DOT line: {line}")
    if not nodes or not edges or len(set(edges)) != len(edges):
        raise ValueError("empty or duplicate graph")
    adjacency = defaultdict(list)
    for source, target in edges:
        if source not in nodes or target not in nodes:
            raise ValueError("dangling graph edge")
        adjacency[source].append(target)
    for source in nodes:
        if (
            len(adjacency[source]) != len(EVENTS)
            or {nodes[t]["event"] for t in adjacency[source]} != EVENTS
        ):
            raise ValueError("incomplete event coverage")
    initial = [key for key, value in nodes.items() if value["event"] == "init"]
    if len(initial) != 1:
        raise ValueError("expected one initial state")
    paths = {initial[0]: []}
    queue = deque(initial)
    while queue:
        source = queue.popleft()
        for target in adjacency[source]:
            if target not in paths:
                paths[target] = paths[source] + [nodes[target]["event"]]
                queue.append(target)
    if len(paths) != len(nodes):
        raise ValueError("unreachable graph node")
    return nodes, edges, paths


def dispatch(policy, token, event):
    return policy.dispatch(
        Event(event, "authorize" if event == "forge" else event),
        approval=None if event == "forge" else token,
    )


def compare(policy, model):
    observed = asdict(policy.snapshot())
    observed["seen"] = list(observed["seen"])
    for key, value in observed.items():
        expected = model["applied"] - model["reverted"] if key == "balance" else model[key]
        if value != expected:
            raise ValueError(f"conformance mismatch: {key}: {value!r} != {expected!r}")
    return observed


def replay(directory):
    nodes, edges, paths = parse_graph(directory / "states.dot")
    log = (directory / "correct.log").read_text()
    counts = re.search(r"(\d+) states generated, (\d+) distinct states found, 0 states left", log)
    if not counts or int(counts[2]) != len(nodes) or int(counts[1]) != len(edges) + 1:
        raise ValueError("graph counts do not match completed TLC output")
    if "Model checking completed. No error has been found." not in log:
        raise ValueError("TLC did not report success")
    observations = []
    for source, target in edges:
        token = object()
        policy = Policy(token)
        for event in paths[source]:
            dispatch(policy, token, event)
        compare(policy, nodes[source])
        event = nodes[target]["event"]
        result = dispatch(policy, token, event)
        if result != nodes[target]["result"]:
            raise ValueError("outcome mismatch")
        observed = compare(policy, nodes[target])
        observations.append(
            dict(
                source=source,
                target=target,
                prefix=paths[source],
                event=event,
                result=result,
                snapshot=observed,
            )
        )
    faulty = (directory / "faulty.log").read_text()
    counterexample = re.findall(r'^/\\ event = "([^\"]+)"$', faulty, flags=re.MULTILINE)
    if (
        counterexample != ["init", "plan", "execute"]
        or "Invariant Authorization is violated" not in faulty
    ):
        raise ValueError("unexpected faulty-model counterexample")
    policy = Policy(object())
    outcomes = [dispatch(policy, None, event) for event in counterexample[1:]]
    if outcomes != ["accepted", "rejected"] or policy.snapshot().applied != 0:
        raise ValueError("counterexample regression failed")
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "evidence"
    if not args.record:
        manifest = json.loads((directory / "manifest.json").read_text())
        for name, expected in manifest.items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
                raise ValueError(f"hash mismatch: {name}")
    observations = replay(directory)
    serialized = "".join(json.dumps(item, sort_keys=True) + "\n" for item in observations)
    destination = directory / "runtime-edges.jsonl"
    if args.record:
        destination.write_text(serialized)
    elif destination.read_text() != serialized:
        raise ValueError("saved runtime observations differ from replay")
    print(json.dumps({"conforming_edges": len(observations), "counterexample_blocked": True}))


if __name__ == "__main__":
    main()
