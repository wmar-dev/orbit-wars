# Candidate P: 3-Iteration Orbit Lead (agent_v27)

**Date**: 2026-05-30 | **Branch**: 007-more-agent-experiments

## Hypothesis

Agent_v20 uses a 2-iteration orbit-lead refinement (`_refined_orbit_lead`): estimate travel time from current position, predict planet position, re-estimate travel time from predicted position. A 3rd iteration should reduce aim error further for fast-orbiting planets, improving capture rate on high-value orbiting targets. This is an unconditional accuracy improvement with no strategic tradeoff — it always makes the aim better. Expected improvement: ≥55% score vs agent_v20 (decisive wins from more accurate captures).

## Change

Built on agent_v20. Extend `_refined_orbit_lead` from 2 iterations to 3:

```python
def _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed):
    t0 = math.hypot(t.x - mine.x, t.y - mine.y) / speed
    x1, y1 = _predict_planet_pos(t, initial_planets_map, angular_velocity, t0)
    t1 = math.hypot(x1 - mine.x, y1 - mine.y) / speed
    x2, y2 = _predict_planet_pos(t, initial_planets_map, angular_velocity, t1)
    t2 = math.hypot(x2 - mine.x, y2 - mine.y) / speed
    return _predict_planet_pos(t, initial_planets_map, angular_velocity, t2)
```

No other changes.

## Self-play result

20 games vs agent_v20 (seeds 0–19):

- agent_v27 wins: 4
- agent_v20 wins: 16
- Draws: 0
- **Win rate: 20%**
- **Score: 20%**
- Pass threshold: ≥55% score

## Conclusion

**FAIL** — 20% score is well below the 55% threshold.

The 3-iteration orbit lead actually hurt performance. The 2-iteration refinement in agent_v20 is already sufficient — adding a 3rd iteration may cause the fleet to aim slightly past the actual planet position (overshoot the refinement), reducing capture rate for planets on curved orbits. The 2-iteration convergence was already tuned to the orbit_wars physics. This mechanic will NOT be included in agent_v30.
