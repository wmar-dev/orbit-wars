# Experiment: Combined Agent (US5)

**Date**: 2026-05-29
**Agent**: agent_v8.py
**Hypothesis**: Stacking the two mechanics that individually passed ≥55% win rate (orbit-lead and comet opportunism) should produce an agent that is stronger than either alone, validated against agent_v3.

## Mechanics Included (both passed ≥55%)

| Mechanic | Source | Isolated Win Rate |
|----------|--------|-------------------|
| Orbit-lead targeting | agent_v4.py | 85.0% |
| Comet opportunism | agent_v5.py | 55.0% |

## Mechanics Excluded (failed ≥55%)

| Mechanic | Source | Isolated Win Rate | Reason |
|----------|--------|-------------------|--------|
| Defensive reinforcement | agent_v6.py | 20.0% | Blocked attack moves, hurt aggression |
| Fleet-speed scoring + fast-fleet | agent_v7.py | 50.0% | Delayed cheap captures, over-drained garrisons |

## Implementation

Orbit-lead and comet opportunism are applied together per target in a single candidate-building pass:
- For comet targets: use `comet_path_lookup` predicted position (skip if expiring within 5 turns).
- For non-comet targets: use `_predict_planet_pos` with `angular_velocity` and `initial_planets_map`.
- Owned comet lifecycle: skip `departing_this_turn` as sources; evacuation dispatch for `evacuate_next_turn`.
- Sun-avoidance applied to predicted positions.

## Self-Play Result

| Run | agent_v8 wins | agent_v3 wins | Draws | Win Rate |
|-----|---------------|---------------|-------|----------|
| Run 1 (seeds 0–19) | 18 | 2 | 0 | **90.0%** |
| Run 2 (seeds 0–19) | 18 | 2 | 0 | **90.0%** |
| Threshold | — | — | — | ≥55% |
| Result | — | — | — | **PASS** |

Both runs identical — confirms deterministic engine with same seeds.

## Conclusion

The combined agent achieves 90% win rate vs agent_v3, matching agent_v4's isolated performance and significantly outperforming the 55% threshold. The orbit-lead mechanic is the dominant contributor; comet opportunism adds marginal but consistent improvement. agent_v8 is the best agent produced in this experiment series and is the recommended candidate for Kaggle submission.

**Best agent**: agent_v8.py (90% vs agent_v3, 18/20 decisive wins)
