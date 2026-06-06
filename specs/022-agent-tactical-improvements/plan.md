# Implementation Plan: Agent Tactical Improvements

**Branch**: `022-agent-tactical-improvements` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-agent-tactical-improvements/spec.md`

## Summary

Three targeted behavioral improvements to `agent_v60` (Kaggle score 916.9), each addressing a measured gap identified via replay analysis against top competitors. Implemented as a new `agent_v61.py` with independent toggle constants so each direction can be isolated in evaluation before combination. All changes are confined to the greedy dispatch logic and the forward-simulation score function; the beam search framework from v60 is preserved intact.

## Technical Context

**Language/Version**: Python 3 (Kaggle sandbox; locally via `uv` with `pyproject.toml`)

**Primary Dependencies**: `math`, `time`, `random`, `copy` (stdlib); `kaggle_environments.envs.orbit_wars.orbit_wars.Planet`

**Storage**: N/A — single-file agent, no disk I/O during play

**Testing**: `make eval` (h2h vs `main.py`, 10 games default), `AGENT=agent_v61.py make eval`, `make selfplay`, `make opponents`; 50-game evals for each direction independently before combination

**Target Platform**: Kaggle sandbox (Python 3, stdlib + `kaggle_environments` only); local: macOS + `.venv` managed by `uv`

**Project Type**: Single-file competition agent (Option A — all helpers inlined, no local imports)

**Performance Goals**: ≤0.8s per turn (0.2s margin from the 1-second Kaggle `actTimeout`); early-dispatch path adds O(1) per mine; weighted eval adds O(depth) per simulation

**Constraints**: All helpers inlined; stdlib + `kaggle_environments` only; no `numpy`, `scipy`, or third-party packages

**Scale/Scope**: Typical game: 20–30 planets, 0–50 in-transit fleets, 500-turn horizon; single agent file ~900–1000 lines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | **Accepted deviation** | Heuristic improvement continues the established lineage (v2–v60). RL path remains open. |
| II. Fair Play | **Pass** | No engine exploits; `actTimeout` respected via existing budget-driven beam with greedy fallback |
| III. Manual Submissions | **Pass** | Submission gated on ≥50-game independent eval per direction; submitted manually |
| IV. Experiment Documentation | **Pass** | Each direction documented in `experiments/` with hypothesis + self-play result before any Kaggle submit |
| V. Local Self-Play | **Pass** | ≥50 games per direction independently; combination requires ≥50 games before submission |
| VI. Submission Package | **Pass** | Single self-contained file; pre-submission import check required |
| VII. 95% Confidence | **Pass** | ≥50-game evals provide statistical confidence; directions tested independently to isolate signal |

## Project Structure

### Documentation (this feature)

```text
specs/022-agent-tactical-improvements/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
agent_v61.py                    # New agent: v60 base + three tactical improvements
experiments/
└── 2026-06-06-tactical-improvements.md   # Experiment log per direction
```

---

## Phase 0: Research

See [research.md](research.md).

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Agent Architecture

`agent_v61.py` inherits the v60 structure with targeted modifications to two functions:

```
agent_v61.py
├── CONSTANTS
│   ├── (all v60 constants preserved)
│   ├── EARLY_DISPATCH_ENABLED = True     # Direction 1
│   ├── EARLY_DISPATCH_WINDOW = 15        # turns 0-15 only
│   ├── DYNAMIC_GARRISON_ENABLED = True   # Direction 2
│   └── WEIGHTED_EVAL_ENABLED = True      # Direction 3
│
├── _SimState.score_weighted()            # NEW: replaces score() in beam eval when WEIGHTED_EVAL_ENABLED
│   └── Accumulates (own_prod - opp_prod) each step instead of sampling at horizon
│
├── _greedy_moves()                       # MODIFIED
│   ├── Early-dispatch path (EARLY_DISPATCH_ENABLED)
│   │   └── Inserted before main dispatch loop; runs only when step <= EARLY_DISPATCH_WINDOW
│   └── Dynamic garrison floor (DYNAMIC_GARRISON_ENABLED)
│       └── Sets buffer=0 when mine has no confirmed incoming threat
│
└── agent()                               # unchanged
```

**No changes to**: `_beam_search`, `_gen_beam_candidates`, `_mcts_search`, `_nply_search`, `_lookahead_search`, `_build_sim_state`, geometry helpers.

### Direction 1: Early-Dispatch Path (turns 0–15)

**Problem**: In turns 0–15, the main dispatch loop requires `mine.ships - floor > 0` AND `mine.ships >= ships_needed`. With `gff=1.0` at step 0 and a small starting garrison, mines that could send a thin fleet toward nearby neutrals stay idle.

**Fix**: Insert an early-dispatch fast path before the main loop, active only when `step <= EARLY_DISPATCH_WINDOW`:

```python
if EARLY_DISPATCH_ENABLED and step <= EARLY_DISPATCH_WINDOW:
    for mine in my_planets:
        if mine.id in departing_this_turn or mine.id in evacuate_this_turn:
            continue
        # Find nearest reachable neutral not already claimed
        best_neutral, best_dist = None, float('inf')
        for t in targets:
            if t.owner != -1:  # neutrals only
                continue
            if t.id in early_claimed:
                continue
            speed = fleet_speed(t.ships + 1)
            x_pred, y_pred = _converged_orbit_lead(t, mine, ...)
            travel = hypot(x_pred - mine.x, y_pred - mine.y) / speed
            ships_at_arrival = t.ships + int(t.production * travel)
            needed = ships_at_arrival + 1
            if mine.ships < needed:
                continue
            if not _path_safe(...):
                continue
            dist = hypot(x_pred - mine.x, y_pred - mine.y)
            if dist < best_dist:
                best_dist = dist; best_neutral = (t, x_pred, y_pred, needed)
        if best_neutral:
            t, bx, by, needed = best_neutral
            early_claimed.add(t.id)
            angle = atan2(by - mine.y, bx - mine.x)
            early_moves.append([mine.id, angle, needed])
    # Merge early_moves into moves, skip main loop for mines already dispatched
