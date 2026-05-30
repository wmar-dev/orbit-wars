# Feature Specification: Fleet Safety Validation & Fixes

**Feature Branch**: `004-fleet-safety-fixes`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Do another round of experiments to check if we are not wasting any of the fleet by sending them into the sun, not hitting the planets and going out of bounds. Fix any issues with current best model agent_v9.py around these concerns."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Diagnose Fleet Loss Root Causes (Priority: P1)

A researcher runs controlled experiments against agent_v9.py to measure how many ships are wasted by: (a) flying into the sun, (b) missing their intended target planet, or (c) traveling out of bounds. Baseline numbers for each failure mode are recorded.

**Why this priority**: You cannot fix what you cannot measure. Quantifying how often each failure mode occurs tells the team where to focus and whether a fix actually worked.

**Independent Test**: Can be tested by running agent_v9 in a simulated match and logging every fleet launch — track which fleets are destroyed by the sun, which never reach a planet, and which exit the map boundary.

**Acceptance Scenarios**:

1. **Given** a full simulated match using agent_v9.py, **When** all fleet launches are recorded with their outcomes, **Then** the proportion of fleets lost to sun collision, missed intercept, and out-of-bounds can be reported numerically.
2. **Given** the diagnostic data, **When** results are compared across multiple seeds/matches, **Then** each failure mode has a consistent, reproducible frequency (variance < 10% across runs).

---

### User Story 2 - Fix Sun-Crossing Fleets (Priority: P2)

The agent correctly rejects any launch whose straight-line path would pass through or clip the sun exclusion zone, even when the target is behind the sun from the launching planet's perspective.

**Why this priority**: Ships lost to the sun are a direct resource drain with no upside. This is the highest-impact single failure mode.

**Independent Test**: Can be tested by setting up scenarios where the only available target is behind the sun, and verifying the agent either finds an alternate target or skips the launch rather than burning ships.

**Acceptance Scenarios**:

1. **Given** a planet whose direct path to a target passes through the sun exclusion zone, **When** the agent evaluates that target, **Then** the launch is rejected and no ships are dispatched on that trajectory.
2. **Given** a planet with multiple targets — some sun-safe, some not — **When** the agent selects a target, **Then** it always selects from the safe set.
3. **Given** no sun-safe targets exist, **When** the agent evaluates all candidates, **Then** it dispatches no fleet rather than sacrificing ships to the sun.

---

### User Story 3 - Fix Out-of-Bounds Target Predictions (Priority: P3)

Orbit-lead and comet path predictions that fall outside the 0–100 board boundary are detected and discarded before a fleet is dispatched toward them.

**Why this priority**: Ships aimed at out-of-bounds coordinates fly off the map and are permanently lost without dealing damage. This wastes ships that could otherwise be used productively.

**Independent Test**: Can be tested by logging all predicted target coordinates and verifying none fall outside [0, 100] × [0, 100] before a fleet is dispatched.

**Acceptance Scenarios**:

1. **Given** an orbit-lead prediction for a planet near the board edge, **When** the predicted position would be outside [0, 100], **Then** the candidate is rejected and the fleet is not launched.
2. **Given** a comet path entry whose future position exceeds board bounds, **When** the agent evaluates that entry, **Then** it is treated as invalid and skipped.

---

### User Story 4 - Fix Target Miss / Intercept Accuracy (Priority: P3)

Fleets launched with orbit-lead or comet prediction reliably arrive at the planet's actual location (within the planet's capture radius) rather than arriving at an empty coordinate.

**Why this priority**: A fleet that travels safely but misses the planet is still wasted. Intercept accuracy directly affects capture rate.

**Independent Test**: Can be tested by logging each fleet's aimed coordinate versus the planet's actual position at arrival time, then measuring the distance. A hit is within the planet's radius.

**Acceptance Scenarios**:

1. **Given** a fleet dispatched using orbit-lead prediction, **When** the fleet arrives at the estimated turn, **Then** the planet is within capture range at least 80% of the time.
2. **Given** a fleet dispatched using comet path prediction, **When** the fleet arrives, **Then** the comet planet is within capture range at least 80% of the time.

---

### Edge Cases

