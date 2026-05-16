from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str]) -> bool:
    print(f"\n== {name} ==")
    env = os.environ.copy()
    pythonpath_parts = [str(ROOT / "src")]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        print(f"FAILED: {name}")
        return False
    print(f"PASSED: {name}")
    return True


def main() -> int:
    python = sys.executable
    steps = [
        ("compile", [python, "-m", "compileall", "src", "tests", "scripts"]),
        ("unit tests", [python, "-m", "pytest", "-q"]),
        ("mock evals", [python, "scripts/run_mock_evals.py"]),
        (
            "app factory import",
            [
                python,
                "-c",
                "from graph_harness.app.main import create_app; "
                "app=create_app(); print(app.title, len(app.routes))",
            ],
        ),
        ("live smoke", [python, "scripts/live_smoke.py"]),
    ]
    ok = True
    for name, command in steps:
        ok = run_step(name, command) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
