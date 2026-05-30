# Experiment: Production-Weighted Targeting Baseline

**Date**: 2026-05-29
**Branch**: `001-beat-starter-agent`
**Agent file**: `agent_v2.py`

## Hypothesis

Scoring candidate planets by a production/distance heuristic rather than selecting
the nearest planet will yield a meaningfully higher win rate against the
getting-started nearest-planet-sniper (`main.py`), because it favors economically
valuable targets over geographically close but low-value ones.

## Change

Replaced the nearest-planet selection criterion (`min distance`) with a
production-weighted range filter:

1. Compute the distance to the nearest non-owned planet (regardless of affordability).
2. Consider only targets within `RANGE_FACTOR * nearest_dist` (RANGE_FACTOR = 2.0).
3. Among those candidates, select the highest `production / distance` scorer.
4. Wait (accumulate ships) if the best-scored target is unaffordable, rather than
   settling for a cheaper but lower-value target.

This differs from the nearest-sniper in two ways:

- Target selection is value-weighted, not distance-minimized.
- Patience: waits for a good target rather than grabbing the cheapest available.

## Self-play result

Games played: 10 (seeds 0–9)

- Agent 0 (`agent_v2.py`) wins: **9**
- Agent 1 (`main.py`) wins: **1**
- Draws: 0
- **Win rate: 90.0%**

Extended validation (30 games, seeds 0–29):

- Agent 0 wins: 21
- Agent 1 wins: 9
- Win rate: **70.0%**

Timing: 10-game run completes in ~14 seconds (well under 60-second budget).

## Conclusion

Hypothesis confirmed. Production-weighted targeting with a patience mechanism
beats the nearest-planet-sniper at 90% over the canonical 10-seed test and 70%
over a 30-seed extended test.

Key finding from the investigation: the getting-started agent's "wait until I can
afford the nearest planet" patience is actually near-optimal. The winning insight
is not just scoring differently, but also applying the same patience to the
*best-scored* target within a proximity window, rather than grabbing any affordable
target immediately.

**Decision**: Keep this strategy as the rule-based baseline. Next experiment should
explore RL self-play using this agent as the initial opponent seed, per the
constitution's RL-first principle.
