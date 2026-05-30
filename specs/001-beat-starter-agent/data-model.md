# Data Model: Beat the Getting Started Agent

**Date**: 2026-05-29

This feature adds no persistent data. All data is read-only from the game observation
each turn and discarded after the turn's action list is returned.

## Runtime Entities (read from observation)

### Planet

Sourced from `obs.planets` as `[id, owner, x, y, radius, ships, production]`.
Accessed via the existing `Planet` named tuple from `kaggle_environments`.

| Field | Type | Notes |
| --- | --- | --- |
| id | int | Unique planet identifier |
| owner | int | Player ID (0–3) or -1 for neutral |
| x | float | Current x position (0–100) |
| y | float | Current y position (0–100) |
| radius | float | Visual radius; derived from production |
| ships | int | Current garrison ship count |
| production | int | Ships generated per turn (1–5) |

### Fleet

Sourced from `obs.fleets`. Not used by the production-weighted agent in v1 (no threat
response), but available for future iterations.

### Derived: TargetScore

Computed per (owned_planet, target_planet) pair each turn. Not stored — evaluated inline.

| Field | Type | Formula |
| --- | --- | --- |
| score | float | `target.production / distance(owned, target)` |
| distance | float | `math.hypot(target.x - mine.x, target.y - mine.y)` |
| ships_needed | int | `target.ships + 1` |

## Evaluation Harness Entities

### GameResult

Produced by `eval.py` for each completed game. Printed to stdout; not persisted.

| Field | Type | Notes |
| --- | --- | --- |
| game_num | int | 1-based index |
| seed | int | Random seed used |
| winner | int | Player index (0 or 1), or -1 for draw |
| score_p0 | float | Final reward for player 0 |
| score_p1 | float | Final reward for player 1 |

### EvalSummary

Aggregated after all games complete. Printed to stdout.

| Field | Type | Notes |
| --- | --- | --- |
| total_games | int | N games run |
| wins_p0 | int | Games won by agent under test (player 0) |
| wins_p1 | int | Games won by baseline (player 1) |
| draws | int | Games ending in a draw |
| win_rate | float | `wins_p0 / total_games` |
