# Feature Specification: Agent Improvement Experiments

**Feature Branch**: `005-agent-improvement-experiments`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Try another set of experiments to improve agent"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify Next High-Value Improvement Mechanics (Priority: P1)

A researcher reviews the current best agent (agent_v10) and the diagnostic data from prior experiments to identify which untried mechanics offer the best expected improvement. Each candidate mechanic is documented with a hypothesis before any code is written.

**Why this priority**: Without a clear hypothesis for each experiment, results are uninterpretable. This story ensures the team knows what to test and why before running any games.

**Independent Test**: Can be tested by confirming that an experiment record exists for each planned mechanic before any agent code is written, and that each record contains a hypothesis, expected outcome, and success threshold.

**Acceptance Scenarios**:

1. **Given** the current agent_v10 and its diagnostic baseline, **When** candidate mechanics are evaluated for expected impact, **Then** at least 3 distinct mechanics are identified, each with a written hypothesis and measurable success criterion.
2. **Given** a candidate mechanic, **When** it was previously tested and failed (e.g., defensive reinforcement in agent_v6), **Then** a revised hypothesis is provided explaining why a different implementation might succeed.

---

### User Story 2 - Run Isolated Mechanic Experiments (Priority: P1)

Each candidate mechanic is implemented as a standalone agent variant and evaluated in a 20-game head-to-head against agent_v10. Results determine whether the mechanic advances to a combined agent.

**Why this priority**: Isolating mechanics prevents confounding — if a combined agent loses, you can't tell which mechanic hurt it. Each mechanic must prove itself independently first.

