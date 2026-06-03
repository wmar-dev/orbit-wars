# Feature Specification: Agent Strategic Improvements — MCTS, Fleet Coordination, Defense

**Feature Branch**: `019-agent-mcts-coordination-defense`

**Created**: 2026-06-02

**Status**: Draft

**Input**: Three strategic improvements to push the agent from ~850 to ~1000 publicScore on Kaggle Orbit Wars leaderboard.

## Background

Current best agent (v58) scores ~828–853 on the Kaggle leaderboard using pure greedy heuristics. The ceiling for single-ply greedy play appears to be ~850–900. Three targeted improvements are specified here, ordered by implementation priority and expected impact:

1. **MCTS / Beam Search** — lookahead search to reason about future game states
2. **Global Fleet Coordination** — eliminate redundant multi-mine dispatches to the same target
3. **Defensive Reinforcement** — respond to detected incoming enemy fleets

## User Scenarios & Testing *(mandatory)*

### User Story 1 — MCTS Lookahead (Priority: P1)

The developer runs a new agent variant that simulates several turns ahead before deciding which fleets to dispatch, and evaluates whether it beats v58 in local self-play.

**Why this priority**: Lookahead search is the single change most likely to break the 850 ceiling. It allows coordinated multi-planet attacks, loss anticipation, and fleet timing that are impossible with 1-ply greedy play. The top leaderboard agents almost certainly use this.

**Independent Test**: Pit the MCTS variant against v58 across 50+ games. Expect win rate ≥55%.

**Acceptance Scenarios**:

1. **Given** a game start, **When** the agent selects fleet dispatches, **Then** it evaluates at least 3 candidate action sets (combinations of fleet launches) and picks the one projecting the highest production advantage after N simulated turns.
2. **Given** two options — capture a low-growth neutral now vs. reinforce a threatened high-growth planet — **When** evaluated through lookahead, **Then** the agent chooses reinforcement when the planet loss would materially hurt projected production.
3. **Given** the MCTS variant runs on a 1-second timeout, **When** evaluated over 50 games, **Then** it never times out (all moves returned within budget).
4. **Given** the MCTS variant plays 50 games vs. v58, **When** win rate is measured, **Then** win rate ≥55%.

---

### User Story 2 — Global Fleet Coordination (Priority: P2)

The developer runs a new agent variant that assigns each target to exactly one source planet, eliminating redundant dispatches, and evaluates whether it beats v58 in local self-play.

**Why this priority**: Currently each mine independently picks its best target, so two mines can dispatch to the same planet, wasting ships. A global assignment prevents this and frees ships for additional captures.

**Independent Test**: Run 50 games vs. v58; expect ≥53% win rate. Also verify: across 10 games, average "redundant fleet pairs" (two owned fleets heading to the same neutral) drops to near zero.

**Acceptance Scenarios**:

1. **Given** two owned planets that both select the same neutral as best target, **When** the global assignment runs, **Then** only one dispatches to that neutral and the other redirects to the next best uncovered target.
2. **Given** a neutral planet already targeted by an in-transit own fleet with sufficient ships, **When** the assignment runs, **Then** no additional fleet is sent to that planet.
3. **Given** the coordination variant plays 50 games vs. v58, **When** win rate is measured, **Then** win rate ≥53%.

---

### User Story 3 — Defensive Reinforcement (Priority: P2)

The developer runs a new agent variant that detects incoming enemy fleets and reinforces threatened planets when economically justified, and evaluates whether it beats v58 in local self-play.

**Why this priority**: The current agent only attacks. When an enemy fleet is detected heading toward a valuable owned planet, sending reinforcement is almost always better than ignoring the threat and losing the planet plus its production.

**Independent Test**: Run 50 games vs. v58; expect ≥53% win rate. Also verify: across 10 games, fraction of "losable high-production planets" that receive timely reinforcement increases vs. v58.

**Acceptance Scenarios**:

