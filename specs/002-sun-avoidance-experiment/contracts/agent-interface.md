# Agent Interface Contract

**Feature**: 002-sun-avoidance-experiment | **Date**: 2026-05-29

## Overview

All Orbit Wars agents must conform to the `kaggle_environments` agent contract. This applies to `agent_v3.py`.

## Function Signature

```
agent(obs) -> list[list]
```

## Input: Observation

The `obs` argument may be a dict or a namespace object. Always access with `.get()` / attribute fallback:

```python
player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
```

**Fields guaranteed to be present**:

| Field       | Type             | Description                             |
|-------------|------------------|-----------------------------------------|
| `player`    | int              | This agent's player ID (0 or 1)         |
| `planets`   | list[list]       | Planet data; parse with `Planet(*p)`    |
| `step`      | int              | Current game step (0-indexed)           |

**Fields present but not required for this agent**:
`fleets`, `comets`, `comet_planet_ids`, `initial_planets`, `next_fleet_id`, `angular_velocity`, `remainingOverageTime`

## Output: Move List

Return a list of moves. Each move is a 3-element list:

```
[from_planet_id: int, angle: float, ships: int]
```

| Field            | Constraint                                          |
|------------------|-----------------------------------------------------|
| `from_planet_id` | Must be the ID of a planet owned by this agent      |
| `angle`          | Radians; typically `atan2(dy, dx)` toward target    |
| `ships`          | Must be ≤ current ships on source planet            |

**Valid return values**:
- `[]` — no moves this turn (valid; agent waits)
- `[[id, angle, ships], ...]` — one move per owned planet (at most)

**Invariants**:
- Never dispatch more ships than available on source planet
- Never return `None` or raise an exception
- Must return within 1 second (actTimeout)

## Sun Avoidance Extension

`agent_v3.py` adds one filtering step before target selection:

```
sun_safe(source, target) = segment_min_dist_to_sun(source, target) >= SUN_RADIUS + SAFETY_MARGIN
```

Where `SUN_RADIUS = 10.0`, `CENTER = (50.0, 50.0)`, `SAFETY_MARGIN = 2.0`.

Only sun-safe targets are eligible for dispatch. If no safe targets exist for a given source planet, that planet skips its turn.

## File Placement

`agent_v3.py` must be placed at the project root (same directory as `main.py` and `agent_v2.py`) for compatibility with `eval.py --agent0 agent_v3.py`.
