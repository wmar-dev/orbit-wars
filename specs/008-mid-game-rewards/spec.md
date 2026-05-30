# Feature Specification: Mid-Game Reward Signals and Reward-Guided Agent Experimentation

**Feature Branch**: `008-mid-game-rewards`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Get ready to incorporate more RL by adding rewards that we can identify mid game. Add experimentation of agents utilizing mid game rewards to see if we can improve the agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect reward signals during replay (Priority: P1)

A researcher runs a completed game through the reward-signal module and receives a time-series of scalar reward values — one per game turn — covering events like planet captures, ship count changes, and production-rate shifts.

**Why this priority**: Without observable per-turn rewards, no RL training loop can be constructed. This is the foundational deliverable.

**Independent Test**: Feed a recorded game log (any seed) into the reward module; verify a numeric reward value is emitted for every turn and that the aggregate over a won game is positive.

**Acceptance Scenarios**:

1. **Given** a completed 2-player game log, **When** the reward module processes it turn by turn, **Then** it returns one scalar reward per turn for each player.
2. **Given** a game where player 0 captures a neutral planet on turn 5, **When** rewards are computed, **Then** player 0's reward for turn 5 is strictly greater than the baseline (zero-event) reward.
3. **Given** a game that player 0 wins, **When** rewards are summed across all turns, **Then** player 0's cumulative reward is positive and greater than player 1's.

---

### User Story 2 - Validate reward shaping incentivizes good play (Priority: P2)

A researcher compares the reward time-series of a high-performing agent (agent_v30) against a weaker agent across the same seeds and confirms that good moves consistently score higher mid-game rewards.

**Why this priority**: Reward signals that don't correlate with winning are useless for RL. Validation against known-good agents ensures the signals are well-shaped before any training begins.

**Independent Test**: Run eval.py with reward logging enabled on agent_v30 vs. agent_v3; confirm agent_v30 has higher average per-turn reward on seeds it wins.

**Acceptance Scenarios**:

1. **Given** agent_v30 vs. agent_v3 across 50 seeds, **When** per-turn rewards are compared, **Then** the winning agent has higher average mid-game reward in at least 75% of games.
2. **Given** a game where a player loses all planets by turn 20, **When** rewards are computed, **Then** that player's reward is negative from the turn the last planet is lost onward.

---

### User Story 3 - Plug reward module into eval harness (Priority: P3)

A researcher runs the existing `eval.py` (or `eval4.py`) with a `--reward-log` flag and receives a JSON Lines file of per-turn, per-player rewards alongside the existing win/loss output, without altering the evaluation logic itself.

**Why this priority**: Logging rewards through the existing harness enables dataset collection for offline RL without requiring a separate workflow.

**Independent Test**: Run `eval.py --reward-log rewards.jsonl --games 5`; verify the output file exists, has one JSON object per (turn, player) per game, and win/loss results are unchanged.

**Acceptance Scenarios**:

1. **Given** `eval.py` invoked with `--reward-log <path>`, **When** evaluation completes, **Then** the log file is written and contains turn-level reward data for every game.
2. **Given** `eval.py` invoked without `--reward-log`, **When** evaluation completes, **Then** no reward file is written and existing output is identical to current behavior.

---

### User Story 4 - Build a reward-guided agent variant (Priority: P4)

A researcher creates a new agent that incorporates the reward signal into its move-selection logic — using per-turn reward estimates to score candidate actions alongside the existing ROI heuristic — then evaluates it against agent_v30 to measure improvement.

**Why this priority**: The reward module's value is validated only when it demonstrably influences agent behavior and win rate. This closes the loop from signal to strategy.

**Independent Test**: Run `eval.py --agent0 agent_v31.py --agent1 agent_v30.py --games 50`; verify agent_v31 achieves at least 55% win rate (the threshold established for prior accepted mechanics).

**Acceptance Scenarios**:

1. **Given** a new agent that blends reward-signal scoring with ROI scoring, **When** evaluated against agent_v30 over 50 games, **Then** the new agent achieves a win rate ≥ 55%.
2. **Given** a new agent configured with reward weights set to zero, **When** evaluated, **Then** its behavior is identical to the baseline heuristic (reward integration is purely additive).
3. **Given** multiple reward-weight configurations run against agent_v30, **When** results are compared, **Then** at least one configuration beats the 55% threshold.

---

### User Story 5 - Identify reward-optimal behaviors from replay analysis (Priority: P5)

A researcher loads the reward log from agent_v30 vs. agent_v3 games and identifies which game states and turn ranges yield the highest mid-game reward deltas, then uses those insights to motivate new agent mechanics.

**Why this priority**: Systematic replay analysis converts raw reward data into actionable hypotheses for new mechanics — turning reward logging into a research tool, not just a training artifact.

**Independent Test**: Load a 50-game reward log and produce a summary showing average reward by turn bucket (early/mid/late game) and by event type (capture, production gain, ship gain); verify the summary is human-readable and identifies at least one high-reward pattern.

**Acceptance Scenarios**:

1. **Given** a reward log from 50 games, **When** a summary analysis is run, **Then** it outputs average per-turn reward broken down by component and game phase.
2. **Given** the summary, **When** agent_v30 wins a game, **Then** its highest reward turns are identifiable and correspond to game events (e.g., a multi-planet capture sequence).

---

### Edge Cases

