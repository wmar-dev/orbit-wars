# Feature Specification: Comet Evacuation Fix, Fleet Targeting Accuracy, and Agent Improvement Experiments

**Feature Branch**: `009-fix-comet-fleet-targeting`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Fix comet evacuation before boundary exit, fix fleet targeting to hit orbiting planets, run agent improvement experiments"

## Background & Context

The current best agent (agent_v31, score 855.6) has two confirmed behavioral bugs and room for experimentation. This feature addresses both bugs as high-priority fixes, then layers improvement experiments on top of the fixed baseline.

### Bug 1 — Comet Non-Evacuation (Critical)

Per [CONTEST.md](../../CONTEST.md): *"When a comet leaves the board, it is removed along with any ships garrisoned on it. Comets are removed before fleet launches each turn, so you cannot launch from a departing comet."*

The agent currently detects comet departure via a `remaining_steps` field fetched from the observation. However, `remaining_steps` is **not** a documented field in the CONTEST.md observation reference (`paths` and `path_index` are documented; `remaining_steps` is not). If the field is missing or always zero, `evacuate_next_turn` never fires and ships are stranded. The correct approach is to compute remaining steps from `len(path) - path_index`.

Additionally, even when evacuation fires, the evacuation logic aims at the **current static position** of the destination planet rather than its orbit-predicted position, causing missed intercepts.

### Bug 2 — Fleet Targeting Misses (High)

Per [CONTEST.md](../../CONTEST.md): *"Orbiting planets rotate around the sun at a constant angular velocity (0.025–0.05 radians/turn, randomized per game). Use `initial_planets` and `angular_velocity` from the observation to predict their positions."*

The current `_refined_orbit_lead` performs only **2 Newton-like iterations** to estimate where a planet will be when the fleet arrives. For targets far from the launch planet, or targets rotating at the high end of the angular velocity range (0.05 rad/turn), 2 iterations diverge from the true intercept. Fleets overshoot or aim at stale positions. The fix is iterative convergence until the estimated intercept stabilises (delta < ε), or equivalently a bisection / fixed-point loop capped at ~10 iterations.

Comet targeting similarly uses a single-step `path_index + travel_turns` lookup without re-estimating travel time after updating the predicted position.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ships always evacuate before comet exits (Priority: P1)

The agent detects comet departure with enough lead time and launches all garrisoned ships to a safe destination before the comet is removed, so no ships are silently destroyed by boundary expiry.

**Why this priority**: Silent ship loss is a zero-ROI outcome — those ships could have been deployed productively. Fixing this is pure win with no trade-off. Per [CONTEST.md](../../CONTEST.md) the departure event is fully predictable from `path_index` and `paths`.

**Independent Test**: Run a game in which the agent owns a comet at some point. Confirm zero ships are ever removed due to comet boundary expiry (ships may be zero on departure only if evacuation happened earlier).

**Acceptance Scenarios**:

1. **Given** the agent owns a comet with N ships and `len(path) - path_index <= EVACUATE_THRESHOLD` turns remaining, **When** it is the agent's turn, **Then** it launches all N ships toward the highest-ROI reachable destination (owned planet for reinforcement or enemy/neutral planet for capture).
2. **Given** no safe evacuation target exists (rare), **When** the comet approaches boundary, **Then** the agent logs the inability and takes no action rather than crash.
3. **Given** a comet has 0 turns remaining (`path_index >= len(path)`), **When** the turn resolves, **Then** the agent has already evacuated on a prior turn and no ship loss occurs.
4. **Given** a comet with 1 turn remaining, **When** the evacuation target is an orbiting planet, **Then** the fleet is aimed at the orbit-predicted intercept position (not the current static position).

---

### User Story 2 — Fleets consistently intercept orbiting planets (Priority: P1)

Fleets aimed at orbiting planets reliably reach their destination rather than flying past into empty space. Intercept prediction converges to the true intercept point within the fleet travel window.