1. **Given** an enemy fleet detected at angle matching an owned planet with high production (≥3), **When** a friendly planet has surplus ships and can arrive before or with the enemy fleet, **Then** a reinforcement fleet is dispatched.
2. **Given** a threat detected on a low-production planet (production < 2) where reinforcement cost exceeds expected production recovered, **When** the agent evaluates defense, **Then** it does not dispatch reinforcement (abandons the planet).
3. **Given** the defense variant plays 50 games vs. v58, **When** win rate is measured, **Then** win rate ≥53%.

---

### Edge Cases

- MCTS: what if the lookahead time budget is exceeded mid-search? Must fall back to greedy (v58 behavior) rather than returning no move.
- Fleet coordination: what if all targets are already covered by in-transit friendly fleets? Agent should hold ships rather than dispatching redundantly.
- Defense: what if reinforcing one planet leaves another planet vulnerable to a second enemy fleet? Prioritization must account for multiple simultaneous threats.
- Combined variant: when all three improvements are active, do they interact adversely (e.g., MCTS already handles defense implicitly)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCTS variant MUST evaluate multiple candidate action combinations per turn and select the one with the highest projected production advantage after N simulated turns (N ≥ 3).
- **FR-002**: The MCTS variant MUST complete all fleet decisions within the 1-second action timeout, falling back to greedy selection if search time is exhausted.
- **FR-003**: The fleet coordination variant MUST assign each non-owned target to at most one source planet per turn using a global assignment step.
- **FR-004**: The fleet coordination variant MUST skip targets already sufficiently covered by in-transit own fleets (own fleet ships in transit ≥ target garrison + 1).
- **FR-005**: The defense variant MUST detect enemy fleets heading toward owned planets by comparing fleet direction angles to owned planet positions.
- **FR-006**: The defense variant MUST dispatch reinforcement only when: (a) a friendly planet can arrive before the enemy, AND (b) the defended planet's production value justifies the ship cost.
- **FR-007**: Each improvement MUST be implemented as a standalone agent variant file evaluable with the existing eval harness.
- **FR-008**: A combined variant incorporating all three improvements MUST be produced and evaluated against v58.
- **FR-009**: All variants MUST be self-contained (no local imports outside stdlib and `kaggle_environments`).

### Key Entities

- **GameState**: A snapshot of planets, fleets, and step used by the MCTS simulator to project future states without modifying live observations.
- **ActionSet**: A combination of fleet launches for one turn, representing one branch in the search tree.
- **ThreatMap**: Per-planet incoming enemy ship count and estimated arrival step, derived from fleet observations.
- **TargetAssignment**: A mapping from target planet ID → source planet ID, computed globally each turn for fleet coordination.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one variant achieves ≥55% win rate vs. v58 over 50 games in local self-play.
- **SC-002**: The combined variant achieves a Kaggle publicScore ≥900 after submission (estimated from local win rate correlation).
- **SC-003**: No variant causes a timeout (missing the 1-second actTimeout) in any evaluated game.
- **SC-004**: Fleet coordination variant reduces average redundant fleet dispatches to <0.5 per game (measured across 10 games).
- **SC-005**: All variants complete evaluation (50 games) in under 15 minutes using 4 parallel workers.

## Assumptions

- The current best agent is v58 (58% vs. v57) and serves as the baseline for all local comparisons.
- The game's 1-second actTimeout is enforced; any approach that cannot return moves within budget must gracefully degrade to greedy.
- Enemy fleet direction can be reliably inferred from the `angle` field in the fleet observation tuple.
- Neutral planets are static garrisons (confirmed in feature 018); fleet sizing `ships + 1` remains correct.
- A "simulated turn" advances owned planet ship counts by their production rate and moves in-transit fleets one step — no opponent model is needed for the MCTS rollout phase (assume opponent plays greedily).
- The combined variant (all three improvements) is the submission candidate; individual variants are diagnostics.
- Mobile/UI concerns are out of scope.
