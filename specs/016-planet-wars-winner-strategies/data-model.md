# Data Model: Planet Wars Winner Strategies

**Date**: 2026-06-01

The agent is a pure function with no persistent data structures beyond two module-level dicts for Variant D (cooldown). The "data model" describes the new per-turn state transformations introduced by each variant.

---

## Variant A: Intra-turn Commitment Tracking

**New variable**: `committed: dict[int, int]` — created fresh at the start of each `agent()` call.

```
committed[planet_id] = ships dispatched from planet_id so far this turn
```

**Modified surplus calculation**:
```
available = mine.ships - garrison_floor - committed.get(mine.id, 0)
```

**Update rule**: After appending a move `[mine.id, angle, ships_needed]`, execute:
```
committed[mine.id] = committed.get(mine.id, 0) + ships_needed
```

**Scope**: Intra-turn only. Reset each `agent()` call.

---

## Variant B: Redistribution

**New named constants**:
```python
REDISTRIB_THRESHOLD = 10    # minimum surplus to trigger redistribution
REDISTRIB_WEIGHT = 1.0      # weight for production in target scoring
```

**Redistribution target score**:
```
score(f) = f.production / (min_enemy_dist_to_f + 1)
```
where `min_enemy_dist_to_f = min(dist(f, e) for e in enemy_planets)`.

**Eligibility**:
- Source: `surplus > REDISTRIB_THRESHOLD` AND planet not in `dispatched_this_turn`
- Target: any friendly planet `f` where `f.id != source.id` and path is safe

**State added per turn**:
- `dispatched_this_turn: set[int]` — planet IDs that sent an offensive fleet this turn. Redistribution sources are excluded from this set (they are the ones NOT in it).

---

## Variant C: Spatial Penalty

**New named constants**:
```python
SPATIAL_RADIUS = 30.0         # units — neighborhood radius
SPATIAL_PENALTY_WEIGHT = 0.01 # penalty per enemy ship in neighborhood
```

**Pre-computed per turn** (once, before scoring any candidate):
```
enemy_neighborhood[t.id] = sum(e.ships for e in enemy_planets if dist(t, e) < SPATIAL_RADIUS)
```

**Modified ROI formula**:
```
adjusted_roi = _roi(t, bx, by, mine) - SPATIAL_PENALTY_WEIGHT * enemy_neighborhood[t.id]
```

Candidates where `adjusted_roi <= 0` are skipped.

---

## Variant D: Departure Cooldown

**Module-level variable** (persists across turns):
```python
_last_dispatch: dict[int, int] = {}   # planet_id -> last turn dispatched
```

**New named constant**:
```python
COOLDOWN_TURNS = 1   # turns between dispatches from same planet (test 1 and 2)
```

**Guard** (before offensive dispatch):
```
if step - _last_dispatch.get(mine.id, -999) < COOLDOWN_TURNS:
    continue   # skip this planet this turn
```

**Update rule**: After appending an offensive move:
```
_last_dispatch[mine.id] = step
```

**Exemptions**: Cooldown does NOT apply to:
- Comet evacuation (`mine.id in evacuate_this_turn`)
- Any move driven by `departing_this_turn`

---

## Combination Variants: State Composition

Combination variants merge the above without conflict:

| Variant | committed dict | dispatched_this_turn set | enemy_neighborhood dict | _last_dispatch dict |
|---------|---------------|-------------------------|------------------------|---------------------|
| A only | ✅ | — | — | — |
| B only | — | ✅ | — | — |
| C only | — | — | ✅ | — |
| D only | — | — | — | ✅ |
| A+B | ✅ | ✅ | — | — |
| A+C | ✅ | — | ✅ | — |
| B+C | — | ✅ | ✅ | — |
| A+B+C | ✅ | ✅ | ✅ | — |
| A+B+C+D | ✅ | ✅ | ✅ | ✅ |

No two variants share or modify the same state variable, so composition is additive and safe.

---

## Agent Function Contract (unchanged)

```python
def agent(obs) -> list[list[int, float, int]]:
    """
    obs: Observation object or dict with keys:
        player, planets, fleets, initial_planets, angular_velocity, step, comets
    
    Returns: list of moves, each move = [planet_id, angle_radians, ship_count]
    """
```

This contract is identical across all variants. Variants add internal logic but do not change inputs or outputs.
