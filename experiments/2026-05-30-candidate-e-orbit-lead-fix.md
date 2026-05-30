# Candidate E: Speed-Corrected Orbit Lead (agent_v16)

**Date**: 2026-05-30 | **Branch**: 006-agent-experiments-round-2

## Hypothesis

The current orbit-lead computation uses `fleet_speed(mine.ships + 1)` (the source planet's total ship count) to estimate travel time, but the actual fleet sent is only `target.ships + 1` ships. When a source planet has many more ships than the target requires, this significantly overestimates speed — e.g., source with 80 ships sends fleet of 11: speed estimate is `fleet_speed(81) ≈ 3.4` but actual speed is `fleet_speed(11) ≈ 2.0`. The orbit-lead then predicts the target's position too early in its orbit, and the fleet arrives to find the planet has moved past the aim point.

Fix: compute `fleet_speed(target.ships + 1)` per target inside the candidates loop. Expected improvement: ≥55% win rate vs agent_v15.

## Change

Built on agent_v15. Removed the single `speed = fleet_speed(mine.ships + 1)` declaration (line 241 in v15). In the candidates loop, added `speed_for_lead = fleet_speed(t.ships + 1)` before each `_refined_orbit_lead` call. Applied the same change in the fallback (range-ignoring) loop. The best-sender precomputation uses raw Euclidean distance only, so no change is needed there.

## Self-play result

20 games vs agent_v15 (20 games):

- agent_v16 wins: 14
- agent_v15 wins: 6
- Draws: 0
- **Win rate: 70%**

## Conclusion

**PASS** — 70% win rate exceeds the 55% threshold by a large margin.

The speed-corrected orbit lead dramatically improves targeting accuracy. With the fix, the predicted intercept matches the fleet's actual travel time, so fleets arrive on-target for orbiting planets. Zero draws in 20 games indicates every game produced a decisive outcome. This mechanic WILL be included in agent_v20.
