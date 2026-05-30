# Implementation Plan: Fleet Safety Validation & Fixes

**Branch**: `004-fleet-safety-fixes` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-fleet-safety-fixes/spec.md`

## Summary

Diagnose and eliminate all forms of wasted fleet in agent_v9.py — ships lost to the sun, out-of-bounds travel, missed intercepts, or collisions with intermediate planets. The primary technical approach is: (1) build a turn-by-turn diagnostic harness to measure baseline waste; (2) extend path safety to check for intermediate planet obstruction, not just the sun; (3) refine orbit-lead travel time estimation with one iteration of correction; (4) verify the full fix set in agent_v10.py with 20-game head-to-head evaluation.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: kaggle_environments (orbit_wars env), standard library (math, csv, json, os)

**Storage**: `logs/` directory — one CSV file per diagnostic run

**Testing**: `eval.py` (existing head-to-head harness), manual diagnostic script

**Target Platform**: Local macOS (darwin), no Kaggle submission required for this feature

**Project Type**: CLI / standalone scripts — no web service, no library API

**Performance Goals**: Diagnostic harness completes 20 games in under 60 seconds (parallelizable via `--jobs`)

**Constraints**: Agent turn budget ≤1 second; no environment source modification; agent_v9.py is read-only baseline

**Scale/Scope**: 20-game baseline run, 20-game head-to-head run; single-file agent (agent_v10.py)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --- | --- | --- |
| I. RL First | PASS | Heuristic improvement; RL-first remains the long-term path. Heuristic baselines are explicitly permitted. |
| II. Fair Play & Rules Compliance | PASS | No engine exploits; fixes eliminate accidental rules violations (launching into sun, OOB). |
| III. Manual Submissions Only | PASS | No automated submission pipeline introduced. |
| IV. Experiment Documentation | PASS | Experiment file must be created before or immediately after the run. |
| V. Local Self-Play Evaluation | PASS | SC-005 requires ≥20 self-play games before any consideration of submission. |

**Result**: All gates pass. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-fleet-safety-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v9.py              # Immutable baseline (read-only)
agent_v10.py             # Fixed agent (to be created)
diagnose_v9.py           # Diagnostic harness (to be created)
logs/                    # Created at runtime
experiments/
│   └── 2026-05-30-fleet-safety-v10.md  # Experiment record (constitution IV)
eval.py                  # Existing head-to-head harness (unchanged)
```

**Structure Decision**: Single-project flat layout, matching existing repo conventions. No subdirectories added.

---

## Phase 0: Research

Resolves all technical unknowns before design. Output: research.md

### R1 — How the environment moves orbiting planets and fleets (turn order)

**Finding**: From CONTEST.md turn order:

1. Comet expiration
2. Comet spawning
3. **Fleet launch** (agent action processed here)
4. Production
5. **Fleet movement** (fleets travel; OOB/sun/planet collisions checked here)
6. **Planet rotation & comet movement** (orbiting planets advance angular position)
7. Combat

**Critical implication**: When the agent computes its move at step N, the source planet is at its current position (after step N-1's rotation). The fleet spawns at step N (Fleet Launch), then moves at step N (Fleet Movement). The source planet does **not** rotate until after the fleet moves (step 6). So the launch origin is the planet's current position — no source-position prediction needed.

The target planet does continue orbiting. The fleet must intercept the target at the position it will be at when the fleet arrives, N + `travel_turns` steps later. `agent_v9` already predicts this correctly using `_predict_planet_pos`. No bug in orbit-lead itself.

**Actual remaining issues identified** (from code review):

| Issue | Location | Description |
| --- | --- | --- |
| **Planet obstruction** | `_path_safe()` | Only checks sun. Intermediate non-sun planets can block/capture a fleet mid-flight. CONTEST.md: "path segment comes within planet radius." Agent v9 has no check for this. |
| **travel_turns approximation** | candidate loop | `dist` is computed to the current target position, not the predicted one — circular dependency. One refinement iteration converges and improves intercept accuracy. |
| **Comet path index clamping** | `_build_comet_path_lookup` | `int(path_index + travel_turns)` can exceed `len(path) - 1`. Should be clamped. |

**Decision**: The highest-value new fix for v10 is **intermediate planet obstruction check**. All other items are either already correct or minor.

### R2 — Planet obstruction: how to check

**Finding**: A fleet is captured by any planet whose radius it enters (not just the target). The check is continuous along the path segment. We extend `_path_safe(ox, oy, tx, ty)` to also receive the planet list and check each non-target planet for ray clearance.

The `_segment_dist_to_sun` helper already computes minimum distance from a segment to a point. The same math applies to any planet. For intermediate planet clearance we use `planet.radius + PLANET_MARGIN` where `PLANET_MARGIN = 1.0`.

**Which planets to skip**: The target planet (intentional collision). Check all other planets — both neutral and opponent — against the full ray from source to board edge.

### R3 — Diagnostic harness design

**Finding**: The environment does not expose per-fleet outcome events. We infer outcomes by:

1. Wrapping the agent to log each launch (source, target, aimed coords, ships, turn).
2. Tracking the fleet list across turns to detect when each agent fleet disappears.
3. At the turn a fleet disappears, checking whether the target planet changed ownership or garrison. If yes → arrived. If no → lost in transit (sun / OOB / intermediate planet).

Log format (CSV per run):

```text
game_seed, turn_launched, source_id, target_id, aimed_x, aimed_y, ships, outcome, turn_resolved
```

Where outcome is one of: `captured`, `missed`, `transit_loss`, `unknown`.

### R4 — Orbit-lead travel_turns refinement

**Finding**: `travel_turns = dist(source, current_target) / speed` uses the current target position, not the predicted one. One iteration of refinement converges:

```python
t0 = math.hypot(t.x - mine.x, t.y - mine.y) / speed
x1, y1 = _predict_planet_pos(t, initial_planets_map, angular_velocity, t0)
t1 = math.hypot(x1 - mine.x, y1 - mine.y) / speed
x_pred, y_pred = _predict_planet_pos(t, initial_planets_map, angular_velocity, t1)
```

**Decision**: Add one refinement step in candidate evaluation.

---

## Phase 1: Design & Contracts

### data-model.md scope

No persistent data model — entities are in-memory Python structures. document-model.md records the key structures for task clarity.

### Key design decisions for agent_v10.py

#### Change 1: Extend `_path_safe` to check intermediate planet obstruction

```python
def _path_safe(ox, oy, tx, ty, all_planets=None, target_id=None):
    # existing sun + OOB check (unchanged)
    # NEW: for each planet in all_planets (excluding target_id),
    #      check ray clearance >= planet.radius + PLANET_MARGIN
```

`PLANET_MARGIN = 1.0` — a conservative buffer to avoid grazing collisions.

#### Change 2: One-step travel_turns refinement for orbit-lead

See R4 above. Applied in the candidate loop before calling `_predict_planet_pos` for the final aimed position.

#### Change 3: Comet path index clamping

```python
future_idx = min(int(path_index + travel_turns), len(path) - 1)
```

#### Change 4: Diagnostic harness (diagnose_v9.py)

Wraps the agent to log launches, runs N games, tracks the fleet list across turns, infers outcomes, writes CSV to `logs/`. Accepts `--games`, `--agent`, `--jobs` CLI flags matching `eval.py` conventions.

### Interface contracts

This feature is a CLI tool / agent script — no external API exposed. No `contracts/` directory needed.

### Agent context update

Update `CLAUDE.md` to point to this plan.
