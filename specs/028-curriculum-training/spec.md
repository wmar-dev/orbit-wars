# Feature Specification: Curriculum Training with Terminal Reward

**Feature Branch**: `028-curriculum-training`

**Created**: 2026-06-07

**Status**: Draft

**Input**: User description: "Implement curriculum training and terminal-only reward to fix PPO convergence failure in round 7"

## User Scenarios & Testing

### User Story 1 — Train policy from scratch with curriculum (Priority: P1)

As a developer, I want to train an RL policy starting against random opponents and only progressing to stronger ones (v38, v64) after reaching defined win-rate thresholds, so that the policy experiences winning states and can learn a useful gradient.

**Why this priority**: Without curriculum, the policy never sees winning states and PPO has no positive examples to reinforce. This is the root cause of 0% convergence across two rounds.

**Independent Test**: Run 200 episodes vs random with a freshly initialized policy. Policy should achieve >50% win rate by episode 200, up from ~22% in round 7.

**Acceptance Scenarios**:

1. **Given** a freshly initialized policy, **When** trained for 500 episodes vs random with terminal-only reward, **Then** win rate vs random exceeds 60%.
2. **Given** a policy that has reached 80% win rate vs random, **When** trained for 500 episodes vs v38, **Then** win rate vs v38 exceeds 30% (up from 0% in round 7).
3. **Given** a policy trained through the full curriculum (random → v38 → v64), **When** evaluated for 100 games vs v64, **Then** win rate exceeds 5% (up from 0% in round 7).

---

### User Story 2 — Evaluate policy at each curriculum stage (Priority: P2)

As a developer, I want automatic win-rate evaluation at each curriculum checkpoint (every 200 episodes) so that I can track progress and know when to advance to the next opponent tier.

**Why this priority**: Curriculum advancement requires measurable win-rate gates. Without automated evaluation, the developer must manually run eval games.

**Independent Test**: Run training with `--eval-frequency 200`. After 200 episodes, an eval log entry appears showing win rate for the current opponent.

**Acceptance Scenarios**:

1. **Given** training is running with `--eval-frequency 200`, **When** episode count reaches a multiple of 200, **Then** 50 eval games are played against the current opponent and the win rate is logged.
2. **Given** the policy's win rate exceeds 80% against the current opponent, **When** the evaluation completes, **Then** the curriculum automatically advances to the next opponent tier.

---

### User Story 3 — Sparser action space with greedy fallback (Priority: P3)

As a developer, I want the policy to fall back to a heuristic (nearest-enemy-sniper) when all 5 fleet slots produce invalid moves, so that idle turns are eliminated and the policy collects more meaningful experience.

**Why this priority**: Round 7 showed 46% idle turns where the policy produced 0 valid moves. This wastes training time and starves PPO of experience.

**Independent Test**: Run 100 episodes vs random. Log shows <5% of turns with 0 dispatches, down from 46%.

**Acceptance Scenarios**:

1. **Given** a turn where all 5 policy-sampled fleet actions are invalid, **When** `decode_action` is called, **Then** a fallback heuristic produces at least 1 valid fleet dispatch.
2. **Given** any turn with valid policy actions, **When** `decode_action` is called, **Then** policy actions take priority and fallback is not triggered.

---

### Edge Cases

- What happens when no planet has surplus ships? Fallback should send 0 ships (only compute fleet is empty to avoid crashes).
- How does the system handle the first episode when no eval stats exist? Eval starts at episode 200, first eval is clean.
- What if curriculum advancement happens mid-rollout? Opponent change takes effect after the current rollout buffer completes.

## Requirements

### Functional Requirements

- **FR-001**: Reward function MUST use only terminal win/loss signal (+1.0 win, -1.0 loss, 0.0 draw). No per-turn blended reward.
- **FR-002**: Training MUST support curriculum stages with configurable opponents and win-rate thresholds.
- **FR-003**: Curriculum MUST advance to next opponent when win rate exceeds configurable threshold (default 80%) over the last N eval games (default 100).
- **FR-004**: Curriculum MUST NOT downgrade to weaker opponents (monotonic progression).
- **FR-005**: System MUST log win rate at configurable eval frequency (default every 200 episodes).
- **FR-006**: Eval MUST play at least 50 games per checkpoint for statistically meaningful win-rate estimates.
- **FR-007**: `decode_action` MUST produce at least 1 valid fleet dispatch per turn using a greedy fallback when all policy-sampled actions are invalid.
- **FR-008**: Fallback MUST use nearest-enemy-sniper strategy: find own planet with most surplus, send to nearest non-owned planet with angle, ships=surplus.
- **FR-009**: Action space (5 independent fleet slots × [source, target, fraction]) and observation (560-dim, 40 planets, 8+42 fleet encoding) from round 7 MUST be preserved unchanged.

### Key Entities

- **Curriculum Stage**: Defined by (opponent_agent_path, win_threshold, min_episodes). Stages: [("random", 0.8, 500), ("agent_v38.py", 0.6, 1000), ("agent_v64.py", 0.0, 5000)].
- **Eval Result**: (episode, opponent, games_played, wins, win_rate).
- **Fallback Action**: (source_planet_id, angle, num_ships) — computed greedily from observation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Idle-turn rate drops from 46% (round 7) to <5% after greedy fallback.
- **SC-002**: Win rate vs random exceeds 60% by episode 500 (up from 22% in round 7).
- **SC-003**: Win rate vs v64 exceeds 5% after curriculum progression (up from 0% in round 7).
- **SC-004**: Training completes 5000 total episodes in under 3 hours on Apple Silicon (up from ~24 ep/min in round 7, target ~28 ep/min).

## Assumptions

- Round 7's observation encoder (560-dim, 40 planets, 8+42 fleet) and action space (5 independent fleet slots) are correct and will be reused without modification.
- Agent v38.py exists in the repository as an intermediate-strength opponent.
- Terminal-only reward (+1/-1/0) provides a cleaner gradient than the blended reward.
- Nearest-enemy-sniper is an effective enough fallback to eliminate idle turns. It does not need to be optimal.
- The PPO hyperparameters from round 7 (LR 3e-4, hidden 256, etc.) remain suitable for the new reward and curriculum setup.
