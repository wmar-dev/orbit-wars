# Feature Specification: Fix Comet Fleet Targeting

**Feature Branch**: `015-fix-fleet-targeting`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "from the replay in replays/78469577.json, it looks like I lost since the fleet I sent missed the planets and went out of the boundaries leading to wasted fleet. Fix errors that cause the fleets to miss the planets."

**Additional context**: "I miss when trying to chase comets."

## Background & Context

Replay 78469577 shows the agent losing due to fleets dispatched toward comet planets going out of bounds instead of capturing the comets. The root cause is a failure in the two-pass comet intercept prediction (`_comet_two_pass`).

### How Comet Interception Works

Comets travel along pre-defined curved paths at 4.0 units/turn, advancing one path index per turn. When the agent sends a fleet toward a comet, the fleet travels in a straight line at a fixed angle determined at launch time. The fleet must be aimed at the position where the comet **will be** when the fleet arrives — not where the comet is now.

### The Bug: Two-Pass Divergence

The `_comet_two_pass` function estimates the intercept point using two iterations:

1. **Pass 1**: Compute travel time `t0` to the comet's current position → predict comet position at `path_index + t0`.
2. **Pass 2**: Recompute travel time `t1` to the Pass-1-predicted position → predict comet position at `path_index + t1`.

The two-pass fails to converge when the comet's predicted position at `t0` is significantly farther from the source planet than the comet's current position. In this case `t1 >> t0`, so the comet at time `t1` is at a completely different location than at time `t0`. The fleet is aimed at `path[path_index + t0]` but the comet will actually be at `path[path_index + t1]` when the fleet arrives.

When `valid2=False` (comet lands before fleet arrives at the second-pass position), the code falls back to the first-pass position `(x1, y1)` as though it is a good intercept — but it is not. The fleet arrives at `(x1, y1)` in `t1` turns, while the comet by then is at a completely different position. The fleet misses the comet, continues along its fixed heading, and exits the board.

**Concrete example** (Step 159, replay 78469577):

- Source: planet 14 at (43.79, 15.39)
- Comet planet 22 at (17.05, 37.24), path_index=9, path length=36
- Pass 1: `t0=13.0` → predicted comet pos = path[22] = (46.62, 76.95)
- Pass 2: `t1=23.3` → predicted comet pos = path[32] → valid2=False (comet lands in <5 turns at time t1)
- **Fallback**: fleet aimed at (46.62, 76.95), but comet will be at path[32] when fleet arrives
- Result: fleet misses comet, exits board

---

## User Scenarios & Testing

### User Story 1 — Fleets aimed at comets successfully capture them (Priority: P1)

When the agent decides to intercept a comet, the fleet's trajectory intersects the comet's actual path at the correct time. No fleets exit the board as a result of missed comet intercepts.

**Why this priority**: Every fleet that exits the board due to a missed comet is ships permanently lost for zero gain — they could have reinforced existing planets or been sent to a capturable target instead. Comet capture provides production income, so missed intercepts doubly hurt the agent.

**Independent Test**: Run the agent against replay seed 78469577 or a game with active comets. Observe: no player-0 fleets exit the board on turns when comets are present and actively targeted. Any fleet aimed at a comet position must either capture the comet or land on another planet.

**Acceptance Scenarios**:

1. **Given** a comet moving along a known path and a source planet farther than the comet's current position, **When** the agent computes an intercept, **Then** the predicted interception time `t*` satisfies `t* ≈ distance(source, path[path_index + t*]) / fleet_speed` to within 0.5 turns.

2. **Given** the two-pass computation produces `t0 ≠ t1` (non-convergence), **When** the intercept is computed, **Then** the agent iterates additional passes until successive predictions differ by less than 0.5 path indices, or marks the comet as unreachable.

3. **Given** a comet that the agent cannot reach before it exits the board (remaining path steps < estimated travel time), **When** `_comet_two_pass` is called, **Then** it returns `valid=False` and the agent does not dispatch a fleet toward that comet.