**Independent Test**: Each agent variant can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v10.py --games 20` and produces a win rate. A mechanic passes if win rate ≥ 55%.

**Acceptance Scenarios**:

1. **Given** a candidate mechanic implemented in its own agent file, **When** evaluated over 20 games against agent_v10, **Then** the win rate is recorded and compared against the 55% pass threshold.
2. **Given** a mechanic that scores below 55%, **When** results are analyzed, **Then** the experiment record documents why it failed and whether a follow-up hypothesis is warranted.
3. **Given** multiple mechanics all passing 55%, **When** deciding which to combine, **Then** mechanics are ranked by win rate margin above 55%.

---

### User Story 3 - Build Combined Agent from Passing Mechanics (Priority: P2)

All mechanics that individually pass ≥ 55% are stacked into a new combined agent (agent_v15) and evaluated against agent_v10 over 20 games.

**Why this priority**: Stacking proven mechanics compounds the gains. This is the delivery vehicle for measurable agent improvement.

**Independent Test**: Run `eval.py --agent0 agent_v15.py --agent1 agent_v10.py --games 20` and verify win rate exceeds 65%.

**Acceptance Scenarios**:

1. **Given** all passing mechanics applied to a new agent, **When** evaluated over 20 games against agent_v10, **Then** win rate is ≥ 65%.
2. **Given** the combined agent beats agent_v10 by ≥ 65%, **When** the README and experiment log are updated, **Then** the new agent is listed as the best agent with its win rate.
3. **Given** the combined agent does NOT reach 65%, **When** results are analyzed, **Then** mechanics are tested in subsets to isolate regressions.

---

### Edge Cases

- What if no mechanic individually reaches 55%? Document all results, do not combine, and re-hypothesize.
- What if a mechanic hurts performance when combined but helped in isolation? Test subsets to find the conflicting pair.
- What if the experiment surface covers too many mechanics simultaneously? Limit to 4 candidates per round to keep the iteration cycle short.
- What if a mechanic requires changing the safety logic (sun/planet checks)? It must not regress SC-002 or SC-003 from the fleet safety spec.
- What if Candidate C's defense threshold (`incoming > garrison + production×5`) triggers every turn late-game? Cap reinforcement dispatches to one per threatened planet per turn.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each candidate mechanic MUST have an experiment record in `experiments/` before its agent file is written (Constitution IV).
- **FR-002**: Each candidate agent MUST be implemented as a self-contained Python file at the repo root, inheriting all fixes from agent_v10 (planet obstruction, orbit-lead refinement, comet clamping).
- **FR-003**: Each candidate agent MUST be evaluated against agent_v10 over exactly 20 games using seeds 0–19. Candidate B runs three sub-experiments (garrison floors: production×5, production×10, fixed 10); the best-performing variant is the one that advances.
- **FR-004**: A mechanic MUST achieve ≥ 55% win rate vs agent_v10 to advance to the combined agent.
- **FR-005**: The combined agent MUST include all passing mechanics and be evaluated against agent_v10 over 20 games.
- **FR-006**: README.md Agents table MUST be updated after each agent is created and evaluated.
- **FR-007**: No existing safety guarantees (sun avoidance, OOB rejection, planet obstruction) may be removed or weakened in any new agent.
- **FR-008**: Each new agent file MUST include a docstring listing which mechanics it adds and which prior agents it builds on.

### Candidate Mechanics to Experiment With

The following mechanics are prioritized by expected impact based on current agent behavior and known gaps:

- **Candidate A (agent_v11) — Redundant fleet avoidance**: Skip launching at a target that already has a friendly fleet en route with enough ships to capture it. Prevents wasting ships on already-won engagements.
- **Candidate B (agent_v12) — Garrison sizing**: Send only enough ships to capture (target.ships + 1) but also ensure the source planet retains a minimum safe garrison. Three garrison floor values are evaluated as sub-experiments: `production × 5`, `production × 10`, and a fixed floor of `10` ships. The best-performing value advances to agent_v15.
- **Candidate C (agent_v13) — Threat-aware defense**: Detect enemy fleets heading toward owned planets; dispatch reinforcements only when `incoming_ships > current_garrison + production × 5`. This narrower threshold avoids the broad defensive drag that hurt agent_v6, which triggered on any `incoming > garrison` condition.
- **Candidate D (agent_v14) — Single-sender coordination**: When multiple owned planets can target the same enemy, only the most efficient sender fires — defined as the planet with the lowest `distance ÷ available_ships_surplus` ratio. Avoids redundant multi-sender pile-ons and frees other planets to attack different targets.
- **Combined (agent_v15)**: All passing mechanics (≥55% vs agent_v10) stacked on top of agent_v10.

### Key Entities

- **Candidate Mechanic**: A single behavioral change tested in isolation; characterized by a hypothesis, agent file, and win rate vs agent_v10.
- **Combined Agent**: A new agent file stacking all mechanics that individually passed ≥ 55%; evaluated against agent_v10 as the final gate.
- **Pass Threshold**: 55% win rate over 20 games vs agent_v10 — the bar a mechanic must clear to be included in the combined agent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 3 candidate mechanics are individually evaluated with documented hypotheses and results.
- **SC-002**: At least one mechanic achieves ≥ 55% win rate vs agent_v10 over 20 games.
- **SC-003**: A combined agent is produced that achieves ≥ 65% win rate vs agent_v10 over 20 games.
- **SC-004**: No safety regression — the combined agent (agent_v15) has 0% sun losses and 0% OOB losses, verified via `diagnose_v9.py --agent agent_v15.py --games 20`. Isolated candidates are not required to run the diagnostic.
- **SC-005**: The README Agents table is updated with all new agents and their win rates.

## Clarifications

### Session 2026-05-30

- Q: How should candidate agent files be numbered? → A: v11–v14 for isolated experiments (one per candidate mechanic), v15 for the combined agent.
- Q: What garrison minimum formula should Candidate B use? → A: Try multiple values as sub-experiments — evaluate at least production×5, production×10, and a fixed floor of 10, pick the best-performing one before advancing to the combined agent.
- Q: How should Candidate D calculate the "most efficient sender"? → A: `distance ÷ available_ships_surplus` — the sender with the shortest trip relative to its ships above garrison floor wins the right to attack that target.
- Q: Should diagnose_v9.py run on each candidate or only the combined agent? → A: Combined agent only.
- Q: How should Candidate C define "threat exceeds garrison"? → A: `incoming_ships > current_garrison + production × 5` — threat must exceed garrison plus 5 turns of production before reinforcements are dispatched.

## Assumptions

- agent_v10.py is the immutable baseline for all experiments in this round; all candidate agents build on it.
- The 55% individual pass threshold and 65% combined threshold are based on the precedent set in the 003-agent-gap-analysis feature.
- "Redundant fleet" is defined as: a friendly fleet already en route to a planet whose ship count ≥ target.ships + 1.
- Evaluation uses seeds 0–19 (20 games) to match the standard established in prior experiments.
- Mechanics that require fundamentally redesigning the targeting loop (e.g., MCTS, RL) are out of scope — only rule-based heuristics are considered.
- The experiment harness (diagnose_v9.py) and eval.py are used as-is; no modifications to evaluation tooling are in scope.
