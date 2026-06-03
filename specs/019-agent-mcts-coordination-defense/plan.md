# Implementation Plan: Agent Strategic Improvements — Beam Search, Fleet Coordination, Defense

**Branch**: `019-agent-mcts-coordination-defense` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/019-agent-mcts-coordination-defense/spec.md`

## Summary

Three improvements to break the ~850 scoring ceiling. Current agent_v58 runs in 0.29ms avg per turn (1-second budget = ~3000 greedy evals headroom). This makes shallow beam search feasible within budget. Implementation order: fleet coordination (simplest), defensive reinforcement (moderate), beam search (largest). A combined v59 incorporates all three.

## Technical Context

**Language/Version**: Python 3.x (uv-managed venv)

**Primary Dependencies**: `kaggle_environments`, stdlib only in agent files

**Storage**: Experiment records in `experiments/` as `.md`

**Testing**: `uv run python eval.py --agent0 <variant> --agent1 agent_v58.py --games 50 --jobs 4`

**Target Platform**: Kaggle Orbit Wars sandbox (1-second actTimeout per turn)

**Performance Goals**: Each variant must complete its turn in ≤800ms. Beam search: 30 candidates × 5 turns × ~0.03ms/turn ≈ 5ms — well within budget.

**Constraints**: No local imports beyond stdlib + `kaggle_environments`; self-contained agent files

**Scale/Scope**: 4 experiment variants + 1 combined, 50 games per variant

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| I. RL First | ✅ Pass | Heuristic improvements permitted as baseline |
| II. Fair Play | ✅ Pass | No rule exploits |
| III. Manual Submissions | ✅ Pass | Manual after evaluation |
| IV. Experiment Documentation | ✅ Pass | All variants documented in experiments/ |
| V. Local Self-Play ≥20 games | ✅ Pass | 50-game evals exceed minimum |
| VI. Submission Package | ✅ Pass | Agent files self-contained |
| VII. 95% Confidence Gate | ✅ Pass | Combined v59 needs ≥55% vs v58 before submission |

## Project Structure

### Documentation

```text
specs/019-agent-mcts-coordination-defense/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
└── tasks.md
```

### Source Code

```text
agent_v58.py               # Baseline (unchanged)
agent_v59_coord.py         # Experiment A: fleet coordination only
agent_v59_defense.py       # Experiment B: defensive reinforcement only
agent_v59_beam.py          # Experiment C: beam search only
agent_v59.py               # Experiment D: all three combined

experiments/
└── 2026-06-02-019-agent-strategic-improvements.md
```

## Implementation Detail

### Experiment A — Fleet Coordination (agent_v59_coord.py)

**Base**: agent_v58.py. **~20 lines changed.**

Build a `coverage` dict after parsing fleets. For each in-transit own fleet, record `coverage[target_planet_id] += fleet_ships`. In the dispatch loop (before `moves.append`), add:

```python
if coverage.get(best_target.id, 0) >= ships_needed:
    continue  # already covered by in-transit fleet
coverage[best_target.id] = coverage.get(best_target.id, 0) + ships_needed
```

**Location**: New coverage dict built at [agent_v58.py:260-280](../../agent_v58.py#L260); check added in dispatch loop at [agent_v58.py:406](../../agent_v58.py#L406).

---

### Experiment B — Defensive Reinforcement (agent_v59_defense.py)

**Base**: agent_v58.py. **~60 lines added.**

Add two helper functions:

```python
def _threat_eta(planet, raw_fleets, player):
    """Return (incoming_ships, eta_steps) for worst enemy fleet heading to planet."""

def _defense_pre_pass(my_planets, threat, raw_fleets, player,
                      GARRISON_FLOOR_FACTOR, moves, dispatched):
    """For each threatened high-production planet, dispatch reinforcement if viable."""
```

`_threat_eta` finds the enemy fleet with angle pointing toward the planet and estimates steps remaining from fleet position and speed.

`_defense_pre_pass` runs before `best_sender`: for each owned planet P with `threat[P.id] > 0` and `P.production >= 2`, compute ETA, check if P can hold alone, and if not, dispatch from nearest allied source that can arrive in time while maintaining garrison floor. Marks dispatched sources in `dispatched` set to prevent double-dispatch in the main loop.

**Location**: New functions after `_enemy_fleet_size`; pre-pass call at start of `agent()` after threat dict is built ([agent_v58.py:273](../../agent_v58.py#L273)).

---

### Experiment C — Beam Search (agent_v59_beam.py)

**Base**: agent_v58.py. **~110 lines added.**

Add inline simulation module:

```python
BEAM_DEPTH = 5
BEAM_CANDIDATES = 30
BEAM_TIMEOUT_MS = 800

class _SimState:
    def __init__(self, planets, fleets): ...
    def step(self): ...  # advance one turn
    def score(self, player): ...  # production advantage

def _build_sim_state(planets, raw_fleets, angular_velocity): ...
def _add_dispatches(state, dispatches): ...  # inject ActionSet into sim
def _gen_candidates(planets, targets, greedy_moves, initial_planets_map,
                    angular_velocity): ...  # generate 30 action sets
def _beam_search(obs, greedy_moves): ...  # top-level: sim + score all candidates
```

`_gen_candidates` produces:
- 1 greedy baseline
- For each of up to 8 owned planets: swap to 2nd-best target (up to 8 variants)
- For top-3 ROI neutrals: "swarm" — all planets attack same target (3 variants)
- Hold-all (0 dispatches)
- ~18–22 candidates total

`_beam_search` calls `_gen_candidates`, runs `BEAM_DEPTH` sim steps per candidate, scores each, returns dispatches of max-score candidate. If wall time > `BEAM_TIMEOUT_MS`, returns greedy_moves immediately.

In `agent()`, replace `return moves` with:
```python
beam_result = _beam_search(obs, moves)
return beam_result
```

**Location**: New functions before `agent()`; `_beam_search` called at end of `agent()`.

---

### Experiment D — Combined (agent_v59.py)

**Base**: agent_v59_beam.py. Adds coverage check (A) and defense pre-pass (B).

Defense pre-pass runs before beam search and removes defending mines from the candidate generation pool. Coverage check is applied when generating beam candidates (skip already-covered targets). The beam search already implicitly handles some defense (hold variant leaves ships home), but the explicit pre-pass handles the most urgent threats immediately.

---

### Evaluation Protocol

```bash
uv run python eval.py --agent0 agent_v59_coord.py   --agent1 agent_v58.py --games 50 --jobs 4
uv run python eval.py --agent0 agent_v59_defense.py --agent1 agent_v58.py --games 50 --jobs 4
uv run python eval.py --agent0 agent_v59_beam.py    --agent1 agent_v58.py --games 50 --jobs 4
uv run python eval.py --agent0 agent_v59.py         --agent1 agent_v58.py --games 50 --jobs 4
```

If combined ≥55% vs v58 → run 100 more games to confirm → submit.

## Phase 0 Research: Complete

See [research.md](research.md). Key findings: beam search preferred over full MCTS (0.29ms/turn baseline leaves room for 200+ rollouts); coverage dict fixes the real fleet redundancy case; threat ETA calculation reuses existing angle-detection logic.

## Phase 1 Design: Complete

See [data-model.md](data-model.md). Variant matrix: v59_coord, v59_defense, v59_beam, v59 (combined).

## Complexity Tracking

No constitution violations.
