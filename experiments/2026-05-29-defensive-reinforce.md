# Experiment: Defensive Reinforcement (US3)

**Date**: 2026-05-29
**Agent**: agent_v6.py
**Hypothesis**: Scanning enemy fleets each turn and dispatching reinforcements to threatened owned planets should reduce losses and improve win rate against agent_v3.

## Change Description

Added `_heading_toward(fleet, planet)` using dot-product alignment (> 0.95 threshold, ~18° cone).

Added defense pre-pass before the attack loop:
- For each enemy fleet heading toward an owned planet, estimate `arrival_turns` and `projected_garrison`.
- If `enemy_fleet.ships > projected_garrison`, find nearest owned source planet with `surplus = source.ships - source.production * SAFETY_MULTIPLIER` (SAFETY_MULTIPLIER = 10).
- Dispatch `min(surplus, enemy_fleet.ships - projected_garrison + 1)` ships toward the threatened planet.
- Planets used as reinforcement sources are excluded from the attack loop that turn.

**Bug fix**: Initial implementation used a custom `Fleet` inner class that incorrectly parsed raw fleet data (which is a list `[id, owner, x, y, angle, ships, from_planet_id]`, not a dict or object). Fixed to use `KFleet(*f)` from `kaggle_environments`.

## Self-Play Result

| Metric | Value |
|--------|-------|
| agent_v6 wins | 4 / 20 |
| agent_v3 wins | 13 / 20 |
| Draws | 3 |
| Win rate (agent_v6) | **20.0%** |
| Threshold | ≥55% (11+ wins) |
| Result | **FAIL** |

## SC-3 Regression (sun-avoidance)

Not run due to failed eval result. Sun-avoidance code unchanged from agent_v3 baseline.

## Root Cause Analysis

The defense pre-pass excludes reinforcement source planets from attack that same turn. When defense triggers frequently (enemy fleets are common in mid/late game), this systematically sacrifices attack opportunities for reinforcement dispatches that may not arrive in time to matter. The net effect is a less aggressive agent that loses the production race.

Additionally, the SAFETY_MULTIPLIER=10 threshold is conservative: a production-5 planet won't send reinforcements unless it has 50+ ships, limiting the mechanic to high-garrison planets.

## Conclusion

Defensive reinforcement FAILS at 20% win rate. The mechanic as implemented hurts more than it helps: blocking attack moves from reinforcement sources reduces total fleet dispatches per turn, and the garrison build-up required by SAFETY_MULTIPLIER delays when reinforcements can fire. This mechanic is NOT included in agent_v8.
