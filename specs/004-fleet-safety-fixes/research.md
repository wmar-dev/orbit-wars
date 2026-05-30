# Research: Fleet Safety Validation & Fixes

**Date**: 2026-05-30
**Feature**: 004-fleet-safety-fixes

## R1 — Turn order and source planet motion

**Decision**: The launch origin is the planet's current observed position. No source-position prediction needed.

**Rationale**: Per CONTEST.md turn order, fleet launch (step 3) precedes planet rotation (step 6). The source planet is at its current position when the fleet spawns. The fleet moves in the same turn before the source planet rotates.

**Alternatives considered**: Predicting source position at launch time — not needed given the turn order.

## R2 — Intermediate planet obstruction

**Decision**: Extend `_path_safe` to check the full ray against every non-target planet using `_segment_dist_to_sun`-style math with clearance `planet.radius + 1.0`.

**Rationale**: CONTEST.md states any fleet whose path segment comes within a planet's radius triggers combat. Agent v9 only checks the sun. Any orbiting or static planet between source and target can silently consume the fleet.

**Alternatives considered**: Only checking static planets — rejected because orbiting planets are the most common obstruction hazard given the 4-fold symmetric map layout near the center.

## R3 — Diagnostic harness inference strategy

**Decision**: Instrument agent via wrapper; track fleet list across turns; infer outcome when fleet disappears by checking target planet state.

**Rationale**: No environment patching required. The fleet list is available in every observation. Disappearance + target planet state change = arrival; disappearance without state change = transit loss.

**Alternatives considered**: Post-hoc ship count diffing — feasible but less precise than tracking individual fleet IDs across turns.

## R4 — travel_turns refinement

**Decision**: One iteration of refinement for orbit-lead candidates.

**Rationale**: The current estimate uses `dist(source, current_target)` which undercounts for planets that have moved away from source. One refinement step (predict at t0, recompute dist to predicted pos, get t1) converges to within <1 turn error for typical orbital speeds.

**Alternatives considered**: Iterating to convergence — not needed; single refinement is sufficient given angular velocity of 0.025–0.05 rad/turn and travel times of 10–50 turns.

## R5 — Comet path index safety

**Decision**: Clamp `future_idx = min(int(path_index + travel_turns), len(path) - 1)` and add `if not path: continue` guard.

**Rationale**: Comet paths have finite length. Near end-of-path, `future_idx` can exceed bounds, causing an IndexError or silent access of the wrong position.

**Alternatives considered**: Already covered by the `future_idx + 5 >= len(path)` guard in v9 — but this guard only triggers if there are fewer than 5 steps remaining. A direct clamp is more robust and simpler.
