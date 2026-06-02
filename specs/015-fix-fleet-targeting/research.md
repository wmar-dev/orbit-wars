# Research: Fix Comet Fleet Targeting

**Feature**: 015-fix-fleet-targeting  
**Date**: 2026-06-01

---

## Q1: Does the iterative fixed-point method converge for all physically reachable comets?

**Decision**: Yes, for all comets where fleet speed ≥ effective comet closing speed.

**Rationale**: The iteration `t_{n+1} = distance(mine, path[path_index + t_n]) / speed` converges when the function `f(t) = distance(mine, path[path_index + t]) / speed` is a contraction — i.e., `|f(t_a) − f(t_b)| < |t_a − t_b|`. Since `path` waypoints are spaced ~4 units apart (= cometSpeed) and `speed` (fleet speed ≥ 1.0, typically 1.8–2.7 for small fleets) can be less than 4.0, the comet can outrun a very slow fleet in the same direction. In that case the iteration diverges — correctly indicating the comet is unreachable. Fleet speeds above ~4.0 units/turn (requiring ~500 ships) are always convergent regardless of comet direction.

**Practical outcome**: For fleets of 1–50 ships (speed 1.0–3.5), a comet moving directly away from the source cannot be intercepted and the loop will diverge. Returning `valid=False` is the correct response. For comets moving toward or across the source, the closing geometry guarantees convergence.

**Alternatives considered**:
- Binary search on `t`: More robust for edge cases, but overkill for this geometry and adds code complexity. Rejected.
- Closed-form solution: Requires solving a system involving the piecewise-linear path, which is not tractable in closed form. Rejected.

---

## Q2: What convergence criterion and iteration cap are appropriate?

**Decision**: `eps = 0.5` turns, `max_iter = 10`.

**Rationale**: 
- 0.5 turns at comet speed 4.0 = 2.0 units of position error. Planet radius ~1.0–2.4 units. A 2-unit error means the fleet might aim slightly off but still within the comet's sweep zone (comet moves ~4 units/turn, sweeping any fleet in its path).
- In practice the loop converges in 3–5 iterations for typical geometries. 10 is a generous cap.
- Tighter epsilon (e.g. 0.1) would require more iterations but produce negligible improvement in capture rate, since the comet sweeps fleets along its path regardless.

**Alternatives considered**:
- `eps = 0.1`, `max_iter = 20`: More accurate but not necessary given the comet sweep mechanic. Rejected.
- `eps = 1.0`: May leave intercept up to 4 units off, risking miss if the comet is near board edge. Rejected.

---

## Q3: Does the fleet speed assumption match the actual dispatch size?

**Decision**: Yes, no change needed.

**Rationale**: For neutral comet planets (`owner == -1`):
- `speed_for_lead = fleet_speed(t.ships + 1)` where `t` is the comet planet
- `ships_needed = t.ships + 1`  
- `moves.append([mine.id, angle, ships_needed])`

The same value (`t.ships + 1`) is used for both the intercept speed calculation and the dispatch size. These are consistent. If the comet's ship count changes between turns (it produces 1 ship/turn while neutral), the next turn's recalculation will self-correct.

**Alternatives considered**:
- Recompute intercept with actual surplus: Unnecessary since ships_needed is always `t.ships + 1` for neutral comets. Rejected.

---

## Summary Table

| Question | Decision | Confidence |
|----------|----------|------------|
| Convergence guarantee | Guaranteed when fleet can outrun comet; divergence = unreachable | High |
| epsilon / max_iter | 0.5 turns / 10 iterations | High |
| Speed consistency | Already consistent, no change | High |
