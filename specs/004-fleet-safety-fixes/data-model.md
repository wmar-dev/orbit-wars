# Data Model: Fleet Safety Validation & Fixes

**Date**: 2026-05-30

No persistent storage. All entities are in-memory Python structures per turn.

## Agent structures

### Candidate

A (target, predicted_x, predicted_y) triple evaluated during move selection.

- `target`: Planet namedtuple (id, owner, x, y, radius, ships, production)
- `x_pred`: float — predicted x position at fleet arrival time
- `y_pred`: float — predicted y position at fleet arrival time

Rejected candidates are discarded. Accepted candidates proceed to fleet dispatch.

### FleetRecord (diagnostic harness only)

Logged at launch time, resolved when the fleet disappears from the observation.

| Field | Type | Description |
| --- | --- | --- |
| game_seed | int | Random seed for the match |
| turn_launched | int | Turn number when fleet was dispatched |
| fleet_id | int | Fleet ID from the environment |
| source_id | int | Source planet ID |
| target_id | int | Intended target planet ID |
| aimed_x | float | Predicted target x at launch |
| aimed_y | float | Predicted target y at launch |
| ships | int | Ships in the fleet |
| outcome | str | `captured`, `transit_loss`, `unknown` |
| turn_resolved | int | Turn the fleet disappeared from observation |

## Constants (agent_v10.py)

| Name | Value | Purpose |
| --- | --- | --- |
| `SUN_EXCLUSION` | 12.0 | Sun radius (10) + safety margin (2) |
| `PLANET_MARGIN` | 1.0 | Extra clearance around intermediate planets |
| `BOARD_SIZE` | 100.0 | Board boundary |
| `RANGE_FACTOR` | 2.0 | Max target range = nearest_dist × factor |
| `EPSILON` | 1e-6 | Division guard |
