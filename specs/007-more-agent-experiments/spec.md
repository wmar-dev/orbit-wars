# Feature Specification: Agent Improvement Experiments — Round 3

**Feature Branch**: `007-more-agent-experiments`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Do many more experiments, until we have a better agent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify and Hypothesize New Candidate Mechanics (Priority: P1)

A researcher reviews agent_v20 (the current best locally-evaluated agent, 75% vs agent_v15 over 20 games) and selects untested mechanics that address known gaps in defense, range strategy, and target prioritization. Each candidate is documented with a hypothesis before any code is written.

**Why this priority**: Without a hypothesis per experiment, results are uninterpretable. Agent_v20's failure modes include undefended multi-threat scenarios, inability to reach large distant enemy planets, and ROI scoring that sometimes over-values cheap-but-low-impact neutrals. These represent the highest-expected-value candidates for this round.

**Independent Test**: Confirm that an experiment record exists for each candidate mechanic before its agent file is written. Each record must include a hypothesis, change description, success threshold (≥ 55% win rate vs agent_v20), and conclusion.

**Acceptance Scenarios**:

1. **Given** the current agent_v20 and its known structural gaps, **When** candidate mechanics are selected, **Then** at least 4 distinct mechanics are identified, each with a written hypothesis, a specific change description, and a measurable pass threshold.
2. **Given** a candidate mechanic that resembles a previously-failed mechanic (e.g., Candidates F or G), **When** it is proposed, **Then** the experiment record includes a revised hypothesis explaining how this attempt differs from the prior failure.

---

### User Story 2 - Run Isolated Mechanic Experiments (Priority: P1)

Each candidate mechanic is implemented as a standalone agent variant (agent_v21–v24) built on agent_v20 and evaluated in a 20-game head-to-head against agent_v20. Results determine whether the mechanic advances to a combined agent (agent_v25).

**Why this priority**: Isolating mechanics prevents confounding. A combined agent that loses can't diagnose which mechanic caused the regression; each mechanic must prove itself independently first.

