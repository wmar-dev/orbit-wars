# Feature Specification: Agent Improvement Experiments — Round 2

**Feature Branch**: `006-agent-experiments-round-2`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Do another round of experiments."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify and Hypothesize New Candidate Mechanics (Priority: P1)

A researcher reviews agent_v15 (the current best agent, 70% vs agent_v10) and selects untested mechanics that target known weaknesses in the current orbit-lead, fleet-sizing, and scoring logic. Each candidate is documented with a hypothesis before any code is written.

**Why this priority**: Without a hypothesis per experiment, results are uninterpretable. Prior analysis of agent_v15 reveals three concrete structural gaps — the orbit-lead speed estimate uses the wrong fleet size causing targeting misses, fleet sizing ignores garrison growth during transit causing failed captures, and the target-scoring formula is unweighted by capture difficulty — that represent the highest-expected-value candidates for this round.

**Independent Test**: Confirm that an experiment record exists for each candidate mechanic before its agent file is written. Each record must include a hypothesis, change description, success threshold (≥55% win rate vs agent_v15), and conclusion.

**Acceptance Scenarios**:

1. **Given** the current agent_v15 and its known structural gaps, **When** candidate mechanics are selected, **Then** at least 4 distinct mechanics are identified, each with a written hypothesis, a specific change description, and a measurable pass threshold.
2. **Given** a candidate mechanic that resembles a previously-failed mechanic, **When** it is proposed, **Then** the experiment record includes a revised hypothesis explaining how this attempt differs from the prior failure.

---

### User Story 2 - Run Isolated Mechanic Experiments (Priority: P1)

Each candidate mechanic is implemented as a standalone agent variant (agent_v16–v19) built on agent_v15 and evaluated in a 20-game head-to-head against agent_v15. Results determine whether the mechanic advances to a combined agent (agent_v20).

**Why this priority**: Isolating mechanics prevents confounding. A combined agent that loses can't diagnose which mechanic caused the regression; each mechanic must prove itself independently first.

