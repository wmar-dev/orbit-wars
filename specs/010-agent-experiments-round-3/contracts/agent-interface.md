# Agent Interface Contract

**Feature**: Round 6 experiments | **Date**: 2026-05-30

## Function Signature

```python
def agent(obs) -> list[list]:
```

**Input**: `obs` — game observation (dict or object with attribute access, per CONTEST.md)

**Output**: `list` of moves, where each move is `[from_planet_id, angle_radians, num_ships]`

## Observation Fields Used

| Field | Access pattern | Used by |
|-------|----------------|---------|
| `obs.player` | `obs.get("player", 0)` or `obs.player` | All candidates |
| `obs.planets` | `obs.get("planets", [])` or `obs.planets` | All candidates |
| `obs.initial_planets` | `obs.get("initial_planets", [])` | Orbit-lead (inherited) |
| `obs.angular_velocity` | `obs.get("angular_velocity", 0.0)` | Orbit-lead (inherited) |
| `obs.comets` | `obs.get("comets", [])` | Comet intercept (inherited) |
| **`obs.fleets`** | `obs.get("fleets", [])` or `obs.fleets` | **NEW: Candidates S and U** |

## Move Constraints (unchanged)

- `from_planet_id` must be an owned planet (owner == player)
- `num_ships` must be ≤ planet's current ship count
- `angle_radians` in `[−π, π]`
- Multiple moves from the same planet are allowed (one per call)
- Empty list `[]` is valid (no moves this turn)

## Safety Invariants (must not be broken)

All agents must preserve these guards from agent_v9/v10/v32:

1. **Sun avoidance**: Fleet path (full ray to board edge) must clear `SUN_EXCLUSION = 12` units from sun center (50, 50).
2. **OOB rejection**: Predicted target position must be within `[0, 100] × [0, 100]`.
3. **Planet obstruction**: Fleet path must not cross any intermediate planet's radius.
4. **Comet evacuation**: Ships on comets with `remaining_turns ≤ EVACUATE_THRESHOLD` must be evacuated before the comet exits.

## New Constants (Round 6)

| Constant | Value | Mechanic |
|----------|-------|---------|
| `ANGLE_EPSILON` | `0.1` radians | Candidates S, U (fleet angle matching) |
| `WINNING_RATIO` | `2.0` | Candidate V (garrison reduction gate) |
| `WIN_FLOOR_FACTOR` | `1` | Candidate V (reduced garrison in winning state) |