**Independent Test**: Each candidate can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v20.py --games 20 --seed 0` and produces a win rate. A mechanic passes if win rate ≥ 55%.

**Acceptance Scenarios**:

1. **Given** a candidate mechanic implemented in its own agent file, **When** evaluated over 20 games (seeds 0–19) against agent_v20, **Then** the win rate is recorded in the experiment record against the 55% pass threshold.
2. **Given** a mechanic that scores below 55%, **When** results are analyzed, **Then** the experiment record documents root-cause reasoning and whether a follow-up hypothesis is warranted.
3. **Given** multiple mechanics all passing 55%, **When** ranking for inclusion in the combined agent, **Then** mechanics are ordered by win-rate margin above 55%.

---

### User Story 3 - Build Combined Agent from Passing Mechanics (Priority: P2)

All mechanics that individually pass ≥ 55% vs agent_v20 are stacked into a new combined agent (agent_v25) and evaluated against agent_v20 over 20 games.

**Why this priority**: Stacking proven mechanics compounds the gains and advances the project's best agent baseline.

**Independent Test**: Run `eval.py --agent0 agent_v25.py --agent1 agent_v20.py --games 20` and verify win rate exceeds 65%.

**Acceptance Scenarios**:

1. **Given** all passing mechanics applied to a new combined agent, **When** evaluated over 20 games against agent_v20, **Then** win rate is ≥ 65%.
2. **Given** the combined agent beats agent_v20 by ≥ 65%, **When** the README and experiment log are updated, **Then** agent_v25 is listed as the best local agent with its win rate.
3. **Given** the combined agent does NOT reach 65%, **When** results are analyzed, **Then** mechanics are tested in subsets to isolate regressions.

---

### User Story 4 - Continue Iterating Until a Better Agent Exists (Priority: P2)

If Round 3 (v21–v25) does not yield a combined agent that surpasses agent_v20, additional experiment rounds are run (v26–v30, etc.) with revised hypotheses based on prior failures, continuing until a new best agent is established.

**Why this priority**: The user's goal is "a better agent," not just completing one round. Iteration continues until the improvement bar is cleared.

**Independent Test**: A better agent exists when a new combined agent beats the previous best by ≥ 65% over 20 games.

**Acceptance Scenarios**:

1. **Given** no combined agent in Round 3 beats agent_v20 by ≥ 65%, **When** a new round begins, **Then** hypotheses are revised using failure analysis from all prior rounds before any new agent is written.
2. **Given** a new combined agent beats the previous best by ≥ 65%, **When** results are logged, **Then** the README is updated and that agent is declared the new local best.

---

### Edge Cases

- What if no mechanic in Round 3 individually reaches 55% vs agent_v20? Document all results, do not combine, revise hypotheses, and begin Round 4 immediately.
- What if a passing mechanic causes a regression when combined (interacts negatively with another)? Test subsets to isolate the conflicting pair; exclude the lower-margin mechanic.
- What if agent_v20 beats a candidate unevenly across seeds (e.g., 45% with seed 0 but 65% with seed 42)? Report the full-20-game aggregate, not per-seed results — the aggregate is the pass criterion.
- What if a revised version of a previously-failed mechanic (e.g., a softer Candidate G) is tested? It must be documented as a distinct candidate with a revised hypothesis explaining the change.
- What if defensive dispatch competes with offensive dispatch for the same ships? Defense takes priority over offense for any source planet with an incoming enemy threat that arrives within the guaranteed-loss threshold.
- What if the multi-source gang attack conflicts with single-sender coordination? Multi-source send is explicitly an override of single-sender for targets that no single source can afford; document the interaction precisely in the experiment record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each candidate mechanic MUST have an experiment record in `experiments/` before its agent file is written (Constitution IV).
- **FR-002**: Each candidate agent (v21–v24 per round) MUST be implemented as a self-contained Python file at the repo root, inheriting all mechanics from agent_v20.
- **FR-003**: Each candidate agent MUST be evaluated against agent_v20 over exactly 20 games using seeds 0–19.
- **FR-004**: A mechanic MUST achieve ≥ 55% win rate vs agent_v20 to advance to the combined agent (agent_v25).
- **FR-005**: The combined agent (agent_v25) MUST include all passing mechanics and be evaluated against agent_v20 over 20 games with a ≥ 65% target.
- **FR-006**: README.md Agents table MUST be updated after each agent is created and evaluated.
- **FR-007**: No existing safety guarantees (sun avoidance, OOB rejection, planet obstruction) may be removed or weakened in any new agent.
- **FR-008**: Each new agent file MUST include a docstring listing which mechanics it adds and which prior agents it builds on.
- **FR-009**: If Round 3 does not yield a better combined agent, hypotheses MUST be revised and a new round begun — iteration continues until the goal is met.
- **FR-010**: The best-performing agent by local win rate MUST be diagnosed with `diagnose_v9.py` to verify 0 sun losses and 0 OOB losses before being declared the new best.

### Candidate Mechanics to Experiment With (Round 3)

The following mechanics are prioritized based on structural gaps identified in agent_v20. Candidates are ordered by expected impact and independence from prior failures:

- **Candidate I (agent_v21) — Reactive defense dispatch**: On each turn, scan all incoming enemy fleets. For each owned planet P where an incoming fleet will arrive in ≤ T turns and the arriving fleet exceeds P's projected garrison, dispatch reinforcements from the nearest owned planet with sufficient surplus ships (after its own garrison floor). Skip offensive dispatch for that source this turn. Hypothesis: Agent_v20 never defends, losing planets that a targeted reinforcement could save. Prior Candidate C (10% vs v10) defended globally and wasted ships; this version triggers only on specific, imminent threats.

- **Candidate J (agent_v22) — Smooth adaptive range**: Replace the fixed `RANGE_FACTOR = 2.0` with `clamp(2.0 * (own_total / max(1, enemy_total)) ** 0.25, 1.5, 3.5)`. This applies a gentle power-law expansion when winning and mild contraction when losing. Hypothesis: Candidate G (0% vs v15) used hard thresholds (1.5 and 3.5) causing extreme contraction when losing; a smooth continuous function achieves the same winning-state expansion without catastrophic contraction.

- **Candidate K (agent_v23) — Enemy-territory priority when winning**: When `own_total / max(1, enemy_total) ≥ 1.5`, multiply the ROI score of enemy-owned planets by 1.5 (a constant bias factor). Leave neutral scoring unchanged. Hypothesis: When significantly ahead, targeting enemy planets directly ends the game faster than expanding into neutrals; the current ROI formula treats neutrals and enemy planets identically, sometimes choosing cheap neutrals over strategically superior enemy targets.

- **Candidate L (agent_v24) — Two-source coordinated attack**: When the best target requires more ships than any single owned planet can send after maintaining its garrison floor, allow the two nearest owned planets to each send a proportional share in the same turn, provided neither source drops below its garrison floor after dispatch. Hypothesis: Large enemy strongholds that single-source coordination (agent_v15's primary mechanic) cannot afford are currently skipped indefinitely; a two-source coordinated send can flip high-production targets that would otherwise never be reachable.

- **Combined (agent_v25)**: All mechanics from Candidates I–L that individually achieve ≥ 55% win rate vs agent_v20, stacked on agent_v20.

### Key Entities

- **Candidate Mechanic**: A single behavioral change tested in isolation; characterized by a hypothesis, agent file, and win rate vs agent_v20.
- **Combined Agent**: A new agent file stacking all mechanics that passed ≥ 55% vs the round's baseline; evaluated against the baseline as the final gate.
- **Pass Threshold**: ≥ 55% win rate over 20 games vs agent_v20 (or the current round's baseline).
- **Baseline Agent**: The combined agent from the prior round; for Round 3 this is agent_v20. Updates each round if a new combined agent wins by ≥ 65%.
- **Garrison Floor**: `GARRISON_FLOOR_FACTOR × planet.production` ships — the minimum ships a source keeps before any dispatch; inherited from agent_v15/v20.
- **Projected Garrison**: Current ships on planet + production × arrival_turns — used to determine if reinforcement is needed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 4 candidate mechanics are individually evaluated with documented hypotheses and results per round.
- **SC-002**: At least one mechanic achieves ≥ 55% win rate vs the round's baseline agent over 20 games.
- **SC-003**: A combined agent is produced that achieves ≥ 65% win rate vs the round's baseline agent over 20 games.
- **SC-004**: No safety regression — the new best combined agent has 0% sun losses and 0% OOB losses verified via `diagnose_v9.py`.
- **SC-005**: The README Agents table is updated with all new agents and their win rates after each evaluation.
- **SC-006**: Iteration continues across multiple rounds until SC-003 is achieved — this feature is not complete until a new best agent exists.

## Assumptions

- Agent_v20 (75% vs agent_v15, 0 sun/OOB losses) is the local self-play baseline; all Round 3 candidates are built on agent_v20.
- Agent_v8 is the current Kaggle leaderboard best. Agent_v15 was submitted but performed worse than agent_v8 on the leaderboard, indicating that local self-play win rates do not directly predict leaderboard performance. Agents v16–v20 have not been submitted.
- Local win rates are a necessary but not sufficient signal. The leaderboard uses diverse real opponents; a higher local win rate vs the previous agent version does not guarantee leaderboard improvement. The ultimate validation for any new best agent is leaderboard submission and comparison against agent_v8's score.
- The leaderboard regression from v8 to v15 is an unresolved open question — possible causes include: (1) the single-sender coordination mechanic reducing aggression against diverse opponent styles, (2) the safety guards from v10 being overly conservative against non-symmetric opponents, or (3) 4-player game dynamics. All local self-play evaluation has used 2-player games; the Kaggle leaderboard includes 4-player games where multi-threat handling, diplomacy, and resource allocation are fundamentally different. Mechanics tuned for 2-player may perform poorly or even negatively in 4-player scenarios.
- 4-player evaluation is not covered by the standard `eval.py --games 20` harness. A separate evaluation run with 4 players may be needed to diagnose the leaderboard regression fully.
- 20 games (seeds 0–19) with `eval.py` is the standard evaluation window; marginal candidates (50–55%) may warrant a 40-game follow-up before being excluded.
- `eval.py` and `diagnose_v9.py` are not modified — all experimental changes are confined to new agent files.
- Mechanics from Rounds 1 and 2 that failed are not retried unless the hypothesis changes substantially (documented in the new experiment record).
- The experiment round count (Round 3 = v21–v25) increments by 5 agent slots per round; future rounds use v26–v30, v31–v35, etc.
