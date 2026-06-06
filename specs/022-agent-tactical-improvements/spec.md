# Feature Specification: Agent Tactical Improvements

**Feature Branch**: `022-agent-tactical-improvements`

**Created**: 2026-06-06

**Status**: Draft

**Input**: Three high-evidence improvement directions identified via replay analysis and experiment logs against the v60 beam-search agent (Kaggle score 916.9, leaderboard gap ~800 points to top).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Early-Game Dispatch Aggressiveness (Priority: P1)

The agent dispatches ships toward the nearest cheap neutral planets within turns 0–15 without waiting to accumulate a large garrison. Currently the agent stockpiles 50+ ships on the home planet while the opponent captures neutrals 1–3 turns earlier, establishing a compounding production advantage.

**Why this priority**: Replay analysis showed median divergence at turn 8 across all analyzed losses. One extra neutral captured by turn 10 changes the production curve for the entire game. This is the most direct cause of the leaderboard gap.

**Independent Test**: Run a 50-game eval between the new agent and v60. Measure average planet count at turn 20 (should increase from ~3.4 to ≥4.0) and median divergence turn (should move from 8 to ≥20).

**Acceptance Scenarios**:

1. **Given** a home planet with garrison above the neutral capture cost, **When** a neutral planet is reachable and capturable within its production growth window, **Then** the agent dispatches a minimal fleet immediately rather than waiting for larger accumulation.
2. **Given** the agent is in turns 0–15, **When** there are uncontested neutrals nearby, **Then** the dispatch threshold for neutral targets is lower than mid-game, allowing thin-margin sends.
3. **Given** a neutral planet is growing garrison faster than the fleet can travel, **When** the agent evaluates the capture, **Then** it sends a correctly-sized fleet accounting for garrison growth during travel.
4. **Given** a minimal fleet is sent early, **When** it arrives and the garrison has grown due to production, **Then** the fleet size is sufficient to capture (no wasted trips).

---

### User Story 2 — Garrison Floor Reduction Under No Threat (Priority: P2)

The agent holds fewer ships in reserve when no enemy fleets are detected incoming toward its planets. Currently the garrison buffer (`production × 2` added by the threat-aware logic in v50) fires even with zero incoming threats, preventing the agent from sending ships it could safely commit.

