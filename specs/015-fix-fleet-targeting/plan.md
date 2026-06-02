# Implementation Plan: Fix Comet Fleet Targeting

**Branch**: `015-fix-fleet-targeting` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-fix-fleet-targeting/spec.md`

## Summary

The `_comet_two_pass` function in `main.py` estimates comet intercept points using exactly two iterations. When the comet's predicted position after the first pass is significantly farther from the source planet than the comet's current position, `t0 ≠ t1` and the two passes diverge rather than converge. The fallback path (when `valid2=False`) aims the fleet at the first-pass position, which the comet has already moved past by the time the fleet arrives. The fleet misses the comet and exits the board.

**Fix**: Replace the 2-pass function with an iterative fixed-point loop (up to 10 iterations, convergence criterion `|t_new − t_old| < 0.5` turns). If the loop does not converge, or if any iteration puts the comet within the safety buffer of landing, return `valid=False`.

---

## Technical Context

**Language/Version**: Python 3.14 (local), Python 3.x (Kaggle sandbox)

**Primary Dependencies**: `kaggle_environments` (orbit_wars env), stdlib `math`

**Storage**: N/A

**Testing**: `make test` (smoke test vs random), `uv run python eval.py` (head-to-head eval)

**Target Platform**: Kaggle Orbit Wars sandbox (single-file Python agent)

**Project Type**: Competition agent (CLI/script)

**Performance Goals**: Agent decision must complete within 1 second/turn (`actTimeout`). The loop adds ≤8 extra calls to `math.hypot` per comet target per turn — negligible.

**Constraints**: Single self-contained `main.py` — no external imports beyond stdlib and `kaggle_environments`.

**Scale/Scope**: Single file change to two functions: `_comet_two_pass` and optionally a tightened `_comet_predicted_pos`.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | ✅ PASS | This is a heuristic bug fix. Heuristics are acceptable as baseline / rule-based logic; RL training continues on top. |
| II. Fair Play | ✅ PASS | Fixing a targeting calculation error, not exploiting engine behaviour. |
| III. Manual Submissions | ✅ PASS | No submission pipeline changes. Submission remains manual. |
| IV. Experiment Documentation | ✅ PASS | Experiment log entry required before any Kaggle submission. |
| V. Local Self-Play Evaluation | ✅ PASS | ≥20 self-play games required before promotion to submission candidate. |
| VI. Submission Package | ✅ PASS | Single-file `main.py` — Option A. All logic inlined. |
| VII. 95% Confidence Gate | ✅ PASS | ≥20 game eval provides statistical signal; no outstanding unknowns after Phase 0. |

**Post-Phase-1 re-check**: No architectural changes introduced. All principles remain satisfied.

---

## Phase 0: Research

*Resolved in `research.md`.*

Key questions investigated:
1. Does the iterative fixed-point method converge for all physically reachable comets?
2. What convergence criterion and iteration cap are appropriate?
3. Does the fleet speed assumption (`fleet_speed(t.ships + 1)`) match the actual dispatch size?

---

## Phase 1: Design

### Algorithm Change

**File**: `main.py`  
**Functions changed**: `_comet_two_pass` (replaced), `_comet_predicted_pos` (unchanged)

**Current** (2-pass, divergent):
```python
def _comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed):
    t0 = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
    x1, y1, valid1 = _comet_predicted_pos(comet_planet, comet_path_lookup, t0)
    if not valid1:
        return comet_planet.x, comet_planet.y, False
    t1 = math.hypot(x1 - mine_x, y1 - mine_y) / speed
    x2, y2, valid2 = _comet_predicted_pos(comet_planet, comet_path_lookup, t1)
    if valid2:
        return x2, y2, True
    return x1, y1, True   # ← BUG: returns wrong position when t1 >> t0
```

**Replacement** (iterative, convergent):
```python
_COMET_INTERCEPT_MAX_ITER = 10
_COMET_INTERCEPT_EPS = 0.5   # turns

def _comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed):
    t = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
    for _ in range(_COMET_INTERCEPT_MAX_ITER):
        x, y, valid = _comet_predicted_pos(comet_planet, comet_path_lookup, t)
        if not valid:
            return comet_planet.x, comet_planet.y, False
        t_new = math.hypot(x - mine_x, y - mine_y) / speed
        if abs(t_new - t) < _COMET_INTERCEPT_EPS:
            return x, y, True
        t = t_new
    return comet_planet.x, comet_planet.y, False   # non-convergent → unreachable
```

**Why this converges**: The iteration `t → distance(mine, path[path_index + t]) / speed` is a contraction mapping when fleet speed ≥ comet speed component toward the source. Since fleet speed (up to 6.0) exceeds comet speed (4.0), the sequence converges for all physically interceptable comets.

**Why non-convergent = unreachable**: If the loop does not converge within 10 iterations, the comet is moving away from the source faster than the fleet can close the gap. Returning `valid=False` is the correct response.

### Speed Consistency Verification

The speed passed into `_comet_two_pass` is `fleet_speed(t.ships + 1)` and the dispatched fleet is always `ships_needed = t.ships + 1` for neutral comets. These are consistent — no change needed.

### No New Entities or Contracts

This is an algorithm-only change inside a single function. No data model changes, no new public interfaces, no contracts file needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/015-fix-fleet-targeting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (from /speckit-tasks)
```

### Source Code (repository root)

```text
main.py                  # Only file changed
```

---

## Complexity Tracking

*No constitution violations. Table not required.*
