# Data Model: Agent Improvement Experiments — Round 6

**Branch**: `010-agent-experiments-round-3` | **Date**: 2026-05-30

## Existing Entities (unchanged from agent_v33)

### Planet
Parsed from `obs.planets` as `Planet(*raw)`. Fields: `id, owner, x, y, radius, ships, production`.

### Fleet (newly accessed in Round 6)
Parsed from `obs.fleets` as a tuple/list `[id, owner, x, y, angle, from_planet_id, ships]`.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique fleet identifier |
| `owner` | int | Player ID of fleet owner (0–3) |
| `x`, `y` | float | Current position |
| `angle` | float | Direction of travel (radians) |
| `from_planet_id` | int | Source planet at launch time |
| `ships` | int | Ship count (constant during travel) |

**Note**: No `to_planet_id` field. Destination is inferred via angle-matching (see research.md Decision 1).

---

## New Computed Structures (Round 6)

### `in_transit: dict[int, int]`
**Purpose**: Cross-turn fleet deduplication (Candidate S).

**Built by**: Scanning `obs.fleets` for friendly fleets and angle-matching each to a target planet.

**Key**: `target_planet_id`
**Value**: Sum of ships in all friendly fleets estimated to be heading toward that target.

**Usage**: `ships_needed = max(1, projected_garrison + 1 - in_transit.get(target.id, 0))`

**Validation rules**:
- Only includes fleets where `fleet.owner == player`
- Angle match threshold: `abs(fleet_angle - angle_to_target) < ANGLE_EPSILON = 0.1` (radians)
- If no match found, `in_transit.get(target.id, 0) == 0` (no deduction)

---

### `threat: dict[int, int]`
**Purpose**: Threat-aware garrison floor (Candidate U).

**Built by**: Scanning `obs.fleets` for enemy fleets and angle-matching each to an owned planet.

**Key**: `owned_planet_id`
**Value**: Sum of ships in all enemy fleets estimated to be heading toward that planet.

**Usage**: `floor = max(GARRISON_FLOOR_FACTOR * planet.production, threat.get(planet.id, 0))`

**Validation rules**:
- Only includes fleets where `fleet.owner != player`
- Angle match threshold: same `ANGLE_EPSILON = 0.1`
- If no threat detected, floor reverts to standard formula

---

### `projected_garrison: int`
**Purpose**: Transit-adjusted fleet sizing (Candidate T).

**Formula**: `target.ships + target.production * travel_turns`

**Where** `travel_turns = ceil(distance / fleet_speed(target.ships + 1))` (one fixed-point iteration; see research.md Decision 2).

**Usage**: `ships_needed = projected_garrison + 1`

**Validation rules**:
- Neutral planets (owner == -1): `target.production` is still positive; formula applies
- `travel_turns` minimum is 1 (floor prevents division issues)

---

### `effective_floor_factor: int`
**Purpose**: Winning-state garrison reduction (Candidate V).

**Values**: `1` (winning by ≥2:1) or `3` (otherwise, same as `GARRISON_FLOOR_FACTOR`).

**Computed**:
```
own_total = sum(p.ships for p in my_planets)
enemy_total = sum(p.ships for p in planets if p.owner not in (-1, player))
winning = own_total >= 2.0 * max(enemy_total, 1)
effective_floor_factor = 1 if winning else GARRISON_FLOOR_FACTOR
```

**Validation rules**:
- `enemy_total` excludes neutral planets (owner == -1)
- If `enemy_total == 0` (all enemies eliminated), `max(enemy_total, 1) = 1`, so `own_total >= 2` triggers winning mode — correct behavior (game is essentially won)

---

## Combined Agent Computation Order

When all four mechanics are combined in agent_v38:

```
1. Parse obs.fleets → build threat dict, build in_transit dict (one pass)
2. Compute own_total, enemy_total → compute effective_floor_factor
3. Compute garrison floor: max(effective_floor_factor * production, threat.get(id, 0))
4. Run single-sender coordination (unchanged from v33) using updated garrison floor
5. For each dispatch candidate:
   a. Compute travel_turns (fixed-point, one iter)
   b. projected_garrison = target.ships + target.production * travel_turns
   c. ships_needed = max(1, projected_garrison + 1 - in_transit.get(target.id, 0))
   d. Skip if mine.ships < ships_needed
```
