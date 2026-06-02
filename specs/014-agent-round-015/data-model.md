# Data Model: Agent Round 015

**Phase**: 1 — Design
**Feature**: specs/014-agent-round-015
**Date**: 2026-06-01

---

## Entities

### Agent Function

The `agent(obs)` function is the contract boundary. Each candidate produces a standalone file with a self-contained `agent(obs)` function. No changes to the function signature.

**Inputs** (from `obs`):
| Field | Type | Used by candidates |
|---|---|---|
| `planets` | `[[id, owner, x, y, radius, ships, production], ...]` | All |
| `fleets` | `[[id, owner, x, y, angle, from_planet_id, ships], ...]` | C1, C4, C5, C6 |
| `player` | `int` | All |
| `angular_velocity` | `float` | All |
| `initial_planets` | `[[id, owner, x, y, radius, ships, production], ...]` | All |
| `comets` | `[{planet_ids, paths, path_index}, ...]` | All |
| `step` | `int` | C2 (endgame normalization) |

**Output**: `[[from_planet_id, angle_radians, num_ships], ...]`

---

### ROI Formula (modified by C1 and C2)

Current form:
```
roi(t, bx, by, mine) =
  (production²  ×  max(1.0, 100.0 - travel))
  ─────────────────────────────────────────────
  max(1.0, t.ships + t.production × travel + 1)

where travel = dist(mine, predicted_pos) / fleet_speed(t.ships + 1)
```

After C1 + C2 combined:
```
roi(t, bx, by, mine, actual_fleet_size=None, remaining_turns=100.0) =
  n = actual_fleet_size ?? (t.ships + 1)
  travel = dist(mine, predicted_pos) / fleet_speed(n)

  (production²  ×  max(1.0, remaining_turns - travel))
  ──────────────────────────────────────────────────────
  max(1.0, t.ships + t.production × travel + 1)
```

**Note**: The denominator is intentionally unchanged. Experiment 014 Candidate A proved the denominator's `t.production × travel` term is an empirically-tuned distance penalty, not a garrison model. The numerator's `remaining_turns - travel` is the corrected time-decay.

---

### Garrison Floor (modified by C3)

Current form:
```
floor = max(production × GARRISON_FLOOR_FACTOR, threat[planet.id])
```

After C3:
```
incoming = threat.get(planet.id, 0)
buffer   = production × 2  if incoming > 0  else 0
floor    = max(production × GARRISON_FLOOR_FACTOR, incoming + buffer)
```

**State**: `threat` dict built fresh each turn from `raw_fleets`.

---

### Sender Assignment (modified by C4)

Current form: for each target, pick source planet with lowest `dist / surplus`.

After C4 — additional pre-screen for enemy targets:
```
if target.owner != -1:
    naive_dist  = dist(src, target_current_pos)
    naive_speed = fleet_speed(target.ships + 1)
    rough_needed = int(target.ships + target.production × (naive_dist / naive_speed)) + 1
    if src.ships < rough_needed:
        skip this src
```

---

### Covered Targets Set (new in C5)

A set of target IDs for which a sufficient friendly fleet is already in transit. Built each turn from `raw_fleets`.

```
covered_targets: set[int]

for each own fleet f in raw_fleets:
    for each target t:
        predicted_pos = orbit_lead_or_current(t)
        expected_angle = atan2(pred_y - f.y, pred_x - f.x)
        if angle_diff(f.angle, expected_angle) < ANGLE_EPSILON:
            rough_needed = ships_needed(t)
            if f.ships >= rough_needed:
                covered_targets.add(t.id)
```

Targets in `covered_targets` are excluded from `best_sender` assignment.

---

### Campaign State (new in C6)

Module-level dict persisting across turns within an episode:

```
_campaign: dict[int, tuple[int, float]]
# planet_id → (target_id, roi_at_time_of_assignment)
```

**Clear conditions** (evaluated before dispatching from a planet):

| Condition | Action |
|---|---|
| `target.owner == player` (captured successfully) | Clear |
| `target not in planets` (target gone — comet expired, etc.) | Clear |
| `target.id in covered_targets` (friendly fleet covers it) | Clear |
| Best available ROI > `roi_at_assignment × 1.30` | Switch to new target |

**Stability**: If none of the clear conditions are met, reuse the stored target_id. Skip re-scoring.

---

## State Transitions

```
Per planet, per turn:

[No campaign]
    ↓  best_sender assigns target T with ROI R
[Campaign: (T, R)]
    ↓  every subsequent turn: check clear conditions
    │  none triggered → reuse T
    │  triggered → [No campaign] → re-score
    ↓  T captured by player
[No campaign]
```

---

## Candidate → File Mapping

| Candidate | File | Change scope |
|---|---|---|
| C1: ROI mismatch fix | `agent_v48.py` | `_roi()` signature + call sites |
| C2: Endgame normalization | `agent_v49.py` | `_roi()` + pass `remaining_turns` |
| C3: Garrison buffer | `agent_v50.py` | Floor computation (2 lines) |
| C4: Sender pre-screen | `agent_v51.py` | `best_sender` loop (5 lines) |
| C5: Friendly fleet sufficiency | `agent_v52.py` | New `covered_targets` set + sender filter |
| C6: Persistent campaign | `agent_v53.py` | Module global `_campaign` + campaign logic |
| Combined (passing only) | `agent_v5X.py` | All passing changes merged |
