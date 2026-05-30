# Experiment: Fleet-Speed Scoring + Fast-Fleet Send (US4)

**Date**: 2026-05-29
**Agent**: agent_v7.py
**Hypothesis**: Scoring targets by production / travel_turns (where travel_turns = distance / fleet_speed(n)) makes large garrisons favor far high-production planets correctly; sending at least MIN_FAST_FLEET=10 ships avoids slow 1-ship crawls.

## Change Description

Two modifications to the scoring and dispatch logic:

**Scoring change**: Replace `production / (distance + EPSILON)` with:
```python
production / (hypot(t.x - mine.x, t.y - mine.y) / fleet_speed(mine.ships) + EPSILON)
```
This makes fleet speed a factor in target attractiveness — a large fleet that can travel fast makes distant high-production planets relatively more attractive.

**Dispatch change**: Always send at least `MIN_FAST_FLEET = 10` ships:
```python
ships_to_send = max(ships_needed, MIN_FAST_FLEET)
ships_to_send = min(ships_to_send, mine.ships)
```
A 10-ship fleet travels at ~1.96 units/turn vs 1.0 for a 1-ship fleet — ~2× speed.

## Self-Play Result

| Metric | Value |
|--------|-------|
| agent_v7 wins | 10 / 20 |
| agent_v3 wins | 9 / 20 |
| Draws | 1 |
| Win rate (agent_v7) | **50.0%** |
| Threshold | ≥55% (11+ wins) |
| Result | **FAIL** (1 win short) |

Result confirmed across two identical runs (deterministic engine).

## SC-3 Regression (sun-avoidance)

Not run due to failed eval result. Sun-avoidance code unchanged from agent_v3 baseline.

## Analysis

The fleet-speed scoring change may actually hurt: when mine.ships is low (early game), `fleet_speed(mine.ships)` is near 1.0, so the score is nearly identical to raw distance. When mine.ships is high, far planets get a boost — but this can cause the agent to chase distant targets and skip nearby cheap captures, slowing early expansion.

The MIN_FAST_FLEET=10 change forces dispatching 10 ships even when 1-2 would suffice, draining planet garrisons faster than needed for easy captures.

## Conclusion

Fleet-speed scoring + fast-fleet send FAILS at 50% (10/20). The mechanic does not provide a net improvement — the scoring change may delay cheap captures and the MIN_FAST_FLEET may over-drain garrisons on easy targets. This mechanic is NOT included in agent_v8.
