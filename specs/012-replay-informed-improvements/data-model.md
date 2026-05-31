# Data Model: Replay-Informed Agent Improvements

**Feature**: `012-replay-informed-improvements` | **Date**: 2026-05-31

This document describes the logical data model for the new agent_v40 concepts. agent_v40 is a stateless function — there is no persistent storage. All entities below are computed per-turn from the observation.

---

## Entities

### PlanetValueScore

Computed per non-owned planet per turn. Used to rank expansion targets.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `planet_id` | int | Planet ID from observation |
| `prod_norm` | float [0,1] | `production / MAX_PROD` where `MAX_PROD = 5` |
| `dist_norm` | float [0,1] | `distance_to_nearest_owned / MAX_DIST` where `MAX_DIST = 141.4` |
| `value` | float | `PROD_WEIGHT * prod_norm - DIST_WEIGHT * dist_norm` |
| `is_enemy` | bool | True if enemy-owned, False if neutral |
| `is_high_prod` | bool | True if `production >= HIGH_PROD_THRESHOLD (4)` |

**Validation rules**:

- `prod_norm` always in [0, 1]; production clamped to [1, 5]
- `dist_norm` always in [0, 1]; distance clamped to [0, MAX_DIST]
- `value` can be negative (very far, low-production planets)

**State transitions**: Recomputed fresh each turn. No caching.

---

### CoordinatedAttackGroup

Computed once per turn when banking mode is inactive.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `primary_target` | Planet | Highest-value non-owned planet |
| `senders` | list[Planet] | All owned planets with `surplus > 0` assigned to primary target |
| `ships_per_sender` | dict[int, int] | `{planet_id: ships_to_send}` for each sender |
| `secondary_target` | Planet or None | Second-highest-value target for remaining surplus planets |
| `secondary_senders` | list[Planet] | Owned planets not assigned to primary |

**Constraint**: A planet can only appear in `senders` OR `secondary_senders`, not both.

**Constraint**: `ships_per_sender[id] <= source.ships - garrison_floor` always.

---

### BankingPhaseState

Computed per turn. Stateless check — no fields persisted between turns.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `active` | bool | True if banking mode should suppress attacks this turn |
| `my_prod` | int | Sum of production across all owned planets |
| `enemy_prod` | int | Sum of production across all enemy planets |
| `prod_advantage` | float | `my_prod / max(enemy_prod, 1)` |
| `my_ships` | int | Total ships on owned planets (not including in-flight fleets) |
| `variant` | str | `"A"`, `"B"`, or `"C"` — selected at agent compile time |
| `threshold` | float | Computed banking threshold for this variant and turn |

**Activation rules by variant**:

| Variant | Active when |
| ------- | ----------- |
| A | `prod_advantage >= 1.3` AND `my_ships < 800` |
| B | `prod_advantage >= 1.3` AND `my_ships < my_prod * 25` |
| C | `prod_advantage >= 1.3` AND `step < 200` AND `my_ships < 600` |

---

### RaceContestEstimate

Computed per candidate neutral target before deciding fleet size.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `target_id` | int | Planet ID of the contested neutral planet |
| `enemy_incoming` | int | Total enemy ships in fleets heading toward this target (angle match within `RACE_EPSILON = 0.2` rad) |
| `ships_to_send` | int | `max(target.ships + 1, target.ships + enemy_incoming + 1)` |
| `ships_capped` | int | `min(ships_to_send, source.ships - garrison_floor)` — actual ships sent |
| `contested` | bool | True if `enemy_incoming > 0` |

---

### FallbackTargetSet

Computed when no neutral high-production planets (production ≥ 4) remain.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `variant` | str | `"A"` (direct attack) or `"C"` (hybrid) |
| `primary` | Planet | Variant A: highest-value enemy high-prod planet. Variant C: lowest `ships/production` enemy high-prod planet |
| `secondaries` | list[Planet] | Variant C only: remaining neutral planets sorted by value score desc |

---

## Constants (agent_v40 top-level)

| Constant | Value | Purpose |
| -------- | ----- | ------- |
| `PROD_WEIGHT` | `2.0` | Weight for production in value score |
| `DIST_WEIGHT` | `1.0` | Weight for distance in value score |
| `MAX_PROD` | `5` | Fixed max production (per CONTEST.md) |
| `MAX_DIST` | `141.4` | Fixed max distance (diagonal of 100×100 board) |
| `HIGH_PROD_THRESHOLD` | `4` | Minimum production to be considered "high-production" |
| `ENEMY_PENALTY` | `0.5` | Additional discount for enemy-owned planets |
| `MAX_SHIPS_ESTIMATE` | `500` | Soft cap for enemy garrison penalty normalisation |
| `BANK_PROD_THRESHOLD` | `1.3` | Minimum production advantage ratio to enter banking mode |
| `BANK_FIXED_THRESHOLD` | `800` | Variant A: fixed ship count banking ceiling |
| `BANK_TURNS_FACTOR` | `25` | Variant B: banking ceiling = `my_prod * BANK_TURNS_FACTOR` |
| `BANK_STEP_CAP` | `200` | Variant C: banking only active before this game step |
| `BANK_ADAPTIVE_THRESHOLD` | `600` | Variant C: fixed ship count banking ceiling |
| `RACE_EPSILON` | `0.2` | Radians threshold for detecting enemy fleets targeting same neutral |
| `BANKING_VARIANT` | `"B"` | Selected at compile time — `"A"`, `"B"`, or `"C"` |
| `FALLBACK_VARIANT` | `"C"` | Selected at compile time — `"A"` or `"C"` |

All constants inherited unchanged from agent_v38:

| Constant | Value |
| -------- | ----- |
| `GARRISON_FLOOR_FACTOR` | `3` |
| `ANGLE_EPSILON` | `0.1` |
| `EVACUATE_THRESHOLD` | `3` |
| `ORBIT_LEAD_EPS` | `0.1` |
| `ORBIT_LEAD_MAX_ITER` | `10` |
| `SUN_EXCLUSION` | `12.0` |
| `BOARD_SIZE` | `100.0` |