**Independent Test**: Each candidate can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v15.py --games 20 --seed 0` and produces a win rate. A mechanic passes if win rate ≥ 55%.

**Acceptance Scenarios**:

1. **Given** a candidate mechanic implemented in its own agent file, **When** evaluated over 20 games (seeds 0–19) against agent_v15, **Then** the win rate is recorded in the experiment record against the 55% pass threshold.
2. **Given** a mechanic that scores below 55%, **When** results are analyzed, **Then** the experiment record documents root-cause reasoning and whether a follow-up hypothesis is warranted.
3. **Given** multiple mechanics all passing 55%, **When** ranking for inclusion in the combined agent, **Then** mechanics are ordered by win-rate margin above 55%.

---

### User Story 3 - Build Combined Agent from Passing Mechanics (Priority: P2)

All mechanics that individually pass ≥ 55% vs agent_v15 are stacked into a new combined agent (agent_v20) and evaluated against agent_v15 over 20 games.

**Why this priority**: Stacking proven mechanics compounds the gains and advances the project's best agent baseline.

**Independent Test**: Run `eval.py --agent0 agent_v20.py --agent1 agent_v15.py --games 20` and verify win rate exceeds 65%.

**Acceptance Scenarios**:

1. **Given** all passing mechanics applied to a new combined agent, **When** evaluated over 20 games against agent_v15, **Then** win rate is ≥ 65%.
2. **Given** the combined agent beats agent_v15 by ≥ 65%, **When** the README and experiment log are updated, **Then** agent_v20 is listed as the best agent with its win rate.
3. **Given** the combined agent does NOT reach 65%, **When** results are analyzed, **Then** mechanics are tested in subsets to isolate regressions.

---

### Edge Cases

- What if the orbit-lead speed fix (Candidate E) causes fleets to overshoot because they now arrive earlier? The `_refined_orbit_lead` two-iteration loop should compensate; if overshoot persists, add a third refinement iteration.
- What if no mechanic individually reaches 55% vs agent_v15? Document all results, do not combine, and re-hypothesize for a subsequent round.
- What if a passing mechanic causes a regression when combined (interacts negatively with another)? Test subsets to isolate the conflicting pair; exclude the lower-margin mechanic.
- What if transit-adjusted fleet sizing makes the agent skip all targets because it can't afford the adjusted send? Cap adjusted send at `source.ships` and fall through to a no-op rather than reducing to the old formula.
- What if adaptive range expansion causes the agent to attack unreachable targets (path blocked by sun or planet)? The existing `_path_safe()` check already filters these; no special handling needed.
- What if game length is too short for ROI scoring to differentiate short vs long captures? Use a fixed proxy of 100 remaining turns (a conservative estimate that still rewards faster captures).
- What if a mechanic requires changing the safety logic (sun/planet checks)? It must not regress SC-002 (sun losses) or SC-003 (OOB losses) from the fleet safety spec.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each candidate mechanic MUST have an experiment record in `experiments/` before its agent file is written (Constitution IV).
- **FR-002**: Each candidate agent (v16–v19) MUST be implemented as a self-contained Python file at the repo root, inheriting all mechanics from agent_v15 (single-sender coordination + all agent_v10 safety guards).
- **FR-003**: Each candidate agent MUST be evaluated against agent_v15 over exactly 20 games using seeds 0–19.
- **FR-004**: A mechanic MUST achieve ≥ 55% win rate vs agent_v15 to advance to the combined agent (agent_v20).
- **FR-005**: The combined agent (agent_v20) MUST include all passing mechanics and be evaluated against agent_v15 over 20 games with a ≥ 65% target.
- **FR-006**: README.md Agents table MUST be updated after each agent is created and evaluated.
- **FR-007**: No existing safety guarantees (sun avoidance, OOB rejection, planet obstruction) may be removed or weakened in any new agent.
- **FR-008**: Each new agent file MUST include a docstring listing which mechanics it adds and which prior agents it builds on.

### Candidate Mechanics to Experiment With

The following mechanics are prioritized based on structural gaps identified in agent_v15. Candidates are ordered by expected impact:

- **Candidate E (agent_v16) — Speed-corrected orbit lead**: Fix the orbit-lead prediction to use `fleet_speed(target.ships + 1)` instead of `fleet_speed(mine.ships + 1)`. The current code computes travel time based on the source planet's full ship count, but the actual fleet sent is only `target.ships + 1` (often far fewer ships, thus slower). This causes the predicted intercept position to be too early in the orbit — the fleet aims where the planet *was* rather than where it *will be*. For example, if the source has 80 ships but sends 11, speed is overestimated by ~70%, and the planet has moved well past the aim point by the time the fleet arrives.

- **Candidate F (agent_v17) — Transit-adjusted fleet sizing**: Estimate travel turns as `distance / fleet_speed(target.ships + 1)`. Send `target.ships + target.production × travel_turns + 1` ships to account for garrison growth during transit. If the source cannot afford this amount, skip the target rather than undersizing. Addresses the silent failure mode where a fleet launched at a 10-ship planet arrives 15 turns later to find 25+ ships and is defeated.

- **Candidate G (agent_v18) — Adaptive range expansion**: Compute the ship-count ratio: `own_total / enemy_total`. When ratio ≥ 1.5 (winning decisively), expand `range_factor` from 2.0 to 3.5 to press the advantage across the map. When ratio ≤ 0.7 (losing), contract to 1.5 to focus on nearby high-probability targets. Addresses the fixed-range blind spot that ignores game-state advantage.

- **Candidate H (agent_v19) — Capture-ROI scoring**: Replace the `production / distance` target score with `production × (100 − travel_turns) / (target.ships + target.production × travel_turns + 1)`. This normalizes by capture cost and remaining turns owned, rewarding planets that are cheap to capture early and have time to produce. Uses `travel_turns = distance / fleet_speed(target.ships + 1)`.

- **Combined (agent_v20)**: All mechanics from v16–v19 that individually achieve ≥ 55% win rate vs agent_v15, stacked on agent_v15.

### Key Entities

- **Candidate Mechanic**: A single behavioral change tested in isolation; characterized by a hypothesis, agent file, and win rate vs agent_v15.
- **Combined Agent**: A new agent file (agent_v20) stacking all mechanics that passed ≥ 55% vs agent_v15; evaluated against agent_v15 as the final gate.
- **Pass Threshold**: ≥ 55% win rate over 20 games vs agent_v15.
- **Travel Turns**: Estimated as `distance / fleet_speed(target.ships + 1)` — the actual fleet size being sent; used for orbit-lead correction (E), fleet sizing (F), and ROI scoring (H).
- **Orbit-Lead Speed Bug**: In agent_v15 line 241, `speed = fleet_speed(mine.ships + 1)` uses the source planet's full ship count. The fix is to compute speed per target as `fleet_speed(target.ships + 1)` at the point of orbit-lead calculation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 4 candidate mechanics are individually evaluated with documented hypotheses and results.
- **SC-002**: At least one mechanic achieves ≥ 55% win rate vs agent_v15 over 20 games.
- **SC-003**: A combined agent (agent_v20) is produced that achieves ≥ 65% win rate vs agent_v15 over 20 games.
- **SC-004**: No safety regression — agent_v20 has 0% sun losses and 0% OOB losses, verified via `diagnose_v9.py --agent agent_v20.py --games 20`.
- **SC-005**: The README Agents table is updated with all new agents and their win rates.

## Clarifications

### Session 2026-05-30

- Q: Are fleets currently missing orbiting targets? → A: Yes. The orbit-lead speed is computed as `fleet_speed(mine.ships + 1)` (source fleet size) but the actual fleet sent is `fleet_speed(target.ships + 1)` (capture size only). When the source has many more ships than the target, the speed is significantly overestimated — fleets arrive later than predicted and the orbiting planet has moved past the aim point. Candidate E (agent_v16) fixes this directly.
- Q: Should the orbit-lead fix be applied to all candidates, not just Candidate E? → A: No — experiment discipline requires testing it in isolation first. If Candidate E passes, it is included in the combined agent and all subsequent rounds inherit it. Candidates F, G, H are built on agent_v15 (which has the unfixed orbit-lead); this ensures their results are comparable to the baseline.

## Assumptions

- agent_v15.py is the immutable baseline for all experiments in this round; all candidate agents (v16–v19) build on it.
- The new baseline is agent_v15 (not agent_v10); the 55%/65% thresholds remain unchanged.
- "Travel turns" for fleet sizing and ROI scoring uses `distance / fleet_speed(ships_to_send)` where `fleet_speed` is the existing formula from agent_v15.
- Planets do produce ships each turn during fleet transit; the current agent's silent failure mode (sending `target.ships + 1` without accounting for growth) is a real gap worth testing.
- The orbit-lead speed bug is confirmed: `fleet_speed(mine.ships + 1)` at agent_v15 line 241 is the wrong value; the fix uses `fleet_speed(target.ships + 1)` per target.
- Mechanics that require fundamentally redesigning the targeting loop (e.g., MCTS, RL, multi-turn planning) are out of scope — only rule-based heuristics are considered.
- The experiment harness (`diagnose_v9.py`) and `eval.py` are used as-is; no modifications to evaluation tooling are in scope.
- Evaluation uses seeds 0–19 (20 games) to match the standard established in prior experiments.
- Candidates E, F, and H all depend on the correct travel-turns estimate (`distance / fleet_speed(target.ships + 1)`); they interact. The combined agent should apply all passing mechanics; if they regress together, test subsets.