- What happens when all targets are behind the sun from all owned planets?
- How does the agent handle a planet very close to the sun where most trajectories are unsafe?
- What if orbit-lead predicts a position exactly on the board boundary (0 or 100)?
- What if `travel_turns` is fractional and the predicted position oscillates between in-bounds and out-of-bounds?
- What if a comet's path list is empty or shorter than `future_idx`?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The experiment harness MUST record, per fleet launch: source planet ID, target planet ID, aimed coordinates, and inferred outcome — derived by comparing ship counts and planet ownership changes across turns (no environment patching required). Results MUST be written as CSV or JSON files to a `logs/` directory, one file per run.
- **FR-002**: The agent MUST reject any fleet whose aimed trajectory crosses or touches the sun exclusion zone (radius 12.0 from sun center at [50, 50]).
- **FR-003**: The agent MUST reject any predicted target position where x < 0, x > 100, y < 0, or y > 100.
- **FR-004**: The agent MUST always hold ships when all candidates are invalid — no unsafe or out-of-bounds launches are permitted under any game state, including late-game losing positions.
- **FR-005**: Orbit-lead predicted positions MUST account for actual orbital period, not just angular velocity, to minimize intercept miss rate.
- **FR-006**: Comet path lookups MUST validate that `future_idx` is within the path list bounds before accessing the position.
- **FR-007**: All fixes MUST be applied to `agent_v10.py` so agent_v9.py remains unchanged as a baseline.
- **FR-008**: After fixes, a head-to-head evaluation MUST be run (agent_v10.py vs agent_v9.py) over at least 20 matches to confirm improvement.

### Key Entities

- **Fleet**: A group of ships dispatched from a planet toward a target coordinate; characterized by source, aimed angle, ship count, and outcome.
- **Candidate**: A (target planet, predicted x, predicted y) triple evaluated for safety before a fleet is dispatched.
- **Path Safety Check**: The combined validation that (a) the trajectory ray avoids the sun exclusion zone and (b) the target coordinates are within board bounds.
- **Intercept Accuracy**: The fraction of fleet arrivals where the target planet is within capture range at the time of arrival.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Experiment logs show the per-failure-mode ship loss rate for agent_v9.py as a numeric baseline across at least 20 matches.
- **SC-002**: The fixed agent reduces sun-destroyed fleet incidents to 0% across all test matches.
- **SC-003**: The fixed agent reduces out-of-bounds fleet incidents to 0% across all test matches.
- **SC-004**: Fleet-to-target intercept accuracy (fleets that reach a planet within capture radius) improves by at least 10 percentage points versus the agent_v9 baseline.
- **SC-005**: The fixed agent achieves a win rate of at least 75% in head-to-head evaluation against agent_v9 over 20+ matches.

## Clarifications

### Session 2026-05-30

- Q: How are fleet outcomes observed by the diagnostic harness? → A: Infer outcomes post-match by comparing ship counts and planet ownership across turns (no environment patching required).
- Q: What should the fixed agent file be named? → A: agent_v10.py
- Q: Where should experiment logs be persisted? → A: CSV or JSON files written to a `logs/` directory, one file per run.
- Q: What minimum match count for the diagnostic baseline? → A: 20 matches for both baseline and head-to-head (consistent standard).
- Q: When no safe candidates exist, should the agent ever take an unsafe shot? → A: Always hold — never dispatch a fleet on an unsafe path, regardless of game state.

## Assumptions

- agent_v9.py is the current best agent and serves as the immutable baseline; all fixes are applied to `agent_v10.py`.
- Experiment logs are written as CSV or JSON to a `logs/` directory; the directory is created if it does not exist.
- The diagnostic harness infers fleet outcomes by comparing ship counts and planet ownership across turns; no environment patching or source modification is required.
- "Out of bounds" means any coordinate strictly outside [0, 100] × [0, 100].
- Capture radius is the planet's `radius` field; a fleet "hits" a planet if it arrives within that radius.
- The experiment harness runs locally using `kaggle_environments` and does not require submission to Kaggle.
- Orbit-lead accuracy improvements are limited to correcting angular velocity application; no new orbital mechanics are introduced.
