# Quickstart: Beat the Getting Started Agent

## Prerequisites

```bash
make install   # installs kaggle-environments>=1.28.0 into .venv
```

## Run the New Agent vs Baseline (10 games)

```bash
uv run python eval.py
```

Expected output:

```
Game 1 (seed=0): Player 0 wins  [P0: 342.0  P1: 198.0]
...
--- Results (10 games) ---
Agent 0 (agent_v2.py): 7 wins
Agent 1 (main.py):     3 wins
Win rate (agent 0):    70.0%
```

## Swap the Agent Under Test

```bash
uv run python eval.py --agent0 my_new_agent.py --agent1 main.py --games 20
```

## Quick Smoke Test (agent vs random)

```bash
make test AGENT=agent_v2.py
```

## Submit to Kaggle

Only after documenting the experiment (see `experiments/` directory):

```bash
make submit AGENT=agent_v2.py MESSAGE="production-weighted targeting v1"
```

## Key Files

| File | Purpose |
| --- | --- |
| `agent_v2.py` | New production-weighted agent |
| `eval.py` | Head-to-head evaluation harness |
| `main.py` | Getting-started baseline (do not modify) |
| `experiments/2026-05-29-production-weighted-baseline.md` | Required experiment log |
