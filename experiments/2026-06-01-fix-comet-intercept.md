# Experiment: Fix Comet Fleet Intercept (Iterative Convergence)

**Date**: 2026-06-01  
**Agent**: main.py (to be promoted as agent_v56)  
**Branch**: 015-fix-fleet-targeting  
**Spec**: specs/015-fix-fleet-targeting/spec.md

---

## Hypothesis

The `_comet_two_pass` function uses exactly 2 iterations to estimate the comet intercept point. When the predicted position after the first pass is significantly farther from the source planet than the comet's current position, the two passes diverge (`t0 ≠ t1`). The fallback path (when `valid2=False`) returns the first-pass position as a valid target, but the comet has moved well past that point by the time the fleet arrives. The fleet misses and exits the board.

Replacing the 2-pass with an iterative fixed-point loop (up to 10 iterations, convergence criterion `|t_new - t_old| < 0.5` turns) will eliminate missed intercepts. When the loop does not converge the comet is declared unreachable (`valid=False`), preventing wasteful dispatches.

---

## Change

**File**: `main.py`

Added two constants after `ANGLE_EPSILON`:
```python
_COMET_INTERCEPT_MAX_ITER = 10
_COMET_INTERCEPT_EPS = 0.5
```

Replaced `_comet_two_pass` (lines ~152–161) with:
```python
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
    return comet_planet.x, comet_planet.y, False
```

Verified against replay 78469577:
- Step 54 (comet unreachable): `valid=False` ✓ (same as before)
- Step 159 (previously divergent): `valid=False` ✓ (old code returned wrong `valid=True` at stale position ~(46,76))

---

## Self-Play Result

**Eval**: `main.py` vs `agent_v50.py` (prior best), 50 games

| Agent | Wins | Win Rate |
|-------|------|----------|
| main.py (fixed) | 33 | **66%** |
| agent_v50 (prior best) | 17 | 34% |

Also ran vs agent_v47: 30 wins / 60% (50 games) — confirms improvement stacks on top of v47 baseline too.

---

## Conclusion

**Keep.** The fix produces a clear improvement: 66% win rate vs agent_v50 (prior best). The iterative approach correctly handles cases the 2-pass missed, and the non-convergence path prevents wasted fleets. No regressions observed in smoke test. Promoting to agent_v56.
