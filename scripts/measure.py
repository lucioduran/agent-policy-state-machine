"""Run bounded TLC checks; call through the host's benchmark lock wrapper."""

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence")
    destination.mkdir(parents=True, exist_ok=True)
    jar = ROOT / ".tools/tla2tools.jar"
    records = []
    for name, config in [("correct", "Policy"), ("faulty", "Faulty")]:
        command = [
            "java",
            "-XX:ActiveProcessorCount=1",
            "-Xmx512m",
            "-cp",
            str(jar),
            "tlc2.TLC",
            "-workers",
            "1",
            "-seed",
            "21",
            "-fp",
            "0",
            "-metadir",
            str(ROOT / "work" / name),
            "-config",
            str(ROOT / "formal" / f"{config}.cfg"),
        ]
        if name == "correct":
            command += ["-dump", "dot", str(destination.resolve() / "states.dot")]
        command += [str(ROOT / "formal/Policy.tla")]
        started = datetime.now(timezone.utc).isoformat()
        before = time.perf_counter()
        result = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        elapsed = time.perf_counter() - before
        (destination / f"{name}.log").write_text(result.stdout)
        records.append(
            dict(
                name=name,
                command=command,
                started_utc=started,
                elapsed_seconds=elapsed,
                returncode=result.returncode,
            )
        )
    files = [
        jar,
        *sorted((ROOT / "formal").glob("*")),
        *sorted((ROOT / "src/agent_policy").glob("*.py")),
        Path(__file__),
        ROOT / "uv.lock",
    ]
    metadata = {
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "worktree_status": subprocess.check_output(["git", "status", "--porcelain"], text=True),
        "platform": platform.platform(),
        "python": sys.version,
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "hardware": subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string", "hw.memsize"], text=True
        ),
        "java": subprocess.run(["java", "-version"], capture_output=True, text=True).stderr,
        "runs": records,
        "sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        },
    }
    (destination / "measurement.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(records, indent=2))
    if records[0]["returncode"] != 0 or records[1]["returncode"] != 12:
        raise SystemExit("Unexpected TLC result; inspect preserved logs")


if __name__ == "__main__":
    main()
