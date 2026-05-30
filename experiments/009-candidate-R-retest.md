# Candidate R Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Hypothesis

Candidate R (production-squared ROI, 45% score vs v20 — FAIL) squares the production term
in the ROI numerator to amplify preference for high-production targets. Previously failed vs
v20 because the stronger preference for high-production planets sometimes ignored cheap nearby
lower-production planets. With the bug-fixed baseline v32 (converged orbit-lead), the agent
can now accurately reach high-production orbiting targets — the targets that production-squared
scoring most values. This may flip the result.

## Change vs agent_v32

Changed `_roi()` to use `(t.production ** 2)` instead of `t.production` in the numerator.
All other logic unchanged.

```python
def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return (t.production ** 2) * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)
```

## Self-Play Result (50 games, agent0=cand_R, agent1=agent_v32)

- Agent0 wins: 30
- Agent1 wins: 20
- Draws: 0
- Win rate: **60.0%** (draws count as losses)
- Score: **60.0%** (draws count as 0.5)
- Mean reward delta (cand_R - v32): **+0.0239**

## Conclusion

**PASS** — 60% score exceeds the 55% gate. Production-squared ROI now works on the
bug-fixed baseline. Analysis: With converged orbit-lead accurately targeting fast-orbiting
high-production planets, the stronger preference for production=4/5 targets pays off. Under
v20's targeting bugs, fleets aimed at these high-value orbiting planets often missed, making
the production^2 bias counterproductive. With accurate targeting fixed, concentrating on
the highest-production planets is genuinely more efficient.

Reward delta of +0.0239/turn (vs v32's +0.0288/turn over v31) confirms the mechanic
improves mid-game decision quality.

This mechanic WILL be included in agent_v33.