- What happens when a game ends before the max turn limit (one player eliminated)? Reward computation must terminate cleanly and assign a large terminal bonus/penalty.
- How does the reward module handle a draw (equal final scores)? Tied players share the same rank and receive the same rank-based terminal reward; no arbitrary tie-breaking is applied.
- What if the game log is malformed or missing state fields? The module MUST raise a descriptive Python exception and halt processing for that game; silent zero emission is explicitly forbidden to prevent corrupting training data.
- 4-player games: rewards must be computed per-player without assuming exactly 2 players.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a reward-signal module that accepts a game-state observation and returns a scalar reward value for a specified player.
- **FR-002**: The module MUST emit one reward per turn, computed solely from the observable game state (no lookahead).
- **FR-003**: Reward components MUST include at minimum: planet-capture events, change in owned production capacity, change in total owned ship count (ships on planets plus ships currently in flight), and terminal win/loss bonus.
- **FR-004**: Each reward component MUST have an independently configurable weight so researchers can experiment with reward shaping.
- **FR-005**: All reward outputs MUST be normalized to the range [-1, 1]. The terminal reward MUST be rank-based and evenly spaced: in an N-player game, rank k receives terminal reward of `1 - 2*(k-1)/(N-1)`, giving +1 for 1st and -1 for last. In 2-player games this reduces to exactly +1 (win) and -1 (loss). All per-turn component signals MUST be scaled as fractions of that range so that the terminal signal dominates.
- **FR-006**: The module MUST support both 2-player and 4-player game formats, adapting per-player reward computation accordingly.
- **FR-007**: The eval harness (`eval.py` and `eval4.py`) MUST accept an optional `--reward-log <path>` argument that writes per-turn, per-player rewards to a JSON Lines file (`.jsonl`, one JSON object per turn per player) without altering existing win/loss output.
- **FR-008**: The reward module MUST be importable as a standalone Python module with no dependency on the eval harness.
- **FR-009**: Reward weights MUST be definable in a single configuration location (a constants block or config dict) so all values can be reviewed and tuned in one place.
- **FR-010**: The system MUST provide at least one new agent variant that incorporates per-turn reward estimates into its action-scoring logic alongside the existing ROI heuristic, with a configurable blend factor controlling the relative influence of reward vs. ROI.
- **FR-011**: The reward-guided agent MUST degrade gracefully to pure-heuristic behavior when its reward blend factor is set to zero, producing output identical to the unmodified baseline agent.
- **FR-012**: The system MUST provide a replay-analysis script that reads a `.jsonl` reward log and produces a human-readable summary of average reward by component and by game phase (early: turns 1–20, mid: turns 21–60, late: turns 61+).
- **FR-013**: Reward-weight configuration experiments MUST be tracked in the `experiments/` directory using the same format established in prior rounds, recording the weight configuration, win rate vs. agent_v30, and number of games evaluated.

### Key Entities

- **RewardSignal**: Per-turn scalar reward for one player; includes breakdown by component (capture bonus, production delta, ship delta, terminal).
- **RewardConfig**: Named weights for each reward component; acts as the primary tuning surface for reward shaping.
- **GameStateSnapshot**: The observable state at a single turn (planets, ships in flight, player statuses) — already provided by the kaggle_environments API.
- **RewardLog**: Structured record of all per-turn RewardSignals across a multi-game evaluation run, written to disk as JSON Lines (`.jsonl`), one object per (game, turn, player).
- **RewardGuidedAgent**: An agent variant that blends reward-signal estimates with the existing ROI heuristic via a configurable blend factor; tracked as a new `agent_vN.py` file.
- **ExperimentRecord**: A file in `experiments/` capturing the reward-weight configuration, blend factor, win rate vs. agent_v30, and game count for a single experimental run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The reward module emits exactly one scalar in [-1, 1] per (turn, player) pair for 100% of turns in any valid game log.
- **SC-002**: In a corpus of 50 games, the winning player's cumulative reward exceeds the losing player's in at least 80% of games.
- **SC-003**: Adding `--reward-log` to an existing eval run increases wall-clock time by less than 10% (reward computation is not a bottleneck).
- **SC-004**: All reward weights are tunable from a single configuration block with no code changes required elsewhere.
- **SC-005**: The module handles 4-player games without errors and produces per-player rewards for all four players.
- **SC-006**: At least one reward-guided agent variant achieves ≥ 55% win rate vs. agent_v30 over 50 games (the accepted-mechanic threshold used in prior rounds).
- **SC-007**: Setting the reward blend factor to zero produces win rate statistically indistinguishable from the unmodified baseline agent (within ±5% over 50 games).
- **SC-008**: The replay-analysis summary script runs in under 5 seconds on a 50-game reward log.

## Clarifications

### Session 2026-05-30

- Q: What format should the reward log file use? → A: JSON Lines (`.jsonl`), one JSON object per (game, turn, player), supporting nested per-component breakdown.
- Q: Should reward output be normalized? → A: Normalize to [-1, 1]; terminal signal = ±1, per-turn components scaled as fractions of that range.
- Q: Which ships count toward "owned ship count" in the reward signal? → A: All ships — both ships on planets and ships currently in flight (en route to a target).
- Q: How should the module handle malformed game state? → A: Raise a descriptive Python exception and halt processing for that game; do not emit silent zeros.
- Q: How should the terminal reward handle multi-player ranking? → A: Rank-based, evenly spaced from +1 (1st place) to -1 (last place); 2-player win/loss remains exactly ±1.

## Assumptions

- The kaggle_environments `orbit_wars` game state is fully observable per turn; no partial-observability handling is needed.
- The primary consumer of reward signals is offline dataset collection, replay analysis, and reward-guided agent scoring. A full online RL training loop (policy gradients, neural networks) is out of scope for this feature.
- Existing agent files (`agent_v*.py`) are not modified — the reward module is additive.
- The reward module is written in Python, consistent with the rest of the codebase.
- 2-player evaluation is the primary target; 4-player support is required but secondary.
- No external ML libraries are introduced in this feature; the reward module is pure Python math.
