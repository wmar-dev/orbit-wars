# Feature Specification: Agent Lookahead Decision Search

**Feature Branch**: `021-lookahead-search`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "I want to try to improve the agent by allowing it to make decisions by exploring possibilities many turns down the line."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Lookahead Beats Greedy Agent (Priority: P1)

The developer runs a new agent variant that simulates multiple turns ahead before committing to fleet dispatches each turn. The variant is evaluated against the current best agent (v58, Kaggle score 842.0) over a series of local games.

**Why this priority**: The greedy approach has plateaued around 842 on the Kaggle leaderboard. The only way to break this ceiling is to reason beyond the current turn — anticipating which planets will be captured by whom and coordinating fleet dispatches accordingly. This is the single highest-leverage change available.

**Independent Test**: Run the lookahead variant against v58 over 50 games using the existing `make eval` harness. A win rate ≥55% confirms the lookahead is beneficial. A regression (win rate <45%) confirms lookahead is harmful and guides tuning.

**Acceptance Scenarios**:

1. **Given** the current game state, **When** the agent selects fleet dispatches, **Then** it has evaluated the projected outcome of at least 2 distinct candidate action sets extended at least 3 turns into the future before choosing.
2. **Given** two viable options — attack a nearby neutral now vs. wait one turn and attack a higher-production neutral — **When** simulated 3+ turns ahead, **Then** the agent selects whichever option maximizes projected production advantage at the lookahead horizon.
3. **Given** the lookahead agent's turn-timer is nearly exhausted, **When** search has not completed, **Then** the agent returns the best action found so far (or falls back to the greedy decision from v58), never timing out.
4. **Given** the lookahead variant plays 50 games vs. v58, **When** win rate is measured, **Then** win rate ≥55% (or the experiment surfaces actionable insight if the hypothesis fails).

---

### User Story 2 — Lookahead Depth Sensitivity Study (Priority: P2)

The developer evaluates several lookahead depths (e.g., 1, 3, 5, 7 turns) to determine which depth yields the best trade-off between decision quality and computational overhead.

**Why this priority**: Too shallow a search adds no value over greedy; too deep a search exceeds the time budget or overfits to unreliable rollouts. Finding the sweet spot is essential before tuning further.

**Independent Test**: Run each depth variant (1/3/5/7) against v58 over 20 games each and record win rates. The depth with the highest win rate that stays within the time budget is recommended for the main submission candidate.

**Acceptance Scenarios**:

1. **Given** each depth variant is run against v58, **When** win rates are compared, **Then** at least one depth achieves ≥55% and no variant causes a timeout in any game.
2. **Given** the depth study results, **When** the best depth is identified, **Then** a combined agent is produced using that depth and evaluated for Kaggle submission.

---

### User Story 3 — Opponent Modeling Quality (Priority: P3)

The developer evaluates whether predicting the opponent's moves during simulation improves decision quality compared to ignoring the opponent (assuming all uncaptured planets remain neutral).

**Why this priority**: The accuracy of the forward model directly determines whether lookahead is trustworthy. If the opponent model is worse than no model, it should be disabled.

**Independent Test**: Run a "greedy opponent model" variant vs. a "no opponent" variant each at the best depth found in User Story 2, 20 games each. Select whichever model yields the higher win rate vs. v58.

**Acceptance Scenarios**:

1. **Given** both opponent model variants run at the same depth, **When** win rates vs. v58 are compared, **Then** the better variant is documented and used in the submission candidate.

---

### Edge Cases

