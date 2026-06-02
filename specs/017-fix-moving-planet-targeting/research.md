# Research: Fix Fleet Targeting When Both Source and Target Are Moving

**Feature**: 017-fix-moving-planet-targeting
**Date**: 2026-06-02

---

## 1. Game Engine Step Order (Critical Finding)

**Source**: `orbit_wars.py` step function, lines 476–633.

Per-step processing order (verified from engine source):

| Phase | Action |
|-------|--------|
| 0 | **Fleet Launch** — fleets are created at `planet.center + direction * (planet.radius + 0.1)`. Planets are still at their *pre-movement* positions (from end of previous step). |
| 1 | Production — owned planets gain ships. |
| 2 | Compute planet end-of-tick positions using `initial_angle + angular_velocity * step`. |
| 3 | **Fleet Movement** — each fleet moves by `speed` units along its angle. Collision uses swept-pair check over both planet and fleet segments. |
| 4 | Apply planet movement — planets update to new positions. |
| 5 | Combat resolution. |

**Decision**: Fleet launch position is `planet.center + direction * (radius + 0.1)`, NOT the planet center. The orbit lead calculation uses `mine.x, mine.y` (planet center) as the origin.

**Rationale**: The +0.1 gap was added in the engine so the fleet doesn't immediately collide with its launch planet.

---

## 2. Orbit Lead Formula Correctness (Theoretical Analysis)

The orbit lead formula in `_converged_orbit_lead` computes:

```
travel = dist(target_predicted, mine.center) / speed
target_at_travel = initial_angle_target + angular_velocity * (T + travel)
```

where T is the current step. This is mathematically correct: the fleet launches at step T+1 and makes move k in step T+k. For `k = dist(mine.center, aim) / speed`, the fleet reaches aim_point in step T + k while the planet is at `theta_0 + angular_velocity * (T + k)`. These match.

**However**: The fleet actually launches from `mine.center + direction * (mine.radius + 0.1)`, not `mine.center`. The actual travel distance is `dist(mine.center, aim) - (mine.radius + 0.1)`. The fleet arrives `(mine.radius + 0.1) / speed` turns EARLIER than the orbit lead predicts.

In that extra time, the target has orbited:
```
position_error = angular_velocity * orbital_radius * (mine.radius + 0.1) / speed
```

For typical parameters (angular_velocity = 0.04, orbital_radius = 28, mine.radius = 2.39, speed = 2):
- Position error ≈ 0.04 × 28 × 2.49 / 2 ≈ **1.4 units**
- Target radius = 2.39 units

The error (1.4 units) is within the target's radius (2.39), so the fleet still hits most of the time. But for small targets (radius ≈ 1.0 from planet group 4, 5, 6, 7) or slow fleets, this causes misses.

---

## 3. Path Safety and Orbiting Intermediate Planets (Secondary Finding)

`_path_safe` checks whether the straight-line path from `mine.x, mine.y` to `(x_pred, y_pred)` avoids:
- The sun (static)
- All intermediate planets at their **current** positions

When both source and target are orbiting, intermediate planets are also orbiting. A planet that is currently in the path might have moved away by the time the fleet passes through that region. This causes **false-negative path blocks** — valid attacks suppressed because the safety check uses stale planet positions.

This is the more impactful bug for "missing planets" in the sense of "failing to dispatch toward valid targets." The fleet doesn't actually miss the target; the dispatch is incorrectly blocked.

---

## 4. Root Cause Summary

| Bug | Scenario | Effect |
|-----|----------|--------|
| **A: Launch offset** | Source or target orbiting, small planet radius or slow fleet | Fleet arrives early; misses small targets (radius < ~1.5) |
| **B: Stale path safety** | Both source AND target orbiting, intermediate orbiting planet currently in path | Dispatch blocked; planet never attacked from current orbital config |

Bug B specifically manifests "when both source and target are moving" because: only when the source is in an orbiting position (which changes over time) does the relative path to an orbiting target pass through intermediate orbiting planets in problematic configurations. With a static source (fixed position), the path geometry is stable and either always blocked or always clear.

---

## 5. Fix Strategy

### Fix A: Correct the effective launch origin in the orbit lead

Adjust `_converged_orbit_lead` to use the actual launch position rather than the planet center. Since the launch position depends on the aim angle (which depends on the orbit lead), use one additional correction iteration:

1. Compute initial orbit lead from `mine.center` → aim point A, angle1.
2. Compute `launch = mine.center + direction(angle1) * (mine.radius + 0.1)`.
3. Recompute orbit lead from `launch` → refined aim point A'.
4. Use A' for dispatch.

This is a small but correct adjustment and makes the orbit lead geometrically consistent with the game engine.

### Fix B: Predict intermediate planet positions in path safety

In `_path_safe`, for orbiting intermediate planets, use their predicted positions at the midpoint of the fleet's travel (halfway through its journey) instead of their current positions. This reduces false-negative blocks when intermediate planets are "currently in the way" but will have moved by the time the fleet arrives.

Alternatively: for orbiting intermediate planets, check whether the planet's swept path (over the flight duration) intersects the fleet's path rather than using its current position. This is more accurate but heavier to compute.

**Recommendation**: Implement Fix A first (simple, directly corrects measured miss error). Add Fix B if time permits. Verify each fix independently with a 50-game eval vs v56.

---

## 6. Alternatives Considered

| Alternative | Status | Reason Rejected |
|-------------|--------|-----------------|
| Ignore launch offset (1.4 unit error < radius) | Partially viable | Fails for small-radius planets (groups 4–7 with radius=1.0); user reports misses |
| Use initial planet positions for path check | Rejected | Initial positions are at step 0, not current; even more stale |
| Sweep all intermediate planets over full flight | Viable alternative for Fix B | More accurate but O(fleet_length × planets) — may exceed 1s time budget at step count > 200 |
