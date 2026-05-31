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
| `agent_v10.py` | + Intermediate planet obstruction check + orbit-lead refinement | 85% vs v9 (20 games) |
| `agent_v11.py` | + Redundant fleet avoidance (Candidate A) | 10% vs v10 (20 games) — FAIL |
| `agent_v12.py` | + Garrison sizing with floor (Candidate B) | 0% vs v10 (20 games) — FAIL |
| `agent_v13.py` | + Threat-aware defense (Candidate C) | 10% vs v10 (20 games) — FAIL |
| `agent_v14.py` | + Single-sender coordination (Candidate D) | 70% vs v10 (20 games) |
| `agent_v15.py` | Combined: single-sender coordination (only passing mechanic from v11–v14) | 70% vs v10 (20 games), 0 sun/OOB losses |
| `agent_v16.py` | + Speed-corrected orbit lead (Candidate E) | 70% vs v15 (20 games) |
| `agent_v17.py` | + Transit-adjusted fleet sizing (Candidate F) | 15% vs v15 (20 games) — FAIL |
| `agent_v18.py` | + Adaptive range expansion (Candidate G) | 0% vs v15 (20 games) — FAIL |
| `agent_v19.py` | + Capture-ROI scoring (Candidate H) | 60% vs v15 (20 games) |
| **`agent_v20.py`** | **Combined: speed-corrected orbit lead + capture-ROI scoring** | **75% vs v15 (20 games), 0 sun/OOB losses** |
| `agent_v21.py` | + Reactive defense dispatch (Candidate I) | 5% score vs v20 (20 games) — FAIL |
| `agent_v22.py` | + Smooth adaptive range (Candidate J) | 50% score vs v20 (20 games, 20 draws) — FAIL |
| `agent_v23.py` | + Enemy-territory priority when winning (Candidate K) | 50% score vs v20 (20 games, 20 draws) — FAIL |
| `agent_v24.py` | + Two-source coordinated attack (Candidate L) | 40% score vs v20 (20 games) — FAIL |
| `agent_v26.py` | + Lower garrison floor factor 5→3 (Candidate O) | 55% score vs v20 (20 games) |
| `agent_v27.py` | + 3-iteration orbit lead (Candidate P) | 20% score vs v20 (20 games) — FAIL |
| `agent_v28.py` | + No range limit on targets (Candidate Q) | 70% score vs v20 (20 games) |
| `agent_v29.py` | + Production-squared ROI (Candidate R) | 45% score vs v20 (20 games) — FAIL |
| `agent_v30.py` | Combined: lower garrison floor + no range limit | 75% score vs v20 (20 games), 100% 4P win rate, 0 sun/OOB losses |
| `agent_v31.py` | + Reward-blend target scoring (Candidate S, REWARD_ALPHA=0.1) | 61% score vs v30 (50 games) |
| `agent_v32.py` | Bug fixes: converged orbit-lead + comet evacuation from documented fields | 64% score vs v31 (50 games) |
| `agent_v33.py` | + Production-squared ROI (Candidate R, passed on bug-fixed baseline) | 60% score vs v32 (50 games) |
| `agent_v34.py` | + Cross-turn fleet deduplication (Candidate S R6) | 4% score vs v33 (50 games) — FAIL |
| `agent_v35.py` | + Transit-adjusted fleet sizing (Candidate T R6) | 0% score vs v33 (50 games) — FAIL |
| `agent_v36.py` | + Threat-aware garrison floor (Candidate U R6) | 86% score vs v33 (50 games) |
| `agent_v37.py` | + Winning-state garrison reduction (Candidate V R6) | 50% score vs v33 (50 draws) — FAIL |
| `agent_v38.py` | Combined R6: threat-aware garrison floor (Candidate U only) | 86% score vs v33 (50 games), 0 sun/OOB losses |
| `agent_v40.py` | + Race-condition fleet scaling, production-weighted sender assignment, banking mode (B-C variant) | 46% win rate vs v38 (50 games); +11.6% avg final ships vs v38 (20 games) |
| `agent_v41.py` | Clean refactor with helper.py module split | 52% vs v38; Kaggle score 755.1 |
| **`agent_v42.py`** | **+ Dynamic garrison floor: ramps 1x->4x over steps 0-300 (replaces static 3x)** | **54% win rate vs v38 (50 games); 60% win rate vs v40 (50 games)** |

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

