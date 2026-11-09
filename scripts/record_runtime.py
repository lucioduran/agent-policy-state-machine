"""Record actual conformance execution metadata, under the benchmark lock."""

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
started = datetime.now(timezone.utc).isoformat()
before = time.perf_counter()
command = [sys.executable, "scripts/replay.py", "--record"]
result = subprocess.run(command, capture_output=True, text=True)
record = {
    "started_utc": started,
    "elapsed_seconds": time.perf_counter() - before,
    "command": command,
    "returncode": result.returncode,
    "stdout": result.stdout,
    "stderr": result.stderr,
    "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "python": sys.version,
    "hardware_reference": "evidence/measurement.json",
    "sha256": {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in [
            "scripts/replay.py",
            "scripts/record_runtime.py",
            "src/agent_policy/runtime.py",
            "evidence/states.dot",
        ]
    },
}
(root / "evidence/runtime-measurement.json").write_text(json.dumps(record, indent=2) + "\n")
print(result.stdout, end="")
print(result.stderr, end="", file=sys.stderr)
raise SystemExit(result.returncode)
