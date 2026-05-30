# Candidate D: Single-Sender Coordination (agent_v14)

**Date**: 2026-05-30 | **Branch**: 005-agent-improvement-experiments

## Hypothesis

Restricting each enemy/neutral target to a single sender (the most efficient planet by `distance / available_surplus`) frees all other owned planets to attack different targets. This spreads offensive reach and avoids wasteful pile-ons where multiple planets send ships to the same target. Expected improvement: ≥55% win rate vs agent_v10.

## Change

Built on agent_v10. For each candidate target, compute `efficiency[source] = distance(source, target) / max(source.ships - garrison_floor, 1)` across all owned sources with surplus > 0. Only the source with the minimum efficiency score may launch at that target this turn. Garrison floor defaults to `production × 5`.

## Self-play result

20 games vs agent_v10 (seeds 0–19):

- agent_v14 wins: 14
- agent_v10 wins: 6
- Draws: 0
- **Win rate: 70%**

## Conclusion

**PASS** — 70% win rate exceeds the 55% threshold by a large margin.

Single-sender coordination dramatically improves offensive effectiveness. By assigning each target to its most efficient sender (minimum `distance / available_surplus`), all other owned planets redirect to different targets. This spreads attack vectors across the map rather than piling ships on one target, and consistently outperforms agent_v10's uncoordinated multi-sender approach.

Notable: zero draws in 20 games — every game produced a decisive outcome. This mechanic WILL be included in agent_v15.
