# Data Model: Clean Agent with Helper Module

**Feature**: 013-clean-agent-helper | **Date**: 2026-05-31

## Entities

### Planet (from kaggle_environments — read-only)

Fields: `id` (int), `owner` (int; -1=neutral, 0–3=player), `x` (float), `y` (float), `radius` (float), `ships` (int), `production` (int)

Used by: observation parsing in `agent_v41.py`; all helper functions accept duck-typed planet objects.

### Fleet (from obs.fleets — read-only)

Raw format: `[id, owner, x, y, angle, from_planet_id, ships]` (list/tuple) or namedtuple equivalent.

Used by: `enemy_incoming`, threat dict construction in agent.

### CometGroup (from obs.comets — read-only)

Fields: `planet_ids` (list[int]), `paths` (list[list[[x,y]]]), `path_index` (int)

Used by: `build_comet_path_lookup` to construct the comet path lookup dict.

### CometPathLookup (computed, ephemeral per turn)

Type: `dict[int, tuple[list, int, int]]` — maps planet_id → `(path, path_index, remaining_turns)`

Created by: `build_comet_path_lookup(obs)`
Used by: `comet_predicted_pos`, `comet_two_pass`, comet evacuation logic in agent.

### ThreatDict (computed, ephemeral per turn)

Type: `dict[int, int]` — maps owned planet_id → total incoming enemy ships

Created by: inline loop in `agent_v41.agent()` using `angle_diff` and `ANGLE_EPSILON`
Used by: garrison floor calculation (`max(production * GARRISON_FLOOR_FACTOR, threat.get(p.id, 0))`)

### BestSenderMap (computed, ephemeral per turn)

Type: `dict[int, int]` — maps target planet_id → sender planet_id

Created by: inline loop in `agent_v41.agent()` (dist/surplus scoring)
Used by: attack loop to assign each planet only one target

## State Transitions

No persistent state across turns. All derived data structures (CometPathLookup, ThreatDict, BestSenderMap) are recomputed each call to `agent(obs)`.

## Constants (all in `helper.py`)

| Constant | Value | Source |
|---|---|---|
| `GARRISON_FLOOR_FACTOR` | 3 | Candidate O (v26) |
| `EVACUATE_THRESHOLD` | 3 | v8/v32 |
| `ORBIT_LEAD_EPS` | 0.1 | v32 Fix 2 |
| `ORBIT_LEAD_MAX_ITER` | 10 | v32 Fix 2 |
| `REWARD_ALPHA` | 0.1 | Candidate S (v31) |
| `ANGLE_EPSILON` | 0.1 | Candidate U (v38) |
| `RACE_EPSILON` | 0.2 | v40 |
| `SUN_RADIUS` | 10.0 | game constant |
| `SAFETY_MARGIN` | 2.0 | v9 |
| `SUN_EXCLUSION` | 12.0 | SUN_RADIUS + SAFETY_MARGIN |
| `PLANET_MARGIN` | 1.0 | v10 |
| `BOARD_SIZE` | 100.0 | game constant |
| `_SUN_X`, `_SUN_Y` | 50.0 | game constant |
| `W_CAPTURE` | 0.5 | reward signal |
| `W_SHIP` | 0.2 | reward signal |
| `CAPTURE_SCALE` | 10.0 | reward signal |
| `SHIP_SCALE` | 20.0 | reward signal |
| `PROD_WEIGHT` | 2.0 | v40 planet value |
| `DIST_WEIGHT` | 1.0 | v40 planet value |
| `MAX_PROD` | 5 | CONTEST.md |
| `MAX_DIST` | 141.4 | diagonal of 100×100 board |
| `HIGH_PROD_THRESHOLD` | 4 | v40 |
| `ENEMY_PENALTY` | 0.5 | v40 |
| `MAX_SHIPS_ESTIMATE` | 500.0 | v40 |
| `BANK_PROD_THRESHOLD` | 1.3 | v40 Variant B |
| `BANK_TURNS_FACTOR` | 25 | v40 Variant B |
| `EPSILON` | 1e-6 | division guard |
