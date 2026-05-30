# Quickstart: Sun Avoidance Experiment

**Feature**: 002-sun-avoidance-experiment | **Date**: 2026-05-29

## What This Adds

A new agent (`agent_v3.py`) that extends the production-weighted targeting strategy from `agent_v2.py` with sun avoidance: it filters out any fleet dispatch whose straight-line path comes within `SUN_RADIUS + SAFETY_MARGIN` of the sun center before selecting targets.

## Run the Experiment

```bash
# 1. Smoke test (1 game, agent_v3 vs random)
uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 1

# 2. Head-to-head: agent_v3 vs baseline (10 games)
uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10

# 3. Head-to-head: agent_v3 vs agent_v2 (10 games)
uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 10

# 4. Verbose 3-game view to observe strategy difference
uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 3 --verbose
```

## Expected Output (step 2)

```
Game 1 (seed=0): Player 0 wins  [P0: 1.0  P1: 0.0]
...
--- Results (10 games) ---
Agent 0 (agent_v3.py): N wins
Agent 1 (main.py): M wins
Win rate (agent 0): XX.X%
```

## Document Results

After both evals, record findings in:

```
experiments/2026-05-29-sun-avoidance.md
```

Required fields: hypothesis, change made, win rate vs `main.py`, win rate vs `agent_v2.py`, conclusion (net positive / neutral / negative).

## Project Files Changed

| File                                               | Change          |
|----------------------------------------------------|-----------------|
| `agent_v3.py`                                      | New (this task) |
| `experiments/2026-05-29-sun-avoidance.md`          | New (after eval)|
| `specs/002-sun-avoidance-experiment/`              | New (this spec) |
