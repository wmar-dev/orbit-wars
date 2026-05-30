# Candidate A: Redundant Fleet Avoidance (agent_v11)

**Date**: 2026-05-30 | **Branch**: 005-agent-improvement-experiments

## Hypothesis

Skipping launches at targets where a friendly fleet is already en route with sufficient ships (`en_route_ships >= target.ships + 1`) reduces wasted launches, conserves source-planet ships, and allows redirecting firepower to unconquered targets. Expected improvement: ≥55% win rate vs agent_v10.

## Change

Built on agent_v10. Before each target evaluation, compute the sum of ships in all friendly fleets whose destination equals the candidate target. If `sum >= target.ships + 1`, skip that target entirely this turn. All other logic (orbit-lead, path safety, scoring) unchanged.

## Self-play result

20 games vs agent_v10 (seeds 0–19):

- agent_v11 wins: 2
- agent_v10 wins: 1
- Draws: 17
- **Win rate: 10%**

(Baseline: agent_v10 self-play over same seeds produces same pattern — ~50% effective, mostly draws)

## Conclusion

**FAIL** — 10% win rate is below the 55% threshold.

The redundant-fleet check appears to have no benefit and may slightly reduce offensive pressure by filtering targets that are only tenuously "covered". In typical game states, en-route ships rarely sum to target.ships + 1 before the game is decided anyway. This mechanic will NOT be included in agent_v15.
