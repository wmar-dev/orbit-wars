# Research: Comet Evacuation Fix, Fleet Targeting Accuracy, and Agent Improvement Experiments

**Feature**: 009-fix-comet-fleet-targeting | **Date**: 2026-05-30

---

## R-001 — Comet Remaining-Life Detection

**Decision**: Compute `remaining_turns = max(0, len(path) - path_index)` from the documented `paths` and `path_index` fields.

**Rationale**: The CONTEST.md Observation Reference table documents `comets` as containing `paths` (full trajectory for each comet) and `path_index` (current position along the path). `remaining_steps` is not listed. In the current code, `_build_comet_path_lookup` fetches `group.get("remaining_steps", 0)`, which defaults to 0 if the field is absent, causing `departing_this_turn` (remaining_steps == 0) to fire every turn and `evacuate_next_turn` (remaining_steps == 1) to never fire. The fix is to derive remaining turns from the documented fields.

**Evidence from CONTEST.md**: *"The `comets` observation field contains comet group data including `paths` (the full trajectory for each comet) and `path_index` (current position along the path), which can be used to predict future comet positions."*

**Alternatives considered**:
- Trust `remaining_steps` — rejected; not documented, may be absent or always 0.
- Detect departure reactively (observe comet disappearing from `comet_planet_ids`) — rejected; by then it is too late to evacuate.

**EVACUATE_THRESHOLD = 3**: Provides 3 turns of buffer before departure. Minimum fleet travel distance at speed 1.0 is 3 units in 3 turns, covering any locally adjacent planet. At speed 6.0, a fleet can reach 18 units away — sufficient for most board positions.

---

## R-002 — Orbit-Lead Convergence Algorithm

**Decision**: Fixed-point iteration, early exit at delta < 0.1 units, cap at 10 iterations.

**Rationale**: The intercept estimation is a fixed-point problem:

```
x* = planet_position(t0 + travel_time(x*))
```

where `travel_time(x*) = dist(mine, x*) / speed`. For orbiting planets, the tangential speed is `orbital_radius * angular_velocity` ≤ `30 * 0.05 = 1.5 units/turn` (well below minimum fleet speed of 1.0 at 1 ship). The fixed-point map is a contraction for `fleet_speed > tangential_speed`, which holds for virtually all real game states. Convergence in 3–6 iterations is typical.

**Previous approach**: `_refined_orbit_lead` ran exactly 2 iterations regardless of convergence. For targets 30+ units away at high angular velocity (0.05 rad/turn), the 2-iteration estimate can be off by 2–5 units, causing the fleet to miss.

**Comparison**:

| Method | Typical iterations to converge | Max error at v=0.05, dist=40 |
|--------|-------------------------------|-------------------------------|
| 1 iteration (old pass 1) | — | ~4.5 units |
| 2 iterations (old v31) | — | ~1.2 units |
| Fixed-point to eps=0.1 | 4–6 | <0.1 units |

**Cap at 10 iterations**: Prevents infinite loops in degenerate cases (e.g., planet oscillating near the rotation threshold). In practice, convergence happens in ≤6 iterations.

**Alternatives considered**:
- Bisection on travel time: binary search until `|t - dist(mine, planet(t)) / speed| < eps`. Correct but 3× more evaluations per call for equivalent accuracy.
- Analytical intercept: requires solving a transcendental equation (circular motion + linear fleet path). No closed form; impractical.

---

## R-003 — Comet Two-Pass Intercept

**Decision**: Two Newton-like passes capped; no full convergence loop.

**Rationale**: Comets move at a constant speed of 4.0 units/turn (per CONTEST.md) along a pre-computed discrete path. `_comet_predicted_pos` returns path[int(path_index + travel_turns)], so further iterations do not improve accuracy below path discretization error (~4 units per step). Two passes close the dominant first-order error:

- Pass 1: estimate from current position → travel_time_1 → predicted_pos_1
- Pass 2: re-estimate from predicted_pos_1 → travel_time_2 → predicted_pos_2

The second pass corrects for the fact that the fleet travels toward where the comet *will be*, not where it currently is. A third pass would correct a second-order term that is ≪ 4 units (path step size) and thus meaningless.

