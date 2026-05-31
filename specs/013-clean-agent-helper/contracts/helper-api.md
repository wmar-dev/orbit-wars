# Contract: helper.py Public API

**Module**: `helper.py` | **Date**: 2026-05-31

This document defines the public interface contract for `helper.py`. All functions listed here are exported via `__all__` and must remain stable for human agent authors.

## Usage

```python
from helper import (
    fleet_speed, angle_to, path_safe,
    predict_planet_pos, converged_orbit_lead,
    build_comet_path_lookup, comet_two_pass,
    roi, planet_value, banking_mode, predict_target,
    # ... see __all__ for complete list
)
```

## Functions

### Geometry Primitives

**`segment_dist_to_point(ax, ay, bx, by, px, py) -> float`**
Minimum distance from point (px, py) to line segment (ax,ay)→(bx,by).

**`segment_dist_to_sun(ax, ay, bx, by) -> float`**
Distance from sun center to line segment. Convenience wrapper around `segment_dist_to_point`.

**`ray_exits_board(ox, oy, angle) -> tuple[float, float]`**
Returns (ex, ey): the point where a ray from (ox, oy) at `angle` exits the 100×100 board.

**`angle_to(x1, y1, x2, y2) -> float`**
Returns `atan2(y2-y1, x2-x1)` — the angle from point 1 to point 2.

**`angle_diff(a, b) -> float`**
Shortest angular distance between two angles (in radians). Always in [0, π].

### Path Safety

**`path_safe(ox, oy, tx, ty, all_planets=None, target_id=None, source_id=None) -> bool`**
Returns True if a fleet path from (ox,oy) to (tx,ty) is safe:
- (tx,ty) is within the board
- The full ray from origin does not come within `SUN_EXCLUSION` of the sun
- No intermediate planet (excluding source and target) is within `planet.radius + PLANET_MARGIN`

### Fleet Mechanics

**`fleet_speed(n) -> float`**
Returns the speed of a fleet of `n` ships: `1.0 + 5.0 * (log(n) / log(1000))^1.5`. Returns 1.0 for n ≤ 0.

### Orbital Prediction

**`predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns) -> tuple[float, float]`**
Returns the predicted (x, y) position of `planet` after `travel_turns` turns, using orbital mechanics. Falls back to current position if the planet is too close to the board edge or not in `initial_planets_map`.

**`converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed) -> tuple[float, float]`**
Iteratively refines the orbit-lead intercept for target planet `t` launched from `mine` at `speed`. Converges within `ORBIT_LEAD_EPS` or stops after `ORBIT_LEAD_MAX_ITER` iterations.

### Comet Mechanics

**`build_comet_path_lookup(obs) -> dict[int, tuple[list, int, int]]`**
Parses `obs.comets` (supports both dict and namedtuple obs) and returns a dict mapping `planet_id → (path, path_index, remaining_turns)`.

**`comet_predicted_pos(comet_planet, comet_path_lookup, travel_turns) -> tuple[float, float, bool]`**
Returns (x, y, valid) — the predicted comet position at `travel_turns` turns from now. Returns `valid=False` if the comet path is expiring (fewer than 5 steps remaining after the future index).

**`comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed) -> tuple[float, float, bool]`**
Two-pass comet intercept: estimates travel time, reads predicted position, refines with a second travel-time estimate. Returns (x, y, valid).

### Scoring

**`roi(t, bx, by, mine) -> float`**
Production-squared ROI score: `t.production² × max(1, 100-travel) / max(1, t.ships + t.production×travel + 1)` where travel is distance / fleet_speed(t.ships+1).

**`reward_estimate(target, dispatch_ships) -> float`**
Blended reward estimate combining capture value and ship cost. Used for REWARD_ALPHA blending in the attack loop.

**`planet_value(planet, source_x, source_y) -> float`**
Production-weighted value score: normalised production (weight 2) minus normalised distance (weight 1), with an enemy garrison penalty if the planet is owned.

**`enemy_incoming(target_x, target_y, raw_fleets, player) -> int`**
Returns total enemy ships in fleets heading toward (target_x, target_y), using `RACE_EPSILON` angle matching.

### Strategy Helpers

**`banking_mode(my_planets, enemy_planets, step, variant) -> bool`**
Returns True if the agent should suppress offensive sends this turn. Uses Variant B: returns True when my total ships < my_production × BANK_TURNS_FACTOR and production advantage ≥ BANK_PROD_THRESHOLD.

**`predict_target(t, mine, initial_planets_map, angular_velocity, comet_planet_ids, comet_path_lookup, planets) -> tuple[float | None, float | None, bool]`**
Unified orbit-lead / comet dispatch: returns (x_pred, y_pred, safe) for target planet `t`. Returns (None, None, False) if the comet path is invalid.

## Constants

All tunable constants are importable from `helper`. See [data-model.md](../data-model.md) for the full table.

## Invariants

- All functions are pure (no side effects, no global mutable state)
- `helper.py` does not import `kaggle_environments`; it works with any duck-typed object with the expected fields
- `helper.py` does not import any other local module