**Why this priority**: Per [CONTEST.md](../../CONTEST.md), the game explicitly provides `initial_planets` and `angular_velocity` so agents can predict positions — failing to use this accurately wastes ships and turns. Fix is pure upside.

**Independent Test**: In eval against the starter agent, count how many fleet launches end up out of bounds or visibly miss their target planet. Target: reduce observed misses by ≥ 80% vs. v31.

**Acceptance Scenarios**:

1. **Given** a fleet launched at an orbiting planet 30+ units away, **When** the angular velocity is at the high end (0.05 rad/turn), **Then** the fleet arrives at the planet (collision occurs) rather than passing through empty space.
2. **Given** an iterative convergence loop, **When** the estimated intercept stabilises (successive predictions differ by < 0.1 units), **Then** the loop terminates and that position is used as the aim point.
3. **Given** the target is a static planet (orbital radius puts it outside the rotation threshold), **When** a fleet is aimed at it, **Then** the current position is used directly (no unnecessary iteration).
4. **Given** a fleet aimed at a comet, **When** the intercept is computed, **Then** travel time is re-estimated after updating the predicted comet position (two-pass minimum, same as orbiting planets).

---

### User Story 3 — Agent improvement experiments on fixed baseline (Priority: P2)

After the two bugs are fixed (yielding a new baseline agent, e.g., v32), a new round of agent experiments tests candidate mechanics against the fixed baseline to push the score beyond 855.6. At least one candidate achieves ≥ 55% win rate vs. the fixed baseline.

**Why this priority**: Each prior round of experiments produced the current state-of-the-art. Running experiments on a bug-free baseline surfaces improvements that were previously masked by the comet and targeting bugs.

**Independent Test**: Evaluate at least 3 candidate variants against the fixed baseline over 50 games each; pick the best performer for integration if it clears the 55% threshold.

**Acceptance Scenarios**:

1. **Given** a fixed-baseline agent (bugs resolved), **When** previously-failed candidates (I, J, K, L, P, R) are retested over 50 games each, **Then** results are recorded in the agent docstring format (win rate, draw count, rationale) consistent with prior experiment logs.
2. **Given** a candidate that achieves ≥ 55% win rate vs. the fixed baseline, **When** it is promoted, **Then** it becomes the new default agent and README is updated.
3. **Given** all candidates score below 55%, **When** experiments conclude, **Then** the fixed-baseline agent (v32) is promoted as the new best and observations are recorded to guide the next round.

---

### Edge Cases

- What if the comet path list is empty? The agent must fall back to the comet's current position and treat it as stationary.
- What if all evacuation targets are blocked by the sun path check? The agent skips the launch silently rather than firing an unsafe fleet.
- What if the iterative orbit-lead loop oscillates and never converges? Cap iterations at 10 and use the last estimate.
- What if `fleet_speed` returns different values for the actual ships dispatched vs. the estimate used for lead prediction? Use the actual dispatch count for speed estimation.
- What if a comet is owned by the agent but has fewer ships than 1? Skip the evacuation launch.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The comet remaining-life calculation MUST use `len(path) - path_index` (derived from documented observation fields) rather than an undocumented `remaining_steps` field. Reference: [CONTEST.md](../../CONTEST.md) — Observation Reference table.
- **FR-002**: The agent MUST trigger comet evacuation when remaining turns ≤ `EVACUATE_THRESHOLD` (default: 3), not just when remaining_steps == 1, to ensure at least one turn of buffer before the comet is removed.
- **FR-003**: Evacuation fleet targets MUST include both owned planets (reinforcement) and non-owned planets (attack/capture), ranked by ROI. The agent MUST prefer the highest-value reachable destination and fall back to any safe owned planet if no enemy/neutral path is available. Positions MUST use orbit-predicted intercepts (same lead computation as normal attacks), not static current positions.
- **FR-004**: Orbit-lead prediction MUST iterate until convergence (successive intercept estimates differ by < 0.1 units) or until a maximum iteration cap (10) is reached.
- **FR-005**: Comet intercept prediction MUST re-estimate travel time after updating the predicted comet position (minimum two-pass, same standard as orbiting planets).
- **FR-006**: The experiment round MUST begin by retesting previously-failed candidates (Candidates I, J, K, L, P, R from prior agent history) against the fixed-baseline agent. New mechanics are added only if all retested candidates still fail. All candidates MUST be evaluated over ≥ 50 games before a pass/fail decision is made.
- **FR-007**: The 55% win-rate threshold MUST remain the acceptance bar for promoting any candidate into the combined agent.
- **FR-008**: The fixed-baseline agent (post bug-fix) MUST be saved as a new versioned file (e.g., agent_v32.py) and the README Agents table MUST be updated.

