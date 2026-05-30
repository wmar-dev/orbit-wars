# Candidate B: Garrison Sizing (agent_v12)

**Date**: 2026-05-30 | **Branch**: 005-agent-improvement-experiments

## Hypothesis

Right-sizing fleet sends (exact `target.ships + 1`) and enforcing a garrison floor before launching improves net ship economy: source planets retain enough ships to defend and produce, while attack fleets are just large enough to capture. Expected improvement: ≥55% win rate vs agent_v10.

Three garrison floor sub-experiments determine the optimal retention level:

- Mode A: `max(production × 5, 1)`
- Mode B: `max(production × 10, 1)`
- Mode C: fixed `10`

## Change

Built on agent_v10. Send logic replaced with `send = min(target.ships + 1, source.ships - garrison_floor)`; skip if `send <= 0`. Three sub-experiments (A/B/C) run separately; best win-rate variant is embedded as the permanent `GARRISON_FLOOR_MODE`.

## Self-play result

Sub-experiment results (20 games each vs agent_v10, seeds 0–19):

| Mode | Garrison Floor | agent_v12 wins | agent_v10 wins | Draws | Win rate |
|------|----------------|---------------|----------------|-------|----------|
| A    | production × 5 | 0             | 20             | 0     | **0%**   |
| B    | production × 10| 0             | 20             | 0     | **0%**   |
| C    | fixed 10       | 0             | 20             | 0     | **0%**   |

All three modes: agent_v10 wins every game.

## Conclusion

**FAIL** — 0% win rate across all sub-experiments, far below the 55% threshold.

The garrison floor mechanics starve the agent completely: requiring a floor before launching means most planets never reach surplus to fire, especially early-game when ships are low. The aggressive send strategy of agent_v10 (send `target.ships + 1` without a floor) proves superior because capturing more planets earlier outweighs the garrison economy benefit.

Root cause: The `min(target.ships + 1, available_surplus)` formula combined with a non-trivial floor means many planets cannot fire at all each turn, effectively halting the expansion. This mechanic will NOT be included in agent_v15.