```

Key invariants:
- Only targets neutrals (`t.owner == -1`)
- Fleet sized for garrison at arrival, not current garrison
- Planet must pass `_path_safe`
- After `EARLY_DISPATCH_WINDOW`, normal dispatch logic takes over

### Direction 2: Dynamic Garrison Floor

**Problem**: The `gff` factor grows from 1.0 to 4.0 over 300 turns. At step 150, every mine needs `production × 2.5` ships before it dispatches. Combined with the threat buffer, mines are over-reserving.

**Current code** (in `_greedy_moves`):
```python
incoming = threat.get(mine.id, 0)
buffer = mine.production * 2 if incoming > 0 else 0
floor = max(mine.production * gff, incoming + buffer)
```

**Fix** (when `DYNAMIC_GARRISON_ENABLED`):
```python
incoming = threat.get(mine.id, 0)
if DYNAMIC_GARRISON_ENABLED:
    buffer = mine.production * 2 if incoming > 0 else 0
    # When no incoming threat, allow floor to be just gff-based, not threat-padded
    floor = max(mine.production * gff, incoming + buffer) if incoming > 0 \
            else mine.production * gff
else:
    buffer = mine.production * 2 if incoming > 0 else 0
    floor = max(mine.production * gff, incoming + buffer)
```

Note: the existing logic already sets `buffer=0` when `incoming==0`, so the `floor` computation reduces to `mine.production * gff` regardless. The real improvement here is a separate tuning of `gff` itself — the linear ramp from 1.0 to 4.0 may be too aggressive. Experiment: cap gff at 2.0 (instead of 4.0) or change the step scaling (`step / 500` instead of `step / 300`). This is the actual parameter to tune.

**Revised formula** (DYNAMIC_GARRISON_ENABLED):
```python
gff = 1.0 + 1.5 * min(step / 300.0, 1.0)  # cap at 2.5x instead of 4x
```

This directly reduces garrison reservation across the whole game, allowing more dispatches when no active threat is detected.

### Direction 3: Production-Weighted Eval

**Problem**: `_SimState.score()` samples production differential only at the depth horizon. A capture at turn 3 of a depth-10 run contributes production for turns 3–10 but is counted only at turn 10, same as a capture at turn 9. This flattens the reward gradient, making the beam unable to distinguish fast-capture candidates from slow-capture ones.

**Fix**: Instead of calling `state.score()` once at the horizon, accumulate `(own_prod - opp_prod)` after each `state.step()` call, then return the total.

```python
def _score_rollout(base_state, dispatches, player, depth):
    state = base_state.copy()
    _apply_dispatches(state, dispatches, player)
    total = 0.0
    for turn in range(depth):
        state.step(opponent_model=OPPONENT_MODEL, player=player)
        total += state.score(player, TRANSIT_WEIGHT)
    return total
```

The beam search loop calls `_score_rollout` instead of `state.score()`. No change to `_SimState` itself.

Threat discount: within `state.score()`, enemy in-transit fleets heading to our planets are already implicitly captured in the simulation (they arrive and damage production). No additional threat term is needed; the production loss from losing a planet mid-rollout is naturally captured.

### Evaluation Protocol

Each direction tested independently (50 games vs v60, `--swap` flag):

1. `EARLY_DISPATCH_ENABLED=True`, others `False` → target ≥52% (statistical signal)
2. `DYNAMIC_GARRISON_ENABLED=True`, others `False` → target ≥52%
3. `WEIGHTED_EVAL_ENABLED=True`, others `False` → target ≥52%
4. All three combined → target ≥60% before Kaggle submission

Experiment log: `experiments/2026-06-06-tactical-improvements.md`

---

## Complexity Tracking

> No Constitution Check violations — no entry required.