- What happens when only one valid action exists (no surplus ships)? Lookahead must still return within the time budget and produce a valid (possibly no-op) action.
- What if the branching factor explodes mid-game (many owned planets, many targets)? Search must prune or sample to stay within budget.
- What if lookahead predicts a planet capture that doesn't materialize (fleet destroyed en route)? Evaluation must gracefully handle divergence between simulation and reality each turn.
- What if multiple agents in the Kaggle tournament are also using lookahead? The opponent model assumption (greedy opponent) may degrade, which is acceptable for now.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST evaluate multiple candidate action sets per turn, each extended at least 3 turns into the future before selecting the best one. At least three distinct search strategies MUST be implemented and compared: beam search (top-K greedy candidates), MCTS (random rollouts with UCB1), and N-ply exhaustive with pruning.
- **FR-002**: Each search strategy MUST operate as an anytime algorithm — searching as many candidates as the time budget allows and returning the best answer found so far when the budget expires. A valid greedy fallback (v58 behavior) MUST be used if no search result is available in time.
- **FR-003**: The lookahead search MUST include a fast forward-simulation function that advances a game state by one turn: applying production to owned planets, moving fleets one step, and resolving arrivals.
- **FR-004**: The forward simulation MUST correctly handle: orbiting planet positions (using angular velocity), fleet arrival resolution (compare ship counts, assign ownership), and sun-path filtering (no fleet dispatched through sun).
- **FR-005**: The agent MUST score each simulated terminal state using a composite metric: (own total production − opponent total production at the horizon) plus a weighted contribution from own in-transit fleets that arrive at or before the horizon. The weighting factor for in-transit ships MUST be a tunable parameter.
- **FR-006**: The lookahead depth MUST be a tunable parameter so that different depths can be evaluated without code changes.
- **FR-007**: The opponent's moves during simulation MUST be modeled using at least one strategy (e.g., the same greedy heuristic the agent uses), with the option to disable opponent modeling entirely.
- **FR-008**: The new agent MUST be evaluable using the existing `make eval` harness without modification. All three search strategies MUST be selectable via a single `SEARCH_STRATEGY` constant at the top of the agent file (e.g., `"beam"`, `"mcts"`, `"nply"`), requiring no other code changes to switch algorithms.
- **FR-009**: If lookahead produces a worse result than baseline greedy (win rate <50% vs. v58 after tuning), the experiment is still considered complete — the finding itself is the deliverable.

### Key Entities

- **GameState**: An immutable snapshot (planets, fleets, step counter) that can be cloned and advanced by the simulator without mutating live observation data.
- **ActionSet**: One candidate decision for a single turn — a list of (source_planet, target_planet, ship_count) triples representing all fleet launches that turn.
- **SearchNode**: A (GameState, ActionSet, depth) triple used to track the current position in the search tree.
- **EvaluationScore**: A scalar representing the projected production advantage at the lookahead horizon, used to rank ActionSets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one lookahead configuration achieves ≥55% win rate vs. v58 over 50 local games.
- **SC-002**: No lookahead variant causes a timeout (missing the game's per-turn action deadline) in any evaluated game.
- **SC-003**: A Kaggle submission using the best lookahead variant achieves a publicScore ≥855 (improvement over the current best of 842.0).
- **SC-004**: The depth sensitivity study produces a ranked comparison of at least 3 depths within one working session.
- **SC-005**: The forward simulation correctly predicts planet ownership at turn N+3 with ≥90% accuracy in self-play games (measured by comparing predicted vs. actual states across sampled game frames).

## Clarifications

### Session 2026-06-05

- Q: How should candidate action sets be generated each turn? → A: Multiple search strategies (beam search, MCTS, N-ply) will all be tried; the best-performing approach becomes the submission candidate.
- Q: How many candidate actions should each strategy explore per turn? → A: Budget-driven — each algorithm searches as many candidates as the time limit allows and returns the best answer found when time expires.
- Q: What should the terminal state evaluation score? → A: Production advantage plus weighted value of own in-transit ships that arrive at or before the lookahead horizon (not pure production only).
- Q: How should the three search strategies be structured for comparison? → A: Single unified agent file with a SEARCH_STRATEGY constant at the top selecting the algorithm; no separate files per strategy.

## Assumptions

- The current best agent is `agent_v58.py` with Kaggle publicScore 842.0; all local win-rate comparisons use v58 as the baseline.
- The game's per-turn action budget is approximately 1 second; lookahead must fit comfortably within this limit (target ≤0.8s to leave margin).
- A "turn" in simulation advances the step counter by 1: production is applied to owned planets, all in-transit fleets move one unit closer to their targets, and any fleets that arrive are resolved.
- The opponent model defaults to: opponent plays the same greedy ROI heuristic as v58. This may be swapped out per FR-007.
- Neutral planets do not produce ships, consistent with prior feature research (spec 018).
- Previous beam search attempts (`agent_v59_beam.py`) provide empirical reference points but do not constrain the approach taken here.
- Kaggle leaderboard score correlates imperfectly with local win rate; local win rate ≥55% is the primary acceptance gate, Kaggle score is a secondary signal.
- Mobile UI and multiplayer concerns are out of scope.
