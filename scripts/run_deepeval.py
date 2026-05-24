from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "anthropic/claude-3-5-sonnet-20241022"


def main() -> int:
    deepeval_bin = shutil.which("deepeval")
    if deepeval_bin is None:
        print("SKIP DeepEval: install eval dependencies with `uv sync --extra dev --extra eval`.")
        return 0

    model = os.getenv("DEEPEVAL_JUDGE_MODEL", DEFAULT_MODEL)
    if model.startswith("anthropic/") and not os.getenv("ANTHROPIC_API_KEY"):
        print(
            "SKIP DeepEval: ANTHROPIC_API_KEY is required for the configured judge model "
            f"({model})."
        )
        return 0

    env = os.environ.copy()
    env.setdefault("DEEPEVAL_JUDGE_MODEL", model)
    pythonpath = [str(ROOT / "src")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env.setdefault("GRAPH_BACKEND", "mock")
    env.setdefault("LLM_BACKEND", "fake")

    command = [deepeval_bin, "test", "run", "evals/deepeval"]
    return subprocess.run(command, cwd=ROOT, env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())
