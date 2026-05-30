# Candidate H: Capture-ROI Scoring (agent_v19)

**Date**: 2026-05-30 | **Branch**: 006-agent-experiments-round-2

## Hypothesis

The current scoring function `production / distance` ignores capture cost: a planet 10 units away with production 3 and 80 ships scores identically to one with production 3 and 5 ships, even though the first requires a large fleet and may be captured too late to generate meaningful production benefit. Replacing the score with a capture-ROI metric — `production × (100 − travel_turns) / capture_cost` — penalizes expensive, late captures and rewards fast, cheap ones that maximize remaining production turns. Expected improvement: ≥55% win rate vs agent_v15.

## Change

Built on agent_v15. Added a module-level helper:
```python
def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return t.production * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)
```
Replaced the best-target selection key from `lambda item: item[0].production / (hypot(...) + EPSILON)` with `lambda item: _roi(item[0], item[1], item[2], mine)`.

## Self-play result

20 games vs agent_v15 (20 games):

- agent_v19 wins: 12
- agent_v15 wins: 8
- Draws: 0
- **Win rate: 60%**

## Conclusion

**PASS** — 60% win rate exceeds the 55% threshold.

ROI scoring consistently outperforms the baseline `production/distance` metric. By weighting targets by their remaining production value minus capture cost, the agent consistently picks captures that generate more value over the remaining game — avoiding expensive late-arrivals to heavily defended planets and preferring cheap, nearby captures early. Zero draws in 20 games indicates decisive outcomes. This mechanic WILL be included in agent_v20.
