# DeepEval Quality Evals

These evals add an optional LLM-as-a-judge layer on top of the deterministic mock evals.

They are intentionally not part of the default CI quality gate because they require a judge
model API key and can vary slightly between runs.

## Setup

```bash
uv sync --extra dev --extra eval
export DEEPEVAL_JUDGE_MODEL=anthropic/claude-3-5-sonnet-20241022
export ANTHROPIC_API_KEY=...
```

## Run

```bash
uv run python scripts/run_deepeval.py
```

The eval app still uses `GRAPH_BACKEND=mock` and `LLM_BACKEND=fake`; the Anthropic key is only
used as the DeepEval judge.
