# Contract: Agent Interface

**Date**: 2026-05-29

The Orbit Wars environment defines the agent contract. Both the new agent and the
getting-started baseline must conform to it.

## Agent Function Signature

```
agent(obs) -> list[list[int | float]]
```

### Input: `obs`

Either a `dict` or an object with attribute access. The agent must handle both forms.

| Field | Type | Description |
| --- | --- | --- |
| `player` | int | Caller's player ID (0–3) |
| `planets` | list | `[id, owner, x, y, radius, ships, production]` per planet |
| `fleets` | list | `[id, owner, x, y, angle, from_planet_id, ships]` per fleet |
| `angular_velocity` | float | Rotation speed for orbiting planets (radians/turn) |
| `initial_planets` | list | Planet positions at game start (for orbit prediction) |
| `comet_planet_ids` | list | Planet IDs that are comets |
| `remainingOverageTime` | float | Remaining time budget (seconds) |

### Output: action list

A list of moves, each `[from_planet_id, angle, num_ships]`:

| Field | Type | Constraints |
| --- | --- | --- |
| `from_planet_id` | int | Must be a planet owned by `obs.player` |
| `angle` | float | Radians; 0 = right, π/2 = down |
| `num_ships` | int | 1 ≤ num_ships ≤ planet.ships |

Return `[]` to take no action this turn.

### Invariants

- The function MUST NOT raise an exception for any valid observation.
- The function MUST return within 1 second (actTimeout budget).
- `num_ships` MUST NOT exceed the current garrison of `from_planet_id`.
- Multiple moves from the same planet are allowed if ships are available.

## Evaluation Harness CLI Contract

```
uv run python eval.py [--games N] [--agent0 PATH] [--agent1 PATH]
```

| Argument | Default | Description |
| --- | --- | --- |
| `--games` | 10 | Number of games to play |
| `--agent0` | `agent_v2.py` | Path to agent under test |
| `--agent1` | `main.py` | Path to baseline agent |

### Stdout format (per game)

```
Game 1 (seed=0): Player 0 wins  [P0: 342.0  P1: 198.0]
Game 2 (seed=1): Player 1 wins  [P0: 120.0  P1: 301.0]
...
```

### Stdout format (summary)

```
--- Results (10 games) ---
Agent 0 (agent_v2.py): 7 wins
Agent 1 (main.py):     3 wins
Draws:                 0
Win rate (agent 0):    70.0%
```