**Why this priority**: Measured 2× dispatch frequency gap in turns 30–50 (0.43/turn vs opponent's 0.92/turn). Addressed directly after the early-game problem is fixed, as it affects the compound phase.

**Independent Test**: Run a 50-game eval vs v60. Measure average dispatch count per turn in turns 30–50 (should increase from ~0.43 toward ~0.7–0.8). Measure ship-to-planet ratio at turn 100 (should reduce from ~56 ships/planet, meaning fewer ships are being stockpiled unused).

**Acceptance Scenarios**:

1. **Given** no enemy fleets are en route to any of the agent's planets, **When** the agent evaluates dispatch candidates, **Then** the garrison floor uses the base factor without the threat buffer.
2. **Given** an enemy fleet is detected heading toward a planet, **When** that specific planet evaluates its garrison, **Then** the threat buffer remains active for that planet only (not all planets).
3. **Given** the agent has multiple owned planets with surplus ships, **When** multiple distinct targets are available, **Then** the agent can dispatch from more than one planet in the same turn to different targets.
4. **Given** the garrison floor is reduced, **When** an undetected enemy fleet arrives, **Then** the planet has sufficient garrison from the base floor (not the threat buffer) to survive production regeneration within reasonable turns.

---

### User Story 3 — Production-Weighted Lookahead Evaluation (Priority: P3)

The forward simulation's evaluation function scores production advantage only at the depth horizon. A planet captured at turn 3 of a depth-10 search scores the same as one captured at turn 9, ignoring 6 turns of production. This causes the search to systematically undervalue fast captures and overvalue slow ones, degrading decision quality.

**Why this priority**: The lookahead search is already in place (v60). Improving its eval function costs no additional compute and directly improves the quality of every beam candidate decision. Lower priority than the behavioral fixes because it requires careful tuning to avoid new forms of bias.

**Independent Test**: Run a 50-game eval vs v60. Win rate should exceed 54% (the current beam-vs-v60 parity). Additionally, measure whether the search now selects faster-capture targets more frequently (can be logged via debug output).

**Acceptance Scenarios**:

1. **Given** two beam candidates where one captures a planet at depth 3 and another at depth 9, **When** both candidates are evaluated, **Then** the depth-3 capture scores higher by at least 6 turns of that planet's production.
2. **Given** an enemy fleet arrives at the agent's planet before the search horizon, **When** the eval function scores that candidate, **Then** the score is penalized by the lost production and ships from that event.
3. **Given** the improved eval is used with depth=10, **When** compared to the horizon-only eval, **Then** the new eval scores candidates in the same relative order for unambiguous cases (regression check).
4. **Given** the depth-weighted eval is enabled, **When** the search runs within the 800ms budget, **Then** timing is not materially affected (eval cost is O(depth) not O(depth²)).

---

### Edge Cases

- What happens when all nearby neutrals are also being targeted by the opponent's fleets (both agents converging on the same planet)? The early-dispatch logic should detect contested targets via fleet angle-matching and send a sufficient fleet to win the race.
- What happens when the garrison floor reduction causes a planet to be captured because a previously undetected comet arrival drains a nearby planet? The comet evacuation path already exists and should remain unaffected by threat-based garrison changes.
- What happens when the production-weighted eval makes the search prefer very close, low-production planets over distant high-production ones too aggressively? Tune the weight so production × turns is balanced against the ROI formula used in candidate generation.
- What happens when multiple tactical improvements interact unexpectedly (e.g., lower garrison floor + early dispatch both trigger on the same planet)? Apply changes in priority order: comet evacuation first, threat defense second, early-game dispatch third, normal dispatch fourth.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In turns 0–15, the agent MUST dispatch toward the nearest capturable neutral planet if the home planet's ships exceed the neutral's projected garrison at arrival, even if the margin is thin (minimum 1 ship surplus after capture).
- **FR-002**: The early-dispatch path MUST compute garrison growth during fleet travel and size the fleet accordingly, not just use the neutral's current ship count.
- **FR-003**: The garrison buffer (`production × 2`) MUST only be applied to planets that have at least one confirmed enemy fleet within angle-match detection range heading toward them.
- **FR-004**: When no incoming threat is detected, the garrison floor MUST use only the base factor (`production × gff`) without the buffer.
- **FR-005**: The forward simulation's `score()` method MUST accumulate production gains turn-by-turn over the search depth rather than sampling only at the horizon.
- **FR-006**: The updated `score()` method MUST include a penalty for in-transit enemy fleets that will arrive at agent planets before the horizon, weighted by expected garrison damage.
- **FR-007**: All three improvements MUST be independently togglable via constants at the top of the agent file (e.g., `EARLY_DISPATCH_ENABLED`, `DYNAMIC_GARRISON_ENABLED`, `WEIGHTED_EVAL_ENABLED`) to allow isolated A/B testing.
- **FR-008**: The agent MUST remain within the 800ms per-turn time budget on Kaggle (verified locally with the same timeout constant).
- **FR-009**: The agent MUST NOT regress on path safety: zero sun-collision or out-of-bounds losses in 50-game eval.

### Key Entities

- **Garrison floor**: The minimum ships a planet retains before dispatching. Composed of base factor (`production × gff`) and optional threat buffer (`production × 2`).
- **Early-dispatch window**: Turns 0–15, where a lower effective dispatch threshold applies for neutral planet targets only.
- **Production-weighted score**: Cumulative sum of `(own_production - opp_production)` over each simulated turn, replacing single-horizon sampling.
- **Threat buffer**: Additional garrison reserved only when an enemy fleet is detected incoming to a specific planet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Average planet count at turn 20 increases from ~3.4 to ≥4.0 in self-play vs v60 (50-game sample).
- **SC-002**: Median divergence turn (the turn where planet-count ratio first reaches 2:1) increases from 8 to ≥20 in self-play vs v60.
- **SC-003**: Average dispatch rate in turns 30–50 increases from ~0.43/turn to ≥0.65/turn in self-play vs v60.
- **SC-004**: Overall win rate vs v60 exceeds 60% (50-game eval, each direction tested independently before combining).
- **SC-005**: Kaggle submission score improves beyond 916.9 (current personal best).
- **SC-006**: Zero path-safety regressions (sun collisions, out-of-bounds) in 50-game eval.
- **SC-007**: Each direction individually tested at ≥50% win rate vs v60 before combination.

## Assumptions

- The opponent-model simulator (`OPPONENT_MODEL=False`) remains disabled; the eval improvement is applied to the own-side lookahead only.
- "Turns 0–15" is the early-dispatch window; this boundary may be adjusted during implementation based on eval results.
- The 4-player Kaggle scoring context means self-play (2-player) results are directionally valid but may not perfectly predict leaderboard movement.
- The garrison floor reduction applies only when no enemy fleet angle-matches any of the agent's planets; it does not require zero enemy ships on the board.
- The production-weighted eval adds O(depth) computation per candidate per beam; at depth=10 and ~10 candidates this is negligible within the 800ms budget.
- Each direction is implemented and evaluated independently before any combination is attempted.
