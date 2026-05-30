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

| File | Strategy | Win rate vs agent_v3 |
| --- | --- | --- |
| `main.py` | Nearest-planet sniper (getting-started baseline) | — |
| `agent_v2.py` | Production-weighted targeting | — |
| `agent_v3.py` | Production-weighted targeting + sun-path avoidance | baseline |
| `agent_v4.py` | + Orbit-lead targeting | 85% (20 games) |
| `agent_v5.py` | + Comet path prediction | 55% (20 games) |
| `agent_v6.py` | + Defensive reinforcement | 20% (20 games) — FAIL |
| `agent_v7.py` | + Fleet-speed scoring + fast-fleet send | 50% (20 games) — FAIL |
| `agent_v8.py` | Combined: orbit-lead + comet | 90% (20 games) |
| `agent_v9.py` | + Fleet path safety fix (full-ray sun check + OOB guard) | 94% vs main.py (50 games), 70% vs v8 |
| **`agent_v10.py`** | **+ Intermediate planet obstruction check + orbit-lead refinement** | **85% vs v9 (20 games)** |

## How It Works

**`main.py` (baseline)**: For each owned planet, finds the nearest non-owned planet and sends exactly enough ships to capture it. Waits if it can't afford the nearest target.

**`agent_v2.py`**: Scores all nearby non-owned planets by `production / distance` and targets the highest-value planet within `2× the nearest planet's distance`. Waits to afford the best nearby target rather than settling for a cheap low-value one.

**`agent_v3.py`**: Extends agent_v2 with sun-path avoidance — filters out any fleet dispatch whose straight-line path comes within 12 units of the sun center (radius 10 + safety margin 2). Falls back to any sun-safe target if none exist within range.

**`agent_v4.py`**: Extends agent_v3 with orbit-lead targeting — predicts where orbiting planets will be when a fleet arrives using `initial_planets` and `angular_velocity`, rather than targeting their current position. Strong improvement: 85% win rate.

**`agent_v5.py`**: Extends agent_v3 with comet path prediction — uses precomputed `comets[].paths` to target predicted comet positions at fleet arrival time; skips expiring comets; evacuates ships off comets leaving next turn. Narrow improvement: 55% win rate.

**`agent_v6.py`**: Extends agent_v3 with defensive reinforcement — scans enemy fleets each turn and dispatches reinforcements to threatened owned planets. Hurts performance (20%) by consuming attack turns for defense.

**`agent_v7.py`**: Extends agent_v3 with fleet-speed-aware scoring and a 10-ship minimum fleet send. Does not improve win rate (50%) — over-drains garrisons on easy captures.

**`agent_v8.py`**: Combines orbit-lead (v4) and comet opportunism (v5) — the two mechanics that individually passed ≥55%. Achieves 90% win rate vs agent_v3, confirmed across two 20-game runs.

**`agent_v9.py`**: Fixes two fleet path safety bugs in v8: (1) sun-avoidance check now covers the full ray to the board edge instead of just source→predicted_target; (2) predicted positions outside the 100×100 board are rejected. Achieves 94% vs main.py and 70% head-to-head vs v8 (50 games each).

**`agent_v10.py`**: Adds intermediate planet obstruction check — `_path_safe` now rejects any launch whose source→target segment passes within `planet.radius + 1.0` of any non-source, non-target planet, preventing fleets from being captured mid-flight. Also refines orbit-lead travel time with one iteration of correction (predict at t0, recompute to predicted pos, use t1), and adds comet path index clamping. Achieves 85% head-to-head win rate vs agent_v9 (20 games).

See [specs/003-agent-gap-analysis/](specs/003-agent-gap-analysis/) for the full design documents and [experiments/](experiments/) for per-experiment results.

## Evaluating Agents

```bash
# Head-to-head: any two agent files
uv run python eval.py --agent0 agent_v9.py --agent1 agent_v8.py --games 20 --jobs 4

# With verbose move logging
uv run python eval.py --agent0 agent_v9.py --agent1 agent_v8.py --games 3 --verbose
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

## Visualization

The notebook renderer uses the Wong colorblind-safe palette:

| Player | Color | Hex |
| --- | --- | --- |
| Player 0 | Blue | `#0072B2` |
| Player 1 | Vermillion | `#D55E00` |
| Player 2 | Teal | `#009E73` |
| Player 3 | Yellow | `#F0E442` |
| Neutral | Grey | `#888888` |

## Game Rules

See [CONTEST.md](CONTEST.md) for full game rules and [agents.md](agents.md) for the getting-started guide.
