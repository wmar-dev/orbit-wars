# Candidate Q: Remove Range Limit (agent_v28)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Agent_v20 limits targets to `nearest_dist * RANGE_FACTOR (2.0)` — only targets within 2× the nearest planet's distance are considered. This prevents attacking isolated high-value enemy planets. Removing the range limit entirely (attack any safe target in any direction, picking by highest ROI) allows the agent to always attack the globally best target, not just the locally nearest one. The ROI formula already discounts distance via `100 - travel_turns`, so it naturally prefers closer targets when equal — the range limit is redundant. Expected improvement: ≥55% score vs agent_v20.

## Change

Built on agent_v20. Remove the `dist <= max_range` condition from both the primary and fallback candidate loops. Keep the range-fallback loop (currently used when no in-range candidates exist) as the only loop — it already handles all targets without range limit. This simplifies the logic significantly.

Concretely: remove `max_range = nearest_dist * RANGE_FACTOR` and the `dist <= max_range` guard. All safe targets become candidates.

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v28 wins: 14
- agent_v20 wins: 6
- Draws: 0
- **Win rate: 70%**
- **Score: 70%**
- Pass threshold: ≥55% score

## Conclusion

**PASS** — 70% score exceeds the threshold by a large margin. Strong result.

Removing the range limit allows the agent to always attack the globally highest-ROI target, even if it's far away. The ROI formula's `(100 - travel_turns)` discount already penalizes distant targets, so this is not reckless — it just allows opportunistic attacks on isolated high-value planets the range limit was blocking. 0 draws in 20 games indicates decisive outcomes. This mechanic WILL be included in agent_v30.
