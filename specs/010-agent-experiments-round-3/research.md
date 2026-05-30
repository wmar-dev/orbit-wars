# Research: Agent Improvement Experiments — Round 6

**Branch**: `010-agent-experiments-round-3` | **Date**: 2026-05-30

## Unknown 1: Fleet destination inference without `to_planet_id`

**Decision**: Angle-based trajectory matching with `ANGLE_EPSILON = 0.1` radians (≈5.7°).

**Rationale**: `obs.fleets` provides `[id, owner, x, y, angle, from_planet_id, ships]` — no destination. To detect cross-turn redundant sends, project each friendly fleet forward at `fleet_speed(ships)` for its remaining travel time (estimated from current position and target's predicted position). Compare the fleet's heading (`angle`) against the angle from fleet position to each target's predicted position. Match threshold: 0.1 rad.

**Alternatives considered**:
- Stateful tracking between turns: Python agent functions are stateless; no inter-turn memory is available.
- Skip Candidate S: Valid fallback if angle inference proves too noisy in implementation; record result and move on.

**Risk**: False positives (inferring a fleet is heading to target T when it's actually heading to T' nearby). At 0.1 rad, planets more than ~10 units apart at the fleet's remaining distance won't be confused. Acceptable for first implementation.

---

## Unknown 2: Fixed-point convergence for transit-adjusted sizing

**Decision**: Single fixed-point iteration is sufficient.

**Rationale**: `ships_needed` determines `fleet_speed` which determines `travel_turns` which determines `projected_garrison` which determines `ships_needed`. One iteration changes the result by <1 ship in virtually all cases because the production term dominates and fleet speed is a slow-changing function (log curve). Two-iteration convergence checked via analysis: for production=5, distance=40, the difference between iteration 1 and iteration 2 is 0–2 ships. One iteration accepted.

**Alternatives considered**: Iterative convergence loop (Newton-style, as used in orbit-lead fix in v32): overkill for this use case; orbit-lead needed convergence because the target's position changes nonlinearly with time. Fleet sizing only needs to converge a linear function.

---

## Unknown 3: Optimal winning-state threshold for garrison reduction

**Decision**: `own_total / max(enemy_total, 1) >= 2.0` triggers `effective_floor_factor = 1`.

**Rationale**: 2.0× ensures the agent is in a materially dominant position before reducing garrisons. Prior ratio-gated mechanics (Candidates G, J, K) failed at lower thresholds (1.5×) because the ratio oscillated and caused loss spirals when the reduced garrison triggered a planet capture that tipped the ratio back below the threshold. At 2.0×, the agent has enough buffer that a single planet loss won't immediately flip below the gate.

**Alternatives considered**:
- 1.5× threshold: More aggressive, higher regression risk in 4-player scenarios where 3 opponents can converge.
- 3.0× threshold: Too conservative; rarely triggers in 2-player games that end before a 3:1 advantage builds.
- Continuous scaling: `floor_factor = max(1, 3 - 2 * (ratio - 1))` — smooth reduction. Rejected to keep the change isolated and interpretable; a binary gate is easier to diagnose if it fails.

---

## Unknown 4: Interaction between Candidate U (threat-aware garrison) and existing garrison floor

**Decision**: Replace `_garrison_floor(planet)` with `_threat_garrison_floor(planet, threat_dict)` in Candidate U agent.

**Rationale**: The current `_garrison_floor` function returns `max(planet.production * GARRISON_FLOOR_FACTOR, 1)`. For Candidate U, we override this to `max(planet.production * GARRISON_FLOOR_FACTOR, threat_dict.get(planet.id, 0))`. The threat dict is built once per turn by scanning `obs.fleets`. This is a drop-in replacement with no interaction with other dispatch logic.

**Why this is different from Candidate I (reactive defense, 16% vs v20)**: Candidate I *added dispatch moves to defend* — actively sending ships toward threatened planets. Candidate U only *raises the garrison floor*, preventing outbound attacks from threatened planets. It does not add any new dispatch instructions. This is the key distinction that may allow it to pass where Candidate I failed.

---

## Unknown 5: Combined agent mechanic ordering and interaction analysis

**Decision**: Apply mechanics in this order within the `agent(obs)` function:

1. Build `threat` dict from `obs.fleets` (shared by Candidates U and S)
2. Build `in_transit` dict from `obs.fleets` (Candidate S)
3. Compute `winning` flag and `effective_floor_factor` (Candidate V)
4. Compute `_garrison_floor` using `effective_floor_factor` and `threat` dict (U + V combined)
5. Run single-sender coordination with updated garrison floor
6. For each dispatch: compute `projected_garrison` with transit-adjusted sizing (Candidate T)
7. Apply `in_transit` deduction to `ships_needed` (Candidate S)

**Interaction analysis**:

| Pair | Interaction | Risk |
|------|-------------|------|
| S + U | Both parse obs.fleets — shared dict build | Low (one pass, separate dicts) |
| T + S | T raises ships_needed; S reduces it | Low (net: send exactly what's needed) |
| V + U | V reduces floor factor; U raises it for threats | Low (max() resolves cleanly) |
| T + V | V frees more ships; T requests more per target | Low (no logical conflict) |

**No mechanic conflicts identified.** All four can be combined cleanly.
