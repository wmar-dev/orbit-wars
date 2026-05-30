# Data Model: Sun Avoidance Experiment

**Phase**: 1 | **Feature**: 002-sun-avoidance-experiment | **Date**: 2026-05-29

## Entities (from game observation)

### Planet
Provided by the environment each turn via `obs.planets`. Parsed with `Planet(*p)`.

| Field        | Type  | Description                                        |
|--------------|-------|----------------------------------------------------|
| `id`         | int   | Unique planet identifier                           |
| `owner`      | int   | Player ID (0 or 1); -1 = neutral                  |
| `x`          | float | Current x position (0–100, orbiting around 50,50) |
| `y`          | float | Current y position (0–100, orbiting around 50,50) |
| `radius`     | float | Planet radius (affects collision detection)        |
| `ships`      | int   | Ships currently garrisoned on the planet           |
| `production` | int   | Ships produced per turn                            |

**Key constraint**: Planet positions change each turn as planets orbit the sun. The x/y values in the current observation reflect the planet's position *this turn* only.

### Sun (implicit — not in observation)

| Constant      | Value  | Description                                |
|---------------|--------|--------------------------------------------|
| `CENTER`      | 50.0   | Sun x and y coordinate (board center)      |
| `SUN_RADIUS`  | 10.0   | Exclusion zone radius; fleets destroyed if |
|               |        | path comes within this distance of CENTER  |
| `SAFETY_MARGIN` | 2.0  | Buffer added to SUN_RADIUS for preemptive  |
|               |        | path safety check at dispatch time         |

### Fleet (dispatched by agent)

| Field | Type  | Description                                               |
|-------|-------|-----------------------------------------------------------|
| `from_id` | int | Source planet ID                                     |
| `angle`   | float | Direction in radians (atan2 of target relative to source) |
| `ships`   | int | Number of ships dispatched                           |

**Constraint**: One angle per dispatch — no multi-segment paths. Sun avoidance is achieved by choosing only targets whose source→target line segment clears the sun.

## Derived Values (computed by agent_v3)

| Value                  | Formula                                              |
|------------------------|------------------------------------------------------|
| `dist_to_target`       | `hypot(t.x - mine.x, t.y - mine.y)`                 |
| `score`                | `t.production / (dist_to_target + ε)`               |
| `sun_path_clearance`   | `segment_min_dist_to_sun(mine.x, mine.y, t.x, t.y)` |
| `sun_safe`             | `sun_path_clearance >= SUN_RADIUS + SAFETY_MARGIN`   |
| `in_range`             | `dist_to_target <= nearest_dist * RANGE_FACTOR`      |
| `candidate`            | planet where `sun_safe AND in_range AND affordable`  |

## Agent Decision Flow

```
For each owned planet (mine):
  1. Compute nearest_dist = min distance to any non-owned planet
  2. Filter candidates: non-owned, within RANGE_FACTOR * nearest_dist, sun-safe
  3. If no sun-safe candidates in range: expand to all sun-safe non-owned targets
  4. If still no candidates: skip this planet (no move)
  5. Best = max(candidates, key=score)
  6. If mine.ships >= best.ships + 1: dispatch
  7. Else: wait (accumulate)
```

## Experiment Comparison Matrix

| Agent       | Targeting    | Sun Avoidance | Expected win vs main.py | Expected win vs v2 |
|-------------|--------------|---------------|--------------------------|---------------------|
| `main.py`   | Nearest      | None          | baseline                 | ~10%                |
| `agent_v2.py` | Prod/dist  | None          | ~90%                     | baseline            |
| `agent_v3.py` | Prod/dist  | Skip unsafe   | TBD (≥70% target)        | TBD (experiment)    |
