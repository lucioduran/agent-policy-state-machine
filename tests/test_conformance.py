import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("replay", ROOT / "scripts/replay.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def test_all_model_edges_conform():
    observations = replay.replay(ROOT / "evidence")
    assert len(observations) == 981
    assert {item["result"] for item in observations} == {"accepted", "rejected", "duplicate"}
    assert {item["snapshot"]["phase"] for item in observations} >= {
        "done",
        "cancelled",
        "rolled_back",
        "compensation_failed",
    }


@pytest.mark.parametrize("mutation", ["remove_edge", "duplicate_edge", "bad_node", "garbage"])
def test_graph_corruption_is_rejected(tmp_path, mutation):
    lines = (ROOT / "evidence/states.dot").read_text().splitlines()
    edge = next(i for i, line in enumerate(lines) if " -> " in line)
    if mutation == "remove_edge":
        lines.pop(edge)
    elif mutation == "duplicate_edge":
        lines.insert(edge, lines[edge])
    elif mutation == "bad_node":
        lines[edge] = lines[edge].replace(lines[edge].split()[0], "999", 1)
    else:
        lines.append("unrecognized syntax")
    path = tmp_path / "broken.dot"
    path.write_text("\n".join(lines))
    with pytest.raises(ValueError):
        replay.parse_graph(path)


def test_runtime_mutation_is_detected(monkeypatch):
    original = replay.Policy.dispatch

    def broken(self, event, **kwargs):
        result = original(self, event, **kwargs)
        if event.kind == "execute" and result == "accepted":
            self._applied += 1
        return result

    monkeypatch.setattr(replay.Policy, "dispatch", broken)
    with pytest.raises(ValueError, match="conformance mismatch"):
        replay.replay(ROOT / "evidence")


def test_model_observation_mutation_is_detected(tmp_path):
    for name in ["states.dot", "correct.log", "faulty.log"]:
        content = (ROOT / "evidence" / name).read_text()
        if name == "states.dot":
            content = content.replace("applied = 1", "applied = 0")
        (tmp_path / name).write_text(content)
    with pytest.raises(ValueError, match="conformance mismatch"):
        replay.replay(tmp_path)


def test_saved_observations_match_runtime():
    saved = [
        json.loads(line)
        for line in (ROOT / "evidence/runtime-edges.jsonl").read_text().splitlines()
    ]
    assert saved == replay.replay(ROOT / "evidence")