**Alternatives considered**:
- Full convergence loop (same as orbiting planets): wasteful due to path quantization floor.
- Single pass (current behavior): misses by up to `speed_comet * travel_time = 4 * (dist/fleet_speed)` units.

---

## R-004 — Evacuation Target Pool

**Decision**: Pool = all planets except the departing comet itself. Score owned planets by `production / (dist + ε)` (reinforce value), non-owned by ROI formula. Best across the pool wins.

**Rationale**: The original evacuate logic only considered `targets = [p for p in planets if p.owner != player]`. If all enemy/neutral planets are blocked by sun path check or are unsafe, ships were stranded. Including owned planets guarantees at least one valid destination (the nearest allied planet) in nearly all game states.

Unified scoring ensures the agent picks the globally best option:
- Evacuating to an owned planet: ships persist, reinforce garrison → value = `production / dist` (high for nearby high-production owned planets).
- Evacuating to an enemy planet: ships attack / capture → value = ROI (production × remaining turns / cost).

**Fallback order**: (1) highest-ROI non-owned safe planet, (2) highest-production-per-distance owned safe planet, (3) skip launch if no safe path exists.

**Note**: The evacuation aim point must use orbit-predicted positions (`_converged_orbit_lead`) for orbiting planets and `_comet_two_pass` for comet targets, not static current positions.

---

## R-005 — Reward Signal in Candidate Evaluation

**Decision**: Run `eval.py --reward-log` for each candidate. Use win rate as the pass/fail gate (55%) and mean per-turn reward delta as a secondary informational signal.

**Rationale**: `reward_signal.py` (feature-008) computes per-turn rewards capturing: planet captures, production delta, ship delta. A candidate that improves the mid-game reward trajectory but doesn't yet flip enough wins at N=50 may still be worth revisiting at N=100 or in a stacked combination. Recording the reward signal now provides that forward-looking data at no extra implementation cost (eval.py already supports `--reward-log`).

**Secondary signal computation** (via existing `reward_analysis.py`):
```
mean_reward_delta = mean(agent0_rewards) - mean(agent1_rewards)  # positive = candidate better
```

**Gate**: Win-rate ≥ 55% remains the sole promotion criterion. Reward delta is logged but does not override the gate.

---

## R-006 — Previously-Failed Candidate Re-evaluation Order

**Decision**: P → J → K → R → L → I

**Rationale**:

| Candidate | Prior result (vs v20) | Likely bug connection | Retest priority |
|-----------|----------------------|----------------------|-----------------|
| P: 3-iteration orbit lead | 20% | Directly addresses targeting bug — was trying to fix the same problem we're now fixing properly | Highest |
| J: smooth adaptive range | 50% (20 draws) | Statistical tie; targeting fix may break the tie | High |
| K: enemy-territory priority | 50% (20 draws) | Statistical tie; fixed targeting may expose priority advantages | High |
| R: production-squared ROI | 45% | Close to threshold; targeting fix may be enough | Medium |
| L: two-source coordinated attack | 40% | Larger gap; coordination logic independent of targeting | Medium |
| I: reactive defense dispatch | 5% | Very poor result; targeting fix unlikely to recover | Low |

Candidate I is still tested (constitution requires documentation), but expected to fail.

---

## R-007 — New Candidate Ideas (if all retests fail)

If all 6 retested candidates fail, the following new mechanics are candidates for evaluation:

- **Candidate T — Weighted multi-fleet attack**: When single sender has insufficient ships, allow a second sender to co-attack the same target in the same turn (ships from different planets, same destination). Different from Candidate L (two-source) in that it uses ROI gating rather than distance gating.
- **Candidate U — Comet opportunism v2**: Proactively launch a fleet to intercept an incoming comet if the comet path passes within INTERCEPT_RADIUS of an owned planet and the comet has ≥ INTERCEPT_SHIPS ships. Uses two-pass comet prediction.
- **Candidate V — Dynamic garrison floor**: Scale `GARRISON_FLOOR_FACTOR` by threat level (number of approaching enemy fleets within 20 units). Reduce floor when no threats visible; raise when under attack.
