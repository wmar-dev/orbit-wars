# Feature Specification: Agent Round 015 — Six Improvement Candidates

**Feature Branch**: `014-agent-round-015`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Orbit Wars agent improvement — Round 015. Base agent: agent_v47.py (68% vs v42, 72% vs v38). Six candidates to test as isolated experiments."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — ROI Scoring Mismatch Fix (Priority: P1)

The agent selects attack targets using an ROI formula that calculates travel time based on a fleet of `target.ships + 1`. But since v47, enemy planets require a larger fleet (`ships + production × travel + 1`), which travels faster. The ROI score for enemy targets is computed with the wrong (slower) speed, making them appear less attractive than they actually are.

**Why this priority**: Direct correctness fix that synergizes with the v47 fleet-sizing change. Enemy targets are systematically undervalued by a measurable amount; fixing this re-aligns scoring with dispatch behavior.

**Independent Test**: Run 50 games vs agent_v47 with only this change. A passing result (≥56% win rate) validates that correctly scoring enemy targets changes which targets get prioritised, leading to better captures.

**Acceptance Scenarios**:

1. **Given** an enemy planet target, **When** the agent scores its ROI, **Then** the travel time used in the formula reflects the speed of the actual fleet that would be dispatched (sized for arrival-time garrison), not the naive `ships + 1` fleet.
2. **Given** a neutral planet and an enemy planet at equal distance with equal production, **When** the agent chooses between them, **Then** the enemy planet's ROI correctly accounts for the larger (faster) fleet required to capture it.
3. **Given** an enemy planet whose production-adjusted ships_needed is significantly larger than `target.ships + 1`, **When** comparing against a neutral of similar value, **Then** the enemy planet is not systematically penalised by an artificially long travel-time estimate.

---

### User Story 2 — Endgame ROI Normalization (Priority: P1)

The ROI formula uses a hard-coded 100-turn horizon (`100.0 - travel`). In the final 100 turns of a 500-turn game, a high-production planet 40 travel-turns away has only ~60 turns of production remaining — but the formula behaves as if there are 100. This causes the agent to over-invest in distant captures that deliver little value before time runs out.

**Why this priority**: Low-risk, one-value change with clear directional reasoning. Late-game behaviour is known to be a significant factor in final ship count.

**Independent Test**: Run 50 games vs agent_v47 with only this change. Evaluate both win rate and average final ship count margin to confirm the agent makes more efficient late-game decisions.

**Acceptance Scenarios**:

1. **Given** the game is at step 400 (100 turns remaining), **When** the agent scores a target 50 travel-turns away, **Then** the time-decay term uses `remaining_turns - travel = 50` rather than `100 - travel = 50` (coincidentally same here — the key difference is at step 450 or beyond).
2. **Given** the game is at step 450 (50 turns remaining), **When** scoring a planet 30 travel-turns away, **Then** the time-decay term is `max(1.0, 20)` rather than `max(1.0, 70)`, significantly reducing its ROI relative to closer targets.
3. **Given** two targets — one 5 turns away, one 40 turns away — at step 460, **When** the agent selects a target, **Then** it strongly prefers the nearby target because the distant one yields almost no production before game end.

---

### User Story 3 — Garrison Defense Buffer (Priority: P2)

When an enemy fleet of N ships is inbound, the agent keeps exactly N ships on the threatened planet. If the enemy fleet arrives with exactly N ships, the planet survives capture but at 0 garrison — completely undefended for the following turns. The defense floor should be slightly above the inbound threat to maintain post-battle viability.

**Why this priority**: Fixes an edge case where perfect-defence logic leaves a planet in a critically vulnerable state. Low risk, small change.

**Independent Test**: Run 50 games vs agent_v47 with only this change. Track whether threatened planets are recaptured the turn after surviving an attack (a diagnostic win).

**Acceptance Scenarios**:

1. **Given** an owned planet with 30 ships and an incoming enemy fleet of 30 ships, **When** the garrison floor is computed, **Then** it is set to `30 + planet.production × 2` (or similar buffer), not just 30.
2. **Given** no incoming threat to a planet, **When** the garrison floor is computed, **Then** it falls back to the standard `production × GARRISON_FLOOR_FACTOR` (no change from current behaviour).
3. **Given** a planet with production 3 and an incoming fleet of 20 ships, **When** a buffer of `production × 2 = 6` is applied, **Then** the floor is 26 so the planet retains at least 6 ships after the battle rather than 0.

