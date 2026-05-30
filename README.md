# Orbit Wars

An agent competition for the [Orbit Wars Kaggle environment](https://www.kaggle.com/competitions/orbit-wars) — a real-time strategy game where players conquer planets orbiting a sun.

## Quick Start

```bash
make install        # install kaggle-environments into .venv
make test           # run agent_v2.py vs random (smoke test)
make eval           # run agent_v2.py vs main.py (10 games, ~14s)
make selfplay       # run agent_v2.py vs itself (symmetric baseline)
```

## Agents

| File | Strategy | Win rate vs baseline |
| --- | --- | --- |
| `main.py` | Nearest-planet sniper (getting-started baseline) | — |
| `agent_v2.py` | Production-weighted targeting | 90% (seeds 0–9), 70% (seeds 0–29) |
| `agent_v3.py` | Production-weighted targeting + sun-path avoidance | 90% (seeds 0–9) |

## How It Works

**`main.py` (baseline)**: For each owned planet, finds the nearest non-owned planet and sends exactly enough ships to capture it. Waits if it can't afford the nearest target.

**`agent_v2.py`**: Scores all nearby non-owned planets by `production / distance` and targets the highest-value planet within `2× the nearest planet's distance`. Waits to afford the best nearby target rather than settling for a cheap low-value one.

**`agent_v3.py`**: Extends agent_v2 with sun-path avoidance — filters out any fleet dispatch whose straight-line path comes within 12 units of the sun center (radius 10 + safety margin 2). Falls back to any sun-safe target if none exist within range. Strategically equivalent to agent_v2 on seeds 0–9 (avoidance filter did not fire); strictly safer on seeds where paths cross the sun.

See [specs/001-beat-starter-agent/](specs/001-beat-starter-agent/) and [specs/002-sun-avoidance-experiment/](specs/002-sun-avoidance-experiment/) for the full design documents and [experiments/](experiments/) for results.

## Evaluating Agents

```bash
# Head-to-head: any two agent files
uv run python eval.py --agent0 agent_v2.py --agent1 main.py --games 10

# With verbose move logging
uv run python eval.py --agent0 agent_v2.py --agent1 main.py --games 3 --verbose
```

## Submitting to Kaggle

Manual submission only (per project constitution). Document your experiment first:

```bash
# 1. Run eval and record results in experiments/
make eval

# 2. Submit
make submit AGENT=agent_v2.py MESSAGE="production-weighted targeting v1"

# 3. Check status
make status
make leaderboard
```

## Game Rules

See [CONTEST.md](CONTEST.md) for full game rules and [agents.md](agents.md) for the getting-started guide.
