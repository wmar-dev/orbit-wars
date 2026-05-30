# Data Model: Comet Evacuation Fix, Fleet Targeting Accuracy, and Agent Improvement Experiments

**Feature**: 009-fix-comet-fleet-targeting | **Date**: 2026-05-30

---

## Entities

### CometPathLookup

Internal data structure built once per turn from the `comets` observation field.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `pid` (key) | int | `planet_ids[i]` | Planet ID of the comet |
| `path` | list[tuple[float, float]] | `paths[i]` | Full trajectory; empty list if not yet spawned |
| `path_index` | int | `path_index` (shared across group) | Current position along path |
| `remaining_turns` | int | `max(0, len(path) - path_index)` | **Computed**, not read from observation |

**Validation rules**:
- If `path` is empty → `remaining_turns = 0`, comet treated as stationary for safety purposes
- `path_index` clamped to `[0, len(path) - 1]` before use in position lookups

**State transition**:
```
remaining_turns > EVACUATE_THRESHOLD  → normal combat/attack logic applies
remaining_turns ∈ [1, EVACUATE_THRESHOLD] → EVACUATE state: launch all ships this turn
remaining_turns == 0  → DEPARTING: skip (comet removed before fleet launch per CONTEST.md)
```

---

### OrbitLeadEstimate

Computed result of the `_converged_orbit_lead` function for an orbiting planet target.

| Field | Type | Description |
|-------|------|-------------|
| `x_pred` | float | Predicted x position of planet at fleet arrival |
| `y_pred` | float | Predicted y position of planet at fleet arrival |
| `converged` | bool | True if delta < eps before iteration cap; False if cap reached |
| `iterations` | int | Number of iterations taken (1–10) |

**Convergence criterion**: `hypot(x_new - x_old, y_new - y_old) < 0.1` units

**Cap**: 10 iterations. Last estimate used regardless of convergence status.

---

### CometInterceptEstimate

Result of `_comet_two_pass` for a comet target.

| Field | Type | Description |
|-------|------|-------------|
| `x_pred` | float | Predicted x after two-pass re-estimation |
| `y_pred` | float | Predicted y after two-pass re-estimation |
| `valid` | bool | False if comet will exit board before fleet arrives (skip this target) |

**Validity rule**: If `future_idx + 5 >= len(path)` after either pass → `valid = False` (comet exits before arrival; do not target)

---

### EvacuationCandidate

Represents a potential evacuation destination when a comet is in EVACUATE state.

| Field | Type | Description |
|-------|------|-------------|
| `planet` | Planet | Destination planet (owned or non-owned) |
| `x_pred` | float | Predicted position x (orbit-lead or two-pass for comets, static for non-orbiting) |
| `y_pred` | float | Predicted position y |
| `score` | float | Evacuation score (see formula below) |
| `path_safe` | bool | True if fleet path from comet to predicted position is safe |

**Scoring formula**:
- Owned planet: `score = planet.production / (dist(comet, planet) + ε)` — reinforce value
- Non-owned planet: `score = _roi(planet, x_pred, y_pred, comet)` — capture ROI

Only `path_safe == True` candidates are eligible. Best score wins.

---

### ExperimentRecord

Written to `experiments/009-candidate-X.jsonl` (reward log) and `experiments/009-candidate-X.md` (prose record per constitution).

**Reward log schema** (one JSON object per line, produced by `eval.py --reward-log`):

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | int | Seed / game number |
| `seed` | int | Game seed (same as game_id) |
| `step` | int | Turn number within game |
| `player` | int | 0 or 1 |
| `capture_bonus` | float | Normalized planet capture reward ∈ [-1, 1] |
| `production_delta` | float | Normalized production change ∈ [-1, 1] |
| `ship_delta` | float | Normalized ship count change ∈ [-1, 1] |
| `terminal` | float \| null | Terminal reward on last turn; null otherwise |
| `total` | float | Weighted sum of per-turn components ∈ [-1, 1] |

**Prose record schema** (per constitution, stored in `experiments/`):

| Section | Required content |
|---------|-----------------|
| Hypothesis | What improvement is expected and why |
| Change | What was modified vs. fixed baseline (agent_v32) |
| Self-play result | Win rate, draw count, mean reward delta over 50 games |
| Conclusion | Pass (≥55%) or fail; keep or discard; lessons learned |

---

## Constants

| Constant | Value | Location | Rationale |
|----------|-------|----------|-----------|
| `EVACUATE_THRESHOLD` | 3 | agent_v32.py | 3-turn buffer ensures fleet can reach any locally adjacent planet |
| `ORBIT_LEAD_EPS` | 0.1 | agent_v32.py | Sub-planet-radius convergence tolerance (planet min radius ≈ 1.0) |
| `ORBIT_LEAD_MAX_ITER` | 10 | agent_v32.py | Cap preventing oscillation in degenerate edge cases |
| `GARRISON_FLOOR_FACTOR` | 3 | agent_v32.py (unchanged) | From feature-004; 3× production multiplier |
| `SUN_EXCLUSION` | 12.0 | agent_v32.py (unchanged) | SUN_RADIUS (10) + SAFETY_MARGIN (2) |