---

### User Story 4 — Sender Pre-Screening for Enemy Targets (Priority: P2)

When assigning the best sender to each target, the agent picks the planet with the best `distance / surplus` ratio. For enemy targets, the actual ships needed (production-adjusted) may exceed the chosen sender's total garrison, causing the attack to be silently dropped later. No fallback sender gets a chance. This wastes offensive opportunities.

**Why this priority**: Fixes a silent attack-dropping bug specific to enemy targets introduced by the v47 fleet-sizing change. Restores offensive pressure that was previously being lost.

**Independent Test**: Run 50 games vs agent_v47 with only this change. Expect more successful enemy captures per game.

**Acceptance Scenarios**:

1. **Given** an enemy target requiring 60 ships to capture and a sender with only 45 ships (best `dist/surplus`), **When** sender assignment runs, **Then** that sender is excluded and the next-best sender with ≥60 ships is selected instead.
2. **Given** no sender has enough ships to cover the production-adjusted garrison, **When** sender assignment runs, **Then** no sender is assigned (attack deferred), same as current behaviour.
3. **Given** a neutral target requiring only `target.ships + 1` ships, **When** sender assignment runs, **Then** the pre-screening uses the lighter neutral estimate (no change in behaviour for neutrals).

---

### User Story 5 — Committed Ships Accounting (Priority: P3)

The agent dispatches ships each turn based on the current garrison. It does not account for ships already in transit (own fleets launched in prior turns). A planet may send 40 ships to target A on turn T, then on turn T+1 the garrison has grown slightly but the agent still treats the planet as having its full next-turn garrison available and sends to target B — potentially under-defending or double-committing.

**Why this priority**: Addresses over-commitment, but the effect is indirect and may interact poorly with dynamic garrison floor. Lower priority; test after higher-priority candidates pass.

**Independent Test**: Run 50 games vs agent_v47 with only this change. Monitor for cases where planets are left under-defended due to sequential dispatches.

**Acceptance Scenarios**:

1. **Given** an owned planet with 80 ships that launched a fleet of 50 ships last turn (still in transit), **When** the agent computes surplus for sender assignment this turn, **Then** those 50 in-transit ships are subtracted from available surplus.
2. **Given** an owned planet with no fleets in transit, **When** surplus is computed, **Then** the result is identical to current behaviour (no regression for the common case).
3. **Given** multiple friendly fleets in transit from the same planet, **When** surplus is computed, **Then** all in-transit ships from that planet are summed and deducted.

---

### User Story 6 — Persistent Campaign Target (Priority: P3)

Each turn the agent re-scores all targets from scratch. For any owned planet, the assigned target may change turn-to-turn as ship counts and positions shift. This causes flip-flopping: a planet sends 30 ships to A this turn, 30 to B next turn, then back to A — none of the fleets are large enough to capture. A campaign target persists until the target is captured, a friendly fleet already covers it, or a significantly better option emerges (ROI improves by >30%).

**Why this priority**: Addresses a behavioural pathology but adds statefulness, which increases complexity and risk. Test after simpler fixes are confirmed.

**Independent Test**: Run 50 games vs agent_v47 with only this change. Measure whether fewer partial-fleet captures occur (fleets that deal damage without capturing).

**Acceptance Scenarios**:

1. **Given** an owned planet assigned to enemy target A, **When** the next turn the ROI of target A drops by 15%, **Then** the planet continues targeting A (within the 30% stability threshold).
2. **Given** an owned planet assigned to enemy target A, **When** target A is captured by another player mid-flight, **Then** the campaign is cleared and the planet re-evaluates targets next turn.
3. **Given** an owned planet assigned to target A, **When** a friendly fleet already in transit to A would cover the remaining garrison, **Then** the campaign is cleared (no redundant follow-up dispatch).
4. **Given** an owned planet assigned to target A, **When** a new target B has ROI more than 30% higher than A, **Then** the campaign switches to B.