**`agent_v11.py`** (Candidate A — FAIL): Adds redundant fleet avoidance — skips targeting planets already covered by sufficient en-route friendly ships (`sum >= target.ships + 1`). No improvement: 10% win rate vs v10. The mechanic rarely triggers in practice and doesn't change decisive outcomes.

**`agent_v12.py`** (Candidate B — FAIL): Adds garrison sizing — each planet retains a floor before launching and sends only `min(target.ships + 1, surplus)`. Three floor sub-experiments (production×5, production×10, fixed 10) all score 0% vs v10. The floor starves early-game expansion; agent_v10's aggressive send-all strategy captures planets faster.

**`agent_v13.py`** (Candidate C — FAIL): Adds threat-aware defense — reinforces owned planets when incoming enemy ships exceed `garrison + production×5`. No improvement: 10% win rate vs v10. Threshold is rarely triggered and defense dispatches consume turns that are more valuable as offense.

**`agent_v14.py`** (Candidate D — PASS): Adds single-sender coordination — for each target, only the planet with the best `distance / available_surplus` efficiency score may launch; all others redirect to different targets. Achieves 70% win rate vs v10. Spreading attack vectors across the map decisively outperforms uncoordinated multi-sender pile-ons.

**`agent_v15.py`**: Stacks all mechanics that passed ≥55% vs agent_v10. Only Candidate D passed; agent_v15 is functionally equivalent to agent_v14. Achieves 70% win rate vs agent_v10 with 0 sun losses and 0 OOB losses across 20 diagnostic games.

**`agent_v20.py`**: Fixes the orbit-lead speed bug (fleet travel time was computed from source planet's full ship count, not the actual launched fleet size) and adds ROI-based target scoring. Achieves 75% win rate vs agent_v15 with 0 sun/OOB losses across 20 diagnostic games.

**`agent_v38.py`**: Adds threat-aware garrison floor (Candidate U). Parses `obs.fleets` to detect enemy fleets heading toward owned planets using angle-matching (0.1 rad threshold) and raises the garrison floor for threatened planets to `max(3×production, incoming_enemy_ships)`. Prevents the agent from draining a planet's garrison offensively right before an enemy fleet arrives and captures it — no defensive dispatch overhead added. Achieves 86% score vs agent_v33 with 0 sun/OOB losses across 50 diagnostic games.

**`agent_v41.py`** (current best): Clean refactor of agent_v40 using `helper.py` — a standalone pure-function module containing all game-mechanics calculations (fleet speed, orbit-lead, comet intercept, path safety, ROI scoring, threat detection, banking mode). `agent_v41.py` is 197 lines vs 477 in v40; dead code removed (variant flags, unused sets). All proven mechanics unchanged. Achieves 52% win rate vs agent_v38 and 52% win / 56% score vs agent_v40 across 50 games each.

See [specs/003-agent-gap-analysis/](specs/003-agent-gap-analysis/) for the full design documents and [experiments/](experiments/) for per-experiment results.

## Evaluating Agents

```bash
# Head-to-head: any two agent files
uv run python eval.py --agent0 agent_v9.py --agent1 agent_v8.py --games 20 --jobs 4

# With verbose move logging
uv run python eval.py --agent0 agent_v9.py --agent1 agent_v8.py --games 3 --verbose
```

## Submitting to Kaggle

Manual submission only (per project constitution). Document your experiment first.

Kaggle requires the entry point to be named `main.py` and accepts a `.tar.gz` for multi-file agents.

```bash
# 1. Run eval and record results in experiments/
uv run python eval.py --agent0 agent_vNN.py --agent1 agent_vMM.py --games 50 --jobs 4

# 2. Copy agent to main.py, build archive, and submit
cp agent_vNN.py main.py
tar -czf agent_vNN.tar.gz main.py helper.py
uvx kaggle competitions submit orbit-wars -f agent_vNN.tar.gz -m "description"

# Or use make (builds archive automatically):
make submit MESSAGE="description"

# 3. Check status
make status
make leaderboard
```

**Note**: `main.py` is the Kaggle entry point — always overwrite it with the agent being submitted. `baseline.py` preserves the original getting-started agent.

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
