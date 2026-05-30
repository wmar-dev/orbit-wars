# Research: Mid-Game Reward Signals

**Feature**: 008-mid-game-rewards | **Date**: 2026-05-30

## Game State Observation Fields

- Decision: Use `obs['planets']` (list of Planet namedtuples) and `obs['fleets']` (list of Fleet namedtuples) as the sole inputs to reward computation.
- Rationale: These are the only observable fields that change meaningfully per turn and are already used by all existing agents. No new observation fields are needed.
- Alternatives considered: `obs['step']` (used for game-phase bucketing in analysis only), `obs['angular_velocity']` (not relevant to reward).

**Planet namedtuple**: `(id, owner, x, y, radius, ships, production)`
- `owner`: `-1` = neutral, `0..N-1` = player index
- `ships`: ships currently on the planet
- `production`: ships produced per turn when owned

**Fleet namedtuple**: `(id, owner, x, y, angle, from_planet_id, ships)`
- `owner`: player index who launched the fleet
- `ships`: ship count in transit

**Total owned ships for player P**: `sum(p.ships for p in planets if p.owner == P) + sum(f.ships for f in fleets if f.owner == P)`

## Reward Component Design

- Decision: Four components, each computed as a normalized delta between consecutive turns, summed with configurable weights.
- Rationale: Deltas capture what changed this turn (the agent's action effect), not absolute state (which varies by map seed). Normalized deltas are comparable across games.

### Component 1: Planet Capture Bonus

```
capture_bonus = sum(planet.production for planet in planets_now
                    if planet.owner == player
                    and planets_prev[planet.id].owner != player)
```
- Scaled by `1 / CAPTURE_SCALE` (configurable; default = 10.0, representing a high-production capture)
- Clamped to [-1, 1] after scaling

### Component 2: Production Delta

```
prod_now  = sum(p.production for p in planets_now  if p.owner == player)
prod_prev = sum(p.production for p in planets_prev if p.owner == player)
production_delta = prod_now - prod_prev
```
- Scaled by `1 / PROD_SCALE` (configurable; default = 5.0)

### Component 3: Ship Delta

```
ships_now  = sum(p.ships for p in planets_now  if p.owner == player)
           + sum(f.ships for f in fleets_now   if f.owner == player)
ships_prev = sum(p.ships for p in planets_prev if p.owner == player)
           + sum(f.ships for f in fleets_prev  if f.owner == player)
ship_delta = ships_now - ships_prev
```
- Scaled by `1 / SHIP_SCALE` (configurable; default = 20.0)

### Component 4: Terminal Reward

```
terminal = 1 - 2 * (rank - 1) / (N - 1)   # N = number of players
```
- `rank` = 1 for highest final reward, N for lowest
- In 2-player: win = +1.0, loss = -1.0
- In 4-player: 1st = +1.0, 2nd ≈ +0.33, 3rd ≈ -0.33, 4th = -1.0
- Emitted only on the final turn (when `obs['step']` reaches max or a player is eliminated)

### Combined Reward Formula

```
per_turn = w_capture * capture_bonus
         + w_production * production_delta
         + w_ship * ship_delta

total = per_turn  # non-terminal turns
      = terminal  # terminal turn (replaces per_turn, not additive)
```

Default weights (all per-turn signals sum to << 1.0 so terminal dominates):
- `W_CAPTURE = 0.5`
- `W_PRODUCTION = 0.3`
- `W_SHIP = 0.2`

## Reward-Guided Agent Design (FR-010–011)

- Decision: Blend reward-signal-based target score with the existing ROI score via a configurable `REWARD_ALPHA` parameter.
- Rationale: Additive blending is the simplest integration that preserves existing behavior at `REWARD_ALPHA = 0.0` (FR-011) and allows continuous tuning.

### Scoring Formula for agent_v31

The existing ROI score per (source, target) pair:
```
roi = production * max(1, 100 - travel_turns) / max(1, ships + production * travel + 1)
```

The reward-signal estimate for attacking target T from source S:
```
expected_capture_gain = T.production / CAPTURE_SCALE   # if we capture it
expected_ship_loss    = -dispatch_ships / SHIP_SCALE
reward_estimate = W_CAPTURE * expected_capture_gain + W_SHIP * expected_ship_loss
```

Blended score:
```
score = (1 - REWARD_ALPHA) * roi_normalized + REWARD_ALPHA * reward_estimate
```
Where `roi_normalized` is ROI rescaled to [0, 1] by dividing by the max ROI across all candidates.

Default starting point: `REWARD_ALPHA = 0.3` (30% reward influence, 70% ROI). Experiment with 0.1, 0.2, 0.3, 0.4, 0.5 against `agent_v30`.

## Replay Analysis Script Design (FR-012)

- Decision: `reward_analysis.py` reads a `.jsonl` reward log and prints a Markdown-formatted summary to stdout, grouped by game phase.
- Rationale: Simple stdout report is immediately readable and scriptable (pipe to file). No GUI or notebook required.

Game phases (turn buckets):
- Early: step 1–20
- Mid: step 21–60
- Late: step 61+

Output columns per phase: avg reward (total), avg capture bonus, avg production delta, avg ship delta; winner vs. loser comparison.