4. **Given** a valid convergent intercept point, **When** the fleet is dispatched, **Then** the fleet's speed at dispatch matches the speed assumption used during intercept calculation.

---

### User Story 2 — Agent does not waste ships on unreachable comets (Priority: P2)

When a comet cannot be intercepted before it exits the board, the agent recognises this early and does not dispatch ships toward the comet. Those ships are redirected to viable targets.

**Why this priority**: The current code has a validity guard (`future_idx + 5 >= len(path)`) but the guard fires too late — after the two-pass produces a plausible-looking but incorrect position. Tightening the guard prevents silently bad decisions.

**Independent Test**: In a game where comets are far from all owned planets, confirm the agent sends zero fleets toward those comets (no wasted ships), and instead directs ships to other productive targets.

**Acceptance Scenarios**:

1. **Given** a comet where estimated travel time to any intercept point exceeds the comet's remaining path steps, **When** the agent evaluates that comet as a target, **Then** `valid=False` is returned and no fleet is sent.

2. **Given** a comet where convergence fails after the maximum number of iterations, **When** the intercept is evaluated, **Then** the comet is skipped as unreachable and a warning is logged if debug is enabled.

---

### Edge Cases

- What happens when the comet is within capture range of the source planet immediately (travel time ~0)? The current position should be used directly without iteration.
- What happens when fleet speed is slower than comet speed for small fleets? The iteration may never converge — the algorithm must detect this and return `valid=False`.
- What happens when the comet's path loops or the path index is near the end when queried? The remaining-steps check must correctly prevent dispatch in all near-boundary cases.

---

## Requirements

### Functional Requirements

- **FR-001**: The comet intercept algorithm MUST iterate until successive predicted intercept positions differ by less than 0.5 path-index steps (convergence criterion), with a maximum of 10 iterations.

- **FR-002**: The algorithm MUST return `valid=False` when the estimated intercept time exceeds the comet's remaining path steps minus a safety buffer of 3 turns, at any iteration.

- **FR-003**: The algorithm MUST return `valid=False` when convergence is not reached within the maximum iterations (non-convergent case treated as unreachable).

- **FR-004**: The fleet dispatch MUST use `fleet_speed(ships_needed)` where `ships_needed` is the same ships count used when computing the intercept — if the two values diverge, the intercept prediction must be recomputed with the actual dispatch size.

- **FR-005**: All changes MUST be applied to `main.py` (the current competition entry), preserving all other agent behaviour.

### Key Entities

- **Comet path**: Ordered list of (x, y) waypoints; comet advances one index per turn at `cometSpeed=4.0` units/turn.
- **Intercept point**: The future path position `path[path_index + t*]` where the fleet and comet meet simultaneously.
- **Convergence**: Successive iterations of `t` agree to within 0.5 turns.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a 50-game eval against the prior agent (e.g., agent_v55), the fixed agent dispatches zero fleets that exit the board while targeting comet planets, compared to the observed exits in the baseline.
- **SC-002**: In replay 78469577 specifically, re-running with the fixed agent shows no player-0 fleets exiting the board on turns when comet targeting is active.
- **SC-003**: The fixed agent's win rate against agent_v47 is maintained or improved (does not regress below 45% over 50 games).
- **SC-004**: Comet capture rate (fraction of targeted comets that are successfully captured vs. missed) improves by at least 50% relative to the bugged version.

---

## Assumptions

- Each path index corresponds to exactly one comet advance step (cometSpeed=4.0 ≈ distance between consecutive waypoints), so `path_index + int(travel_turns)` correctly indexes the future comet position.
- The `fleet_speed` function and its inputs are not changing; only the iteration count and convergence check in `_comet_two_pass` and `_comet_predicted_pos` need updating.
- A safety buffer of 3 turns before comet expiry (matching the existing `EVACUATE_THRESHOLD`) is sufficient to prevent dispatch toward a comet too close to the board edge.
- The fix is scoped to `_comet_two_pass` and optionally `_comet_predicted_pos`; no other functions require changes.
