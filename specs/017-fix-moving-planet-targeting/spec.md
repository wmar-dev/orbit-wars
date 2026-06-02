# Feature Specification: Fix Fleet Targeting When Both Source and Target Are Moving

**Feature Branch**: `017-fix-moving-planet-targeting`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "It looks like we are still missing planets, when both the target and source are moving. Fix the issue."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fleet Reaches Orbiting Target From Orbiting Source (Priority: P1)

A fleet dispatched from an orbiting (inner) planet toward another orbiting planet should arrive at the target planet, not pass through empty space where the target used to be. Currently, when both the source and target planet are orbiting, the fleet's aim point is computed with a positional error that causes the fleet to miss.

**Why this priority**: This is the primary failure mode. Every attack on an orbiting enemy planet that happens to be launched from an inner orbiting planet is potentially wasted. Inner planets are the most productive and are the natural attacking bases.

**Independent Test**: Run `eval.py` comparing a patched agent against agent_v56 over 50 games. A valid fix shows ≥ 55% win rate. Separately, add a diagnostic print in the agent that logs "miss" whenever a dispatched fleet's travel time and aim vector diverge from what the game engine records — confirm zero misses in a 5-game verbose run.

**Acceptance Scenarios**:

1. **Given** an owned orbiting source planet and an orbiting target planet (neutral or enemy), **When** the agent dispatches a fleet, **Then** the fleet arrives at the target planet's location when the fleet completes travel, with zero misses across a 20-game diagnostic run.
2. **Given** both source and target are in inner orbits (small orbital radii, faster apparent movement), **When** the fleet is dispatched, **Then** the fleet still intercepts correctly — the faster relative movement does not cause a larger positional error.
3. **Given** the source planet just orbited through a large arc (many turns since game start), **When** a fleet is dispatched, **Then** the intercept prediction remains accurate regardless of the source's orbital phase.

---

### User Story 2 — Path Safety Check Uses Consistent Planet Positions (Priority: P2)

The path safety check (`_path_safe`) currently uses planet positions at the moment of dispatch. When both source and target are orbiting, intermediate planets along the flight path may be at different positions during the fleet's actual transit. A fleet may be incorrectly blocked (valid route marked unsafe) or incorrectly allowed (path will become unsafe mid-flight).

**Why this priority**: An incorrect block means a good attack opportunity is lost. An incorrect allow is a safety hazard (fleet hits an intermediate planet). Both reduce agent performance but the dispatch failure is more common.

**Independent Test**: Run 20 games with verbose logging. Count dispatches blocked by `_path_safe` where the target was subsequently successfully attacked by the opponent — these are false-block candidates. The count should be lower with the fix than without.

**Acceptance Scenarios**:

1. **Given** two orbiting planets with a third orbiting planet currently in between them, **When** the orbiting intermediate will have cleared the path by the time the fleet reaches that region, **Then** the dispatch is allowed (not incorrectly blocked).
2. **Given** two orbiting planets with a clear current path, **When** an intermediate planet will orbit into the path during the fleet's travel, **Then** the dispatch is either blocked or the fleet safely avoids the intermediate planet.

---

### Edge Cases

- What happens when the source planet completes a full orbit between game start and dispatch? The launch position should still be the source's actual position at dispatch time.
- How does the system handle the case where source and target orbital radii are equal (same ring)? They orbit at the same speed, so the intercept geometry is a constant-offset interception.
- What if the fleet travel time is very short (adjacent orbits) — is the error still present or negligible?
- What if `angular_velocity` is zero (static planets, outer ring)? The fix must not regress these cases.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orbit lead calculation MUST use the source planet's position at the moment of fleet launch, not a position that may be inconsistent with how the game engine determines launch origin.
- **FR-002**: The fleet aim angle MUST be computed from the same launch position used in the travel time calculation, so direction and distance are geometrically consistent.
- **FR-003**: When both source and target are orbiting, fleet intercept accuracy MUST be equivalent to the accuracy observed when only the target is orbiting.
- **FR-004**: The fix MUST NOT regress targeting accuracy for static-source scenarios (outer ring planets or planets with near-zero orbital radius).
- **FR-005**: The fix MUST NOT regress comet intercept accuracy (the iterative comet fix from v56 must remain intact).
- **FR-006**: All existing `_path_safe` checks MUST continue to use positions that are geometrically consistent with the fleet path being validated.

### Key Entities

- **Source planet**: The owned planet from which a fleet is dispatched. May be orbiting (inner ring) or static (outer ring).
- **Target planet**: The neutral or enemy planet being attacked. May be orbiting or static.
- **Fleet launch position**: The precise `(x, y)` from which the game engine starts the fleet moving. If this differs from `planet.x, planet.y` in the observation, the orbit lead must use the actual launch position.
- **Orbit lead intercept point**: The predicted future position `(bx, by)` of the target when a fleet arrives. All downstream calculations (aim angle, fleet sizing, path safety) must use the same intercept point.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The patched agent achieves ≥ 55% win rate vs agent_v56 over 50 games, demonstrating that fixing the miss bug provides a net gameplay improvement.
- **SC-002**: In a 20-game diagnostic verbose run, zero fleets dispatched toward orbiting planets fail to arrive at the target (confirmed by checking fleet final positions in the game log).
- **SC-003**: The patched agent's win rate vs agent_v56 on maps with exclusively static (outer-ring) planets remains at 48–52% (no regression for the static case).
- **SC-004**: Self-play win rate (patched vs patched) remains within 48–52%, confirming the fix is symmetric and not an artifact of asymmetric map positions.

## Assumptions

- The game engine's fleet launch origin for a planet is deterministic and derivable from the planet's observable position and orbital parameters — it is not arbitrary or randomized.
- The `angular_velocity` field in `obs` is a single scalar that applies uniformly to all orbiting planets (rigid-body orbital model).
- The existing `_converged_orbit_lead` iterative structure is correct for predicting the TARGET's future position; only the SOURCE position input needs correction.
- The outer-ring planets (large orbital radius, near or beyond the board boundary check) are treated as static by `_predict_planet_pos` and are unaffected by this fix.
- Comet planets have a different motion model (precomputed path lookup) and are handled separately; this fix applies only to regularly orbiting planets.
