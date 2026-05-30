# Data Model: Mid-Game Reward Signals

**Feature**: 008-mid-game-rewards | **Date**: 2026-05-30

## Entities

### RewardConfig

Single source of truth for all tunable parameters. Defined as a module-level constants block in `reward_signal.py`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `W_CAPTURE` | float | 0.5 | Weight for planet-capture bonus component |
| `W_PRODUCTION` | float | 0.3 | Weight for production-delta component |
| `W_SHIP` | float | 0.2 | Weight for ship-delta component |
| `CAPTURE_SCALE` | float | 10.0 | Denominator that normalizes capture bonus to ~[-1, 1] |
| `PROD_SCALE` | float | 5.0 | Denominator that normalizes production delta to ~[-1, 1] |
| `SHIP_SCALE` | float | 20.0 | Denominator that normalizes ship delta to ~[-1, 1] |

### TurnReward

Computed per (game, turn, player). Emitted by the reward module for every turn of every player.

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | int | Sequential game index within an eval run (0-based) |
| `seed` | int | Random seed used for the game |
| `step` | int | Turn number (0-based, matches `obs['step']`) |
| `player` | int | Player index (0..N-1) |
| `capture_bonus` | float | Normalized capture component for this turn |
| `production_delta` | float | Normalized production-change component |
| `ship_delta` | float | Normalized ship-count-change component |
| `terminal` | float or null | Rank-based terminal signal (non-null only on final turn) |
| `total` | float | Combined scalar reward in [-1, 1] |

**Constraints**:
- `total` is always in [-1, 1]
- `terminal` is null on non-terminal turns; on the terminal turn `total == terminal` (per-turn components are not added)
- One TurnReward row per (game_id, seed, step, player); no duplicates

### RewardLog (on-disk format)

Each line of the `.jsonl` file is a JSON object matching the TurnReward schema above:

```json
{"game_id": 0, "seed": 0, "step": 1, "player": 0, "capture_bonus": 0.0, "production_delta": 0.0, "ship_delta": -0.05, "terminal": null, "total": -0.01}
{"game_id": 0, "seed": 0, "step": 1, "player": 1, "capture_bonus": 0.0, "production_delta": 0.0, "ship_delta": 0.05, "terminal": null, "total": 0.01}
```

**Ordering**: Records are written in turn order, with player 0 before player 1 (etc.) within the same turn.

### GameStatePair

Internal structure used by the reward module. Never persisted; lives only in memory during a single `compute_reward()` call.

| Field | Type | Description |
|-------|------|-------------|
| `planets_prev` | dict[int, Planet] | `{planet_id: Planet}` from the previous turn |
| `fleets_prev` | dict[int, Fleet] | `{fleet_id: Fleet}` from the previous turn |
| `planets_now` | dict[int, Planet] | Current turn planets |
| `fleets_now` | dict[int, Fleet] | Current turn fleets |
| `player` | int | Player index being evaluated |
| `step` | int | Current turn number |

**Validation**: If any required field is missing from the raw observation, the module raises `ValueError` with a descriptive message identifying the missing field and turn.

### ExperimentRecord (on-disk, experiments/)

One Markdown file per experiment run, following the constitution's required format.

| Field | Description |
|-------|-------------|
| `Hypothesis` | What improvement is expected and why |
| `Change` | Reward weights used, `REWARD_ALPHA` value, agent version |
| `Self-play result` | Win rate vs. `agent_v30` over ≥20 games (target: 50) |
| `Conclusion` | Pass/fail at 55% threshold; keep or discard; observations |

## State Transitions

```
Turn N-1 observation
        │
        ▼
compute_reward(prev_obs, curr_obs, player)
        │
        ├─► terminal turn? ──YES──► terminal = rank_reward(final_rewards, player)
        │                            total = terminal
        │
        └─► non-terminal ──────────► capture_bonus + production_delta + ship_delta
                                      total = weighted sum, clamped to [-1, 1]
```

First turn (step == 0): No previous observation exists. Reward is 0.0 for all components (no delta possible).
