# Feature Specification: RL-Optimized Agent

**Feature Branch**: `011-rl-optimize-agent`

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Use RL to optimize agent"

## Background & Context

The current best agent (**agent_v38**) is a heuristic rule-based system. All mechanics have been hand-crafted and tuned through successive experiment rounds. The top leaderboard agents (scores 1400–1724) are substantially ahead of agent_v30's Kaggle score of 763.2, suggesting that hand-crafted heuristics have approached a local optimum. Reinforcement learning offers a path to discover non-obvious strategies and parameter weightings that outperform human-designed rules.

The project constitution names RL as the primary long-term optimization path. This feature implements that path: train an RL agent using self-play, evaluate it against agent_v38, and submit the best result to the Kaggle leaderboard.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Train an RL Agent via Self-Play (Priority: P1)

A researcher sets up a training loop that runs games between two versions of the agent (or against prior fixed agents), uses game outcomes to update a policy, and saves checkpoints at regular intervals.

**Why this priority**: Training is the core deliverable — without it, no RL agent exists to evaluate.

**Independent Test**: A training run can be launched with a single command, produces checkpoint files at regular intervals, and logs reward/score progression over episodes. A 100-episode smoke test should complete without crashing and show non-trivial reward signal.

**Acceptance Scenarios**:

1. **Given** the Kaggle Orbit Wars environment, **When** the training loop runs, **Then** episode rewards are logged and checkpoint files are saved at configurable intervals.
2. **Given** a training run in progress, **When** a checkpoint is loaded, **Then** the agent can be evaluated in `eval.py` against any fixed agent without modification.
3. **Given** a crashed or interrupted training run, **When** the training command is re-run, **Then** training resumes from the most recent checkpoint rather than starting over.

---

### User Story 2 — Evaluate RL Agent Against agent_v38 (Priority: P1)

The trained RL agent is evaluated head-to-head against agent_v38 over 50 games using the existing `eval.py` harness. Results are recorded in an experiment file following the established format.

**Why this priority**: Without a head-to-head result against the current best, the RL agent cannot be promoted or submitted.

**Independent Test**: The RL agent can be passed as `--agent0` to `eval.py` and produces a score. The experiment record is filled with result and conclusion fields.

**Acceptance Scenarios**:

1. **Given** a trained RL checkpoint, **When** evaluated over 50 games vs agent_v38 (seed 0), **Then** a score ≥ 55% means the RL agent passes the promotion threshold.
2. **Given** an RL agent that passes 55%, **When** checked with `diagnose_v9.py`, **Then** zero sun-collision or out-of-bounds losses are recorded.
3. **Given** an RL agent that fails 55% on 50 games, **When** the score is 45–55%, **Then** evaluation is extended to 100 games before a final pass/fail determination.

---

### User Story 3 — Submit Best RL Agent to Kaggle (Priority: P2)

The best RL-trained agent is packaged as a single self-contained Python file and submitted to the Kaggle leaderboard via `make submit`. The resulting public score is recorded in SUBMISSIONS.md.

**Why this priority**: Leaderboard score is the ultimate external validation — local win rate vs agent_v38 is necessary but not sufficient.

**Independent Test**: The agent file passes `make test` (smoke test vs random) and `make submit` without errors. SUBMISSIONS.md is updated with the resulting score.

**Acceptance Scenarios**:

1. **Given** a trained RL agent file, **When** submitted via `make submit`, **Then** a public Kaggle score is returned and recorded in SUBMISSIONS.md.
2. **Given** the submitted RL agent's Kaggle score, **When** compared to agent_v30's score of 763.2 (current best submission), **Then** an improvement is recorded as a milestone; a regression is documented with a root-cause note.

---

### Edge Cases

- What happens when the RL agent selects an invalid action (illegal fleet dispatch)?
- How does the agent behave when it has no ships available to send?
- What if training diverges and reward collapses — how is this detected and recovered from?
- Does the trained policy generalize across different map seeds, or overfit to training seeds?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The training loop MUST be launchable with a single command and log episode rewards to a file.
- **FR-002**: The training loop MUST save agent checkpoints at configurable intervals (default: every 100 episodes).
- **FR-003**: Training MUST be resumable from the most recent checkpoint after interruption.
- **FR-004**: The trained agent MUST be exportable as a single self-contained Python file compatible with `eval.py` and the Kaggle submission format.
- **FR-005**: The RL agent MUST produce a valid action every turn within the Kaggle actTimeout budget (<1 second/turn).
- **FR-006**: Illegal or unsafe actions (sun collision, out-of-bounds dispatch) MUST be masked or penalized during training so the agent does not learn to produce them.
- **FR-007**: The RL agent MUST be evaluable against any fixed agent using the existing `eval.py` harness without modifications to `eval.py`.
- **FR-008**: An experiment record MUST be written in `experiments/` documenting the RL training approach, hyperparameters, evaluation results, and conclusion before any Kaggle submission.
- **FR-009**: SUBMISSIONS.md MUST be updated after each Kaggle submission with the returned public score.

### Key Entities

- **Policy**: The learned decision function mapping game observations to fleet dispatch actions. Persisted as a checkpoint file; exported as inline Python for submission.
- **Episode**: One complete game (start to terminal state) used as a training sample.
- **Checkpoint**: A saved snapshot of the policy at a point in training, loadable for evaluation or resumption.
- **Reward Signal**: The scalar feedback given to the policy after each turn or episode. Derived from existing `reward_signal.py` constants and game outcome (win/loss/draw).
- **Experiment Record**: A Markdown file in `experiments/` following the established format (hypothesis, change, result, conclusion).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The RL agent achieves a score ≥ 55% vs agent_v38 over 50 games (local promotion threshold).
- **SC-002**: Zero sun-collision or out-of-bounds losses in a 50-game safety audit via `diagnose_v9.py`.
- **SC-003**: A Kaggle public score higher than agent_v30's current best of 763.2 is achieved and recorded.
- **SC-004**: A full training run of ≥ 1,000 episodes completes without crashing and produces a loadable checkpoint.
- **SC-005**: The exported RL agent file passes the existing smoke test (`make test`) without errors.

---

## Assumptions

- The existing `reward_signal.py` reward constants provide a usable training signal; additional reward shaping may be needed but is not assumed to be mandatory.
- The Kaggle Orbit Wars environment is deterministic given a seed, enabling reproducible evaluation.
- Training will run locally on the developer's machine; GPU acceleration is not assumed to be available.
- The RL agent is a single Python file at repo root following the `agent(obs)` function convention — no new file layout conventions are introduced.
- The `eval.py` and `diagnose_v9.py` harnesses are not modified as part of this feature.
- Mobile/web deployment is out of scope; the agent targets the Kaggle submission environment only.
- The RL approach is policy-based or value-based (e.g., PPO, DQN, or REINFORCE); the specific algorithm is a planning decision, not a spec constraint.
