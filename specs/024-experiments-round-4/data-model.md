# Data Model: Experiments Round 4

**Date**: 2026-06-06 | **Plan**: [plan.md](plan.md)

## Core Entities

### Game Observation (`obs`)

Represents the full observable game state each turn.

| Field | Type | Description |
|-------|------|-------------|
| `player` | int | Our player ID (0-3) |
| `planets` | list[[Planet](#planet)] | All planets on the board |
| `fleets` | list[[Fleet](#fleet)] | All in-transit fleets |
| `initial_planets` | list[[Planet](#planet)] | Starting positions (for orbit lead) |
| `angular_velocity` | float | Rotation speed of inner planets (rads/turn) |
| `step` | int | Current turn number |

### Planet

Represents a celestial body that produces ships and can be owned.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique planet ID |
| `owner` | int | Player who owns it (-1 = neutral) |
| `x` | float | X coordinate (0-100) |
| `y` | float | Y coordinate (0-100) |
| `radius` | float | Ship production rate (ships/turn) |
| `ships` | int | Current garrison |
| `production` | float | Ships produced per turn (≈ radius) |

### Fleet

Represents ships in transit between planets.

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Unique fleet ID |
| `owner` | int | Player who launched it |
| `x` | float | Current X position |
| `y` | float | Current Y position |
| `angle` | float | Direction of travel (radians) |
| `from_planet_id` | int | Source planet ID |
| `ships` | int | Number of ships |

### Move (Action)

A single dispatch command returned by the agent.

| Field | Type | Description |
|-------|------|-------------|
| `from_planet_id` | int | Source planet to dispatch from |
| `angle` | float | Direction to send fleet (radians) |
| `num_ships` | int | Number of ships to send |

### SimState (internal, forward simulation)

Lightweight copy of game state used by beam search for lookahead.

| Field | Type | Description |
|-------|------|-------------|
| `planets` | list[_SimPlanet] | Simulated planets (owner, ships, production, x, y) |
| `fleets` | list[_SimFleet] | Simulated fleets (owner, target_id, ships, eta) |
| `_idx` | dict[int, int] | Planet ID → index lookup |

### SimPlanet / SimFleet (internal)

Minimal planet/fleet representations for simulation with pre-computed ETA for fleets.

---

## Experiment-Specific Entities

### Opponent Model v3

Replacement for `_sim_opponent_step_v2` in forward simulation.

| Property | Description |
|----------|-------------|
| Target selection | ROI-based (similar to `_greedy_moves`) rather than nearest-target |
| Garrison check | Applies garrison floor factor (like our own dispatch) |
| Fleet speed | Scales with fleet size (uses `fleet_speed()`) |
| Path check | Respects sun safety (unlike v2) |

### Multi-Turn Plan Candidate

Beam search candidate where one or more source planets send 0 ships on the current turn.

| Property | Description |
|----------|-------------|
| `dispatches` | List of `(src_id, target_id, ships, eta)` — may be empty for skipped planets |
| `moves` | List of `[src_id, angle, ships]` — empty for skipped planets |
| Score | Evaluated via beam search rollouts; skip candidates compete with dispatch candidates |

### Phase Detection State

Game-phase analysis computed each turn from observation.

| Property | Description | When Active |
|----------|-------------|-------------|
| `expansion` | <40% of non-neutral planets owned | Normal GARRISON_FLOOR_FACTOR ramp |
| `mid_game` | 40-80% of non-neutral planets owned | Reduced garrison floor |
| `elimination` | >80% owned or ≤1 opponent alive | Lowest garrison floor, no splinter |
