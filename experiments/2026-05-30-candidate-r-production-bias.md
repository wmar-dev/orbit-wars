# Candidate R: Production-Squared ROI Bias (agent_v29)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

The current ROI formula `production * (100 - travel) / cost` weights production linearly. High-production planets are good, but the formula doesn't differentiate strongly enough between production=3 and production=5 planets when other factors are similar. Squaring the production term — `production^2 * (100 - travel) / cost` — creates a much stronger preference for high-production targets, concentrating the agent's attacks on the most valuable planets from the start. This creates decisive early advantages and asymmetric game outcomes. Expected improvement: ≥55% score vs agent_v20.

## Change

Built on agent_v20. Change `_roi()` to square the production term:

```python
def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return (t.production ** 2) * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)
```

All other logic unchanged. This is unconditional (always active) and changes target selection from the first turn.

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v29 wins: 9
- agent_v20 wins: 11
- Draws: 0
- **Win rate: 45%**
- **Score: 45%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 45% score is below the 55% threshold.

Squaring the production term over-concentrates targeting on the highest-production planets, sometimes ignoring cheap nearby lower-production planets that would be more efficient to capture. The original linear weighting better balances production value vs. cost and distance. This mechanic will NOT be included in agent_v30.