---

### Edge Cases

- What happens when `remaining_turns - travel` is zero or negative in the endgame ROI formula? → Clamp to `max(1.0, ...)`.
- What if all senders are pre-screened out for an enemy target (none can cover)? → No sender assigned; attack deferred (same as current skip behaviour).
- What if in-transit ships are counted and garrison goes negative? → Guard with `max(0, surplus)` as currently done.
- What if a campaign target switches owner from enemy to neutral mid-flight (another player's fleet captures it first)? → Campaign cleared; re-evaluate.
- What if `step` is 0 (very first turn) and `remaining_turns = 500`? → ROI formula behaves identically to the current hardcoded 100.0 baseline (500 - travel >> 100 so the cap at `max(1.0, ...)` is never hit at normal distances).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ROI scoring function MUST use the actual dispatched fleet size (production-adjusted for enemy targets) when computing travel time, not the naive `target.ships + 1` estimate.
- **FR-002**: The ROI time-decay term MUST use `max(1.0, remaining_turns - travel)` where `remaining_turns = 500 - step`, replacing the hardcoded `100.0`.
- **FR-003**: The garrison threat floor MUST include a buffer above the raw inbound ship count: `threat[p.id] + p.production × 2` (or equivalent), not just `threat[p.id]`.
- **FR-004**: The sender assignment loop MUST pre-screen senders for enemy targets using a rough `ships_needed` estimate, excluding senders whose total garrison is insufficient to cover the production-adjusted fleet size.
- **FR-005**: Surplus computation in sender assignment MUST subtract ships already in transit from owned planets (from `raw_fleets` where `f_owner == player`), to avoid over-committing garrisons across turns.
- **FR-006**: Each owned planet MUST maintain a persistent campaign target across turns, updated only when: the target is captured, an in-transit friendly fleet already covers it, or a superior target (ROI >30% higher) appears.
- **FR-007**: Each candidate MUST be implemented as a standalone agent file (agent_v48 through agent_v53) and evaluated independently vs agent_v47 over 50 games before any combination step.
- **FR-008**: Passing candidates (≥56% win rate vs agent_v47) MUST be combined into a single agent and re-evaluated vs agent_v47 and the strongest individual candidate.

### Key Entities

- **Agent**: A Python function `agent(obs)` returning a list of moves `[planet_id, angle, ships]`.
- **ROI formula**: `(production² × time_decay) / arrival_garrison` — the core target-scoring expression.
- **Sender assignment**: The loop that selects one optimal source planet per target each turn.
- **Garrison floor**: The minimum ships an owned planet retains before launching a fleet.
- **Campaign target**: A per-planet persistent record of the current attack objective.
- **In-transit committed ships**: Ships owned by the player currently in flight (not yet arrived).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each individual candidate achieves ≥56% win rate vs agent_v47 over 50 games to be considered passing.
- **SC-002**: The combined agent (passing candidates only) achieves ≥60% win rate vs agent_v47 over 50 games.
- **SC-003**: The combined agent achieves ≥72% win rate vs agent_v38 (historic baseline), matching or exceeding the v47 benchmark.
- **SC-004**: Zero sun-collision or out-of-bounds fleet losses occur in any of the 50-game evaluation runs (path safety must not regress).
- **SC-005**: The combined agent achieves ≥50% score in symmetric self-play (agent vs itself), confirming no dominant self-losing strategy is introduced.

## Assumptions

- Each candidate is tested in strict isolation: only one mechanic changes at a time relative to agent_v47.
- The `raw_fleets` observation field accurately reflects all fleets in transit at the time of each turn (used for committed-ships accounting and campaign-target clearing).
- The 30% ROI threshold for campaign switching (FR-006) is a starting point; it may need tuning if the candidate passes but margin is thin.
- Remaining turns formula assumes a fixed 500-turn game (episodeSteps default). No configuration override is in scope.
- The garrison buffer multiplier of `production × 2` for FR-003 is a starting point; a single-round test will determine if a larger or smaller buffer is appropriate.
- Combinations are only attempted after all individual evaluations complete; no partially-evaluated candidates are combined.
