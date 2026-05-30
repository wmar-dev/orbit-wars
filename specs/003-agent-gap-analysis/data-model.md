# Data Model: Agent Gap Analysis

**Feature**: 003-agent-gap-analysis | **Date**: 2026-05-29

All data comes directly from the Kaggle Orbit Wars observation dict. No new persistent
entities are introduced. This document describes the derived/computed values each agent
adds on top of the raw observation.

## Observation Entities (existing)

### Planet
`[id, owner, x, y, radius, ships, production]`

- `id`: int — unique planet identifier
- `owner`: int — player ID (0–3) or -1 for neutral
- `x`, `y`: float — current position (may be orbiting)
- `radius`: float — `1 + ln(production)`
- `ships`: int — current garrison
- `production`: int — 1–5 ships/turn when owned

### Fleet
`[id, owner, x, y, angle, from_planet_id, ships]`

- `id`: int
- `owner`: int — player ID
- `x`, `y`: float — current position
- `angle`: float — heading in radians
- `from_planet_id`: int
- `ships`: int — fixed during travel

### CometGroup (from `obs.comets`)
```
{
  planet_ids: [int, int, int, int],   # one per quadrant
  paths: [[[x,y], ...], ...],         # one path list per planet_id
  path_index: int                     # current step along the path
}
```

## Derived Values (computed each turn)

### OrbitalClassification
Computed from `initial_planets` once per game (values are constant):

| Field | Type | Description |
|-------|------|-------------|
| `is_orbiting` | bool | `hypot(ip.x-50, ip.y-50) + planet.radius < 50` |
| `orbital_radius` | float | `hypot(ip.x-50, ip.y-50)` |

### PredictedPosition
Computed per target planet per source planet (turn-local):

| Field | Type | Description |
|-------|------|-------------|
| `travel_turns` | float | `distance / fleet_speed(available_ships)` |
| `theta_arrival` | float | `atan2(y-50, x-50) + angular_velocity * travel_turns` |
| `x_pred`, `y_pred` | float | Predicted (x, y) at arrival time |

For comets: `(x_pred, y_pred) = paths[path_index + travel_turns]` (integer index, truncated).

### ThreatAssessment
Computed per enemy fleet per owned planet (turn-local):

| Field | Type | Description |
|-------|------|-------------|
| `heading_toward` | bool | dot-product alignment > 0.95 |
| `arrival_turns` | float | `distance(fleet, planet) / fleet_speed(fleet.ships)` |
| `projected_garrison` | float | `planet.ships + planet.production * arrival_turns` |
| `is_threatened` | bool | `fleet.ships > projected_garrison` |
| `reinforce_needed` | int | `fleet.ships - projected_garrison + 1` |

### SourceSurplus
Computed per owned planet for reinforcement dispatch:

| Field | Type | Description |
|-------|------|-------------|
| `safety_threshold` | int | `planet.production * 10` |
| `surplus` | int | `max(0, planet.ships - safety_threshold)` |

## State Transitions

No new state is maintained between turns. All derived values are recomputed each call
to `agent(obs)`. The observation is the sole source of truth.

## Experiment File Naming

Each agent file at project root:

| File | Mechanic |
|------|----------|
| `agent_v4.py` | Orbit-lead targeting |
| `agent_v5.py` | Comet opportunism |
| `agent_v6.py` | Defensive reinforcement |
| `agent_v7.py` | Fleet-speed scoring + fast-fleet send |
| `agent_v8.py` | Combined (stacks passing mechanics) |
