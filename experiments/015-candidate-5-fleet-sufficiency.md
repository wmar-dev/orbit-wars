# Experiment 015: Candidate 5 — Friendly Fleet Sufficiency Check

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**Candidate agent**: agent_v52.py
**Target**: ≥56% win rate vs agent_v47 (50 games)

## Hypothesis

When a friendly fleet already in transit to a target has enough ships to capture it, dispatching a second fleet wastes ships that could go elsewhere. The agent has no mechanism to detect this; it re-evaluates all targets from scratch each turn and may send another fleet to an already-covered target.

Note: the original spec framing (subtract in-transit ships from surplus) was found incorrect — the game engine already deducts ships from garrison when dispatched, so re-subtracting would double-count. The correct approach is to skip targets already covered by a sufficient in-transit friendly fleet.

Fix: build `covered_targets` set each turn by scanning own fleets and checking angle alignment to target predicted positions. If a friendly fleet of sufficient size is heading to a target, skip assigning any sender to that target.

## Change

After threat dict construction, build `covered_targets = set()`: for each own fleet `f`, check angle alignment to each target's predicted position (ANGLE_EPSILON tolerance); if aligned and `f.ships >= rough_ships_needed(t)`, add `t.id`. In `best_sender` outer loop, skip `t` if `t.id in covered_targets`.

## Self-play result

Win rate vs agent_v47: 44% (22W/28L/0D) — below 56% threshold

## Conclusion

FAIL — 44% is a modest regression below 50%, consistent with noise but in the wrong direction. Skipping targets that already have a friendly fleet in transit is too conservative: the angle-matching heuristic generates false positives (a fleet heading toward A may also align with B further along the same heading), causing valid targets to be incorrectly blocked. Same geometry problem as the race-filtering experiment in round 014 (Candidate v44). Ruled out for combined agent.
