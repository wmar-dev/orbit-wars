# Data Model: Agent Improvement Experiments — Round 2

**Branch**: `006-agent-experiments-round-2` | **Date**: 2026-05-30

Agents v16–v20 are stateless Python scripts. All data is derived from the game observation each turn; no state is persisted between turns. This document describes the game entities read from the observation and the new computed values introduced by each candidate.

---

## Core Entities (from game engine, read-only)

### Planet

| Field | Type | Description |
| ----- | ---- | ----------- |
| `x`, `y` | float | Board position (0–100) |
| `ships` | int | Current ship count |
| `production` | int | Ships produced per turn |
| `owner` | int | Player index, or neutral sentinel |
| `radius` | float | Physical radius (used for obstruction checks) |
| `id` | int | Unique planet identifier |

### Comet Group (subset of planets)

| Field | Type | Description |
| ----- | ---- | ----------- |
| `planet_ids` | list[int] | Planets in this comet group |
| `paths` | list[list[[x,y]]] | Per-planet future position sequence |
| `path_index` | int | Current step index in paths |
| `remaining_steps` | int | Steps until comet exits the board |

### In-flight Fleet (for round 005 Candidate A reference; NOT used in round 2)

Round 2 candidates do not read the fleets array. Documented for completeness.

| Field | Type | Description |
| ----- | ---- | ----------- |
| `ships` | int | Fleet size |
| `owner` | int | Owning player |
| `source_id` | int | Origin planet id |
| `destination_id` | int | Target planet id |

---

## Computed Values (new in round 2)

### speed_for_target (Candidate E — per target, per source)

| Name | Formula | Used in |
| ---- | ------- | ------- |
| `speed_for_target` | `fleet_speed(target.ships + 1)` | `_refined_orbit_lead` call; replaces `fleet_speed(mine.ships + 1)` from v15 |

**Change from agent_v15**: In v15, `speed = fleet_speed(mine.ships + 1)` was computed once per source planet. Candidate E moves this inside the per-target loop so each target uses the actual launched fleet's speed.

---

### travel_turns (Candidates F and H — per target)

| Name | Formula | Used in |
| ---- | ------- | ------- |
| `travel_turns` | `hypot(mine.x − x_pred, mine.y − y_pred) / speed_for_target` | Transit-adjusted fleet sizing (F); ROI scoring (H) |

Uses distance to **predicted position** (post-orbit-lead), not current target position.

---

### ships_needed (Candidate F — per target)

| Name | Formula | Used in |
| ---- | ------- | ------- |
| `ships_needed_raw` | `target.ships + int(target.production × travel_turns) + 1` | Fleet size to send |
| `skip_condition` | `mine.ships < ships_needed_raw` | If True, skip this target |

**Change from agent_v15**: v15 always sends `target.ships + 1`. Candidate F adds a production-growth buffer and skips if the source can't afford the adjusted amount.

---

### range_factor (Candidate G — per turn, global)

| Name | Formula | Used in |
| ---- | ------- | ------- |
| `own_ships` | `sum(p.ships for p in my_planets)` | Ratio computation |
| `enemy_ships` | `sum(p.ships for p in planets if p.owner == 1 − player)` | Ratio computation |
| `ratio` | `own_ships / max(enemy_ships, 1)` | Range factor selection |
| `range_factor` | `3.5 if ratio ≥ 1.5 else 1.5 if ratio ≤ 0.7 else 2.0` | `max_range = nearest_dist × range_factor` |

**Change from agent_v15**: v15 uses a constant `RANGE_FACTOR = 2.0`. Candidate G replaces it with a per-turn computed value.

---

### roi_score (Candidate H — per target)

| Name | Formula | Used in |
| ---- | ------- | ------- |
| `roi_score` | `production × max(1, 100 − travel_turns) / max(1, target.ships + production × travel_turns + 1)` | Best-target selection |

**Change from agent_v15**: v15 selects best target by `target.production / (distance + EPSILON)`. Candidate H replaces this with ROI score.

---

## Agent Behavioral Contracts

### agent_v16 (Candidate E — speed-corrected orbit lead)

Inherits agent_v15. Single change: the per-target candidates loop computes `speed_for_lead = fleet_speed(t.ships + 1)` and passes it to `_refined_orbit_lead` instead of the pre-computed `fleet_speed(mine.ships + 1)`.

### agent_v17 (Candidate F — transit-adjusted fleet sizing)

Inherits agent_v15. Single change: after selecting `best_target`, compute `ships_needed = int(best_target.ships + best_target.production × travel_turns + 1)` using predicted-position distance; skip if `mine.ships < ships_needed`.

### agent_v18 (Candidate G — adaptive range expansion)

Inherits agent_v15. Single change: `RANGE_FACTOR` constant is replaced by a per-turn `range_factor` computed from `own_ships / enemy_ships` ratio before the per-planet loop.

### agent_v19 (Candidate H — capture-ROI scoring)

Inherits agent_v15. Single change: the `max(candidates, key=lambda item: item[0].production / (distance + EPSILON))` selection is replaced with `max(candidates, key=lambda item: roi_score(item[0], mine, item[1], item[2]))`.

### agent_v20 (combined)

Inherits agent_v15. Stacks all mechanics from v16–v19 that individually pass ≥55% win rate vs agent_v15. Integration order per research.md D-006: global range_factor → per-target correct speed → ROI scoring → transit-adjusted ships_needed.
