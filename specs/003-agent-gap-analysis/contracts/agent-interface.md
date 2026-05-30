# Contract: Agent Interface

**Feature**: 003-agent-gap-analysis | **Date**: 2026-05-29

All experiment agents (v4–v8) conform to the same Kaggle Orbit Wars agent interface.

## Function Signature

```python
def agent(obs) -> list:
    ...
```

## Input: `obs`

Either a dict or an object with attribute access. All agents must handle both forms:

```python
player     = obs.get("player", 0) if isinstance(obs, dict) else obs.player
raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
```

### Required observation fields used by new mechanics

| Field | Type | Used by |
|-------|------|---------|
| `initial_planets` | list of planet lists | v4 (orbit-lead) |
| `angular_velocity` | float | v4 (orbit-lead) |
| `comets` | list of comet group dicts | v5 (comet targets) |
| `comet_planet_ids` | list of int | v5 (comet targets) |
| `fleets` | list of fleet lists | v6 (defense) |

## Output

```python
[[from_planet_id, direction_angle, num_ships], ...]
```

- `from_planet_id`: int — must be a planet owned by this player
- `direction_angle`: float — radians; 0 = right, π/2 = down
- `num_ships`: int — 1 ≤ num_ships ≤ planet.ships

Return `[]` (empty list) to pass the turn.

## Constraints

- Decision time: < 1 second per call (enforced by engine `actTimeout`)
- No side effects: agent must not modify observation data or global state
- Self-contained: each agent file imports only stdlib and `kaggle_environments`
- No launches from planets not owned by the player

## Backward Compatibility

Each v4–v7 agent is a standalone file. If a new observation field (e.g., `initial_planets`)
is absent (e.g., older engine version), the agent must degrade gracefully:

```python
initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
```

If the field is empty, treat all planets as static (no orbit-lead prediction).