### Key Entities

- **Comet**: A temporary planet-like body tracked via `paths` and `path_index` in the observation. Remaining life = `len(path) - path_index`. Per [CONTEST.md](../../CONTEST.md): radius 1.0, production 1, exits board when it exhausts its path.
- **Orbit-lead intercept**: The predicted (x, y) position of a rotating planet when a fleet launched now will arrive. Depends on `angular_velocity`, `initial_planets`, fleet speed, and fleet size.
- **Candidate mechanic**: A single isolated behavioral change to the agent, evaluated by win rate over ≥ 50 games vs. the fixed baseline.
- **Fixed baseline agent**: The version of the agent with both bugs (comet evacuation, fleet targeting) corrected, before any experiment candidates are stacked.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero ships are lost to comet boundary expiry across a 50-game eval suite run after the fix.
- **SC-002**: Observed fleet-targeting misses (fleets going out of bounds or visibly missing their target) decrease by ≥ 80% vs. agent_v31 in a 50-game eval.
- **SC-003**: The fixed-baseline agent (v32) achieves a higher average score than agent_v31 (855.6) when both are evaluated against the same opponent set over 50 games.
- **SC-004**: At least 3 distinct candidate mechanics are tested in the experiment round with results documented.
- **SC-005**: All experiments conclude before any Kaggle submission. Only the best combined agent (bugs fixed + best passing candidate, or v32 alone if no candidate passes) is submitted to Kaggle, and the score improves over 855.6.

---

## Clarifications

### Session 2026-05-30

- Q: Should comet evacuation send ships to non-player-owned targets only, or also to owned planets as reinforcement? → A: Owned planets are valid evacuation destinations (ships reinforce garrison). Prefer the highest-value destination (owned or enemy/neutral) ranked by ROI; fall back to any owned planet if no safe attack path exists.
- Q: Should the fixed-baseline agent (v32) be submitted to Kaggle before experiments, or only the best combined agent after all experiments? → A: Run all experiments first; submit only the best combined agent. No intermediate v32 Kaggle submission.
- Q: Should the experiment round revisit previously-failed candidates (I, J, K, L, P, R) or only test new mechanics? → A: Revisit previously-failed candidates against v32 first (the bugs may have masked gains); add new mechanics only if all retested candidates still fail.

---

## Assumptions

- The `paths` list and `path_index` field are reliably present in the `comets` observation for all active comet groups, per [CONTEST.md](../../CONTEST.md).
- The `angular_velocity` and `initial_planets` fields are stable throughout a game (same values every turn), matching [CONTEST.md](../../CONTEST.md) description.
- Fleet speed uses `fleet_speed(ships_dispatched)` with the actual dispatch count, not the garrison count. The formula from [CONTEST.md](../../CONTEST.md): `speed = 1.0 + (maxSpeed - 1.0) * (log(ships) / log(1000))^1.5`.
- The eval harness (`eval.py`) and the 55% win-rate threshold are unchanged from the feature-008 workflow.
- Bug fixes are isolated to orbit-lead and comet-evacuation code paths; all other agent logic (ROI scoring, single-sender coordination, garrison floor, sun avoidance) is unchanged.
- Experiment candidates are independent of each other; combination of passing candidates is deferred to the next round if multiple pass.
