# Feature Specification: Agent Improvement Experiments — Round 6

**Feature Branch**: `010-agent-experiments-round-3`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Do another round of experiments"

## Background & Context

The current best local agent is **agent_v33**, which builds on the bug-fixed baseline (agent_v32: converged orbit-lead + documented-field comet evacuation) and adds production-squared ROI scoring (Candidate R, 60% vs agent_v32 over 50 games).

All prior mechanics have been retested vs agent_v32, and only Candidate R passed. The remaining failure modes of agent_v33 appear to be:

1. **Overkill dispatch** — multiple source planets occasionally send redundant fleets to the same target, wasting ships that could have captured a second planet instead.
2. **Transit attrition** — the agent calculates fleet size as `target.ships + 1` rather than `target.ships + production × travel_turns`, meaning it under-sends to growing enemy planets and loses the fleet on arrival.
3. **Garrison depletion under threat** — the fixed garrison floor (3× production) does not account for incoming enemy fleets; threatened planets get drained by outbound attacks and fall to the arriving enemy.
4. **Slow endgame** — when the agent is comfortably winning (own ships ≥ 2× all enemies combined), it maintains the same 3× production garrison floor it uses when losing, slowing the kill.

This round tests four independent mechanics targeting these gaps. Each candidate is evaluated over 50 games vs agent_v33 (PASS ≥ 55% score). A combined agent is built from all passing mechanics and evaluated vs agent_v33 at ≥ 65% target.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Identify and Hypothesize New Candidate Mechanics (Priority: P1)

A researcher reviews agent_v33 and its documented failure modes, selects four distinct candidate mechanics from the identified gaps, and documents each with a hypothesis and measurable pass threshold before any agent file is written.

**Why this priority**: Without a written hypothesis per candidate, results are uninterpretable — we cannot distinguish lucky randomness from structural improvement.

**Independent Test**: Confirm that an experiment record exists in `experiments/` for each candidate before its agent file is written. Each record must include a hypothesis, change description, pass threshold (≥ 55% score vs agent_v33), and a conclusion field to be filled after evaluation.

**Acceptance Scenarios**:

1. **Given** agent_v33 as the current best and its four identified failure modes, **When** candidates are documented, **Then** exactly one candidate targets each failure mode, each with a distinct written hypothesis and a 55% pass threshold.
2. **Given** a candidate that resembles a prior failed mechanic (e.g., prior Candidate I: reactive defense), **When** proposed, **Then** the experiment record explains the specific change that differentiates this attempt from the prior failure.

---

### User Story 2 — Run Isolated Mechanic Experiments (Priority: P1)

Each candidate mechanic is implemented as a standalone agent file (agent_v34–agent_v37), built on agent_v33, and evaluated in a 50-game head-to-head against agent_v33. The 50-game window is required (not 20) because agent_v33 uses production² ROI which produces decisive outcomes — 50 games gives stable win-rate estimates.

**Why this priority**: Isolating mechanics prevents confounding. A combined agent that regresses cannot diagnose which mechanic caused the regression.

**Independent Test**: Each candidate can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v33.py --games 50 --seed 0` and produces a score. Score = (wins + 0.5 × draws) / 50. A mechanic passes if score ≥ 55%.

**Acceptance Scenarios**:

1. **Given** a candidate mechanic implemented in its own agent file, **When** evaluated over 50 games against agent_v33 (seeds 0–49), **Then** the win rate is recorded in the experiment record against the 55% pass threshold.
2. **Given** a mechanic that scores below 55%, **When** results are analyzed, **Then** the experiment record includes a root-cause note and whether a revised hypothesis is warranted for a future round.
3. **Given** a mechanic that scores 50–55% (borderline), **When** deciding whether to include it in the combined agent, **Then** extend the evaluation to 100 games before making a pass/fail determination.
4. **Given** multiple mechanics all passing 55%, **When** ranking for inclusion in the combined agent, **Then** mechanics are ordered by win-rate margin above 55% to inform trade-off decisions.

---

### User Story 3 — Build Combined Agent from Passing Mechanics (Priority: P2)

All mechanics that individually pass ≥ 55% vs agent_v33 are stacked into a new combined agent (agent_v38) and evaluated against agent_v33 over 50 games.

**Why this priority**: Compounding proven mechanics advances the local best-agent baseline.

**Independent Test**: Run `eval.py --agent0 agent_v38.py --agent1 agent_v33.py --games 50` and verify score ≥ 65%.

**Acceptance Scenarios**:

1. **Given** all passing mechanics applied to agent_v38, **When** evaluated over 50 games against agent_v33, **Then** score ≥ 65%.
2. **Given** agent_v38 passes ≥ 65%, **When** safety audit runs via `diagnose_v9.py`, **Then** 0 sun losses and 0 OOB losses across the 50 games.
3. **Given** agent_v38 does NOT reach 65%, **When** results are analyzed, **Then** mechanics are tested in subsets to isolate regressions, and the best-performing subset becomes the promotion candidate.
4. **Given** agent_v38 is promoted as the new best, **When** README.md and Makefile are updated, **Then** the Agents table lists agent_v38 with its score vs agent_v33, bolded as the current best.

---

### User Story 4 — Submit Best Agent to Leaderboard (Priority: P3)

After a new combined agent is promoted locally, it is submitted to the Kaggle leaderboard to measure performance against diverse real opponents.

**Why this priority**: Local self-play win rate does not guarantee leaderboard improvement (regression observed from v8 to v15). Leaderboard submission is the ultimate validation.

**Independent Test**: A successful submission produces a leaderboard score higher than the current best submission (agent_v8: 639.0, agent_v15: 605.2).

**Acceptance Scenarios**:

1. **Given** agent_v38 is the new local best, **When** submitted to Kaggle via `make submit`, **Then** a leaderboard score is returned and recorded in `SUBMISSIONS.md`.
2. **Given** the new leaderboard score is lower than agent_v8 (639.0), **When** the regression is diagnosed, **Then** `SUBMISSIONS.md` records the failure and the likely cause (4-player vs 2-player self-play mismatch, over-aggressive garrison reduction, etc.).

---

### Edge Cases

- What if no mechanic in Round 6 individually reaches 55% vs agent_v33? Document all results, skip the combined agent step, revise hypotheses, and identify new candidates for Round 7.
- What if a passing mechanic causes a regression when combined (interacts negatively with another)? Test subsets to isolate the conflicting pair; exclude the lower-margin mechanic.
- What if fleet deduplication skips a target the agent should still attack (because a friendly fleet is en route but insufficient)? The deduplication check must compare in-transit fleet size vs target's projected garrison at arrival — not just a binary "fleet is heading there" check.
- What if transit-adjusted sizing vastly over-sends (production × travel_turns is much larger than actual garrison growth because the enemy also reinforces)? Record the over-send rate and tune the sizing coefficient if needed.
- What if the winning-threshold garrison reduction (Candidate V) triggers on a game turn where the agent is only momentarily ahead and then falls behind? The mechanic is evaluated turn-by-turn — no state is carried between turns, so the garrison floor reverts to 3× production as soon as the threshold is no longer met.
- What if `diagnose_v9.py` shows increased transit loss rate for the combined agent? Transit losses (fleets arriving at wrong position or being intercepted) are not safety failures — record them as context but do not gate promotion on them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each candidate mechanic MUST have an experiment record in `experiments/` before its agent file is written.
- **FR-002**: Each candidate agent (v34–v37) MUST be implemented as a self-contained Python file at the repo root, inheriting all logic from agent_v33.
- **FR-003**: Each candidate agent MUST be evaluated against agent_v33 over exactly 50 games using seeds 0–49. Score = (wins + 0.5 × draws) / 50.
- **FR-004**: A mechanic MUST achieve ≥ 55% score vs agent_v33 to advance to the combined agent (agent_v38). Borderline (50–55%): extend to 100 games before excluding.
- **FR-005**: The combined agent (agent_v38) MUST include all passing mechanics and be evaluated against agent_v33 over 50 games with a ≥ 65% score target.
- **FR-006**: README.md Agents table MUST be updated after each agent is created and evaluated. The best agent MUST be bolded. Makefile `AGENT` and `RENDER_AGENT` variables MUST point to the current best agent.
- **FR-007**: No existing safety guarantees (sun avoidance, OOB rejection, planet obstruction check, documented comet evacuation) may be removed or weakened in any new agent.
- **FR-008**: Each new agent file MUST include a docstring listing which mechanics it adds and which prior agents it builds on.
- **FR-009**: The promoted combined agent MUST pass `diagnose_v9.py` with 0 sun losses and 0 OOB losses across the evaluation games.
- **FR-010**: If no combined agent passes the 65% gate in Round 6, hypotheses MUST be revised and a new round begun — iteration continues until the goal is met.

### Candidate Mechanics for Round 6

The following mechanics are ordered by expected impact:

- **Candidate S (agent_v34) — In-transit fleet deduplication**: Before dispatching a fleet from source planet P to target T, sum all friendly fleets currently in transit to T. If `in_transit_to_T + P_send_size > target_projected_garrison + buffer`, reduce the send size to only cover the shortfall, or skip if already fully covered. Hypothesis: agent_v33 sends redundant full-attack fleets to the same target from multiple owned planets in the same turn, wasting ships that could have captured a second planet. This is especially common with the no-range-limit mechanic (from v30) and the single-sender coordination ancestry (from v15).

- **Candidate T (agent_v35) — Transit-adjusted fleet sizing**: When computing how many ships to send to enemy planet E, estimate E's garrison at fleet-arrival time as `E.ships + E.production × travel_turns` (using the current travel-time estimate). Send enough ships to defeat this projected garrison plus a buffer. Hypothesis: agent_v33 targets enemy planets at current garrison size; planets with positive production accumulate ships during transit, making the fleet insufficient on arrival. This is most impactful for medium-distance targets (travel time 10–30 turns).

- **Candidate U (agent_v36) — Threat-aware garrison floor**: When computing the garrison floor for owned planet P, use `max(GARRISON_FLOOR_FACTOR * P.production, max_incoming_enemy_fleet_size)` where max_incoming_enemy_fleet_size is the largest hostile fleet currently in transit to P. If no hostile fleet targets P, the floor reverts to the standard formula. Hypothesis: agent_v33 sometimes dispatches offensively from a planet that has an incoming enemy fleet, leaving it with too few ships to defend. The threat-aware floor prevents dispatch only from specifically threatened planets, avoiding the global defense trap that failed in Candidate I (reactive defense).

- **Candidate V (agent_v37) — Winning-state garrison reduction**: When `own_total / max(1, enemy_total) >= 2.0`, reduce `GARRISON_FLOOR_FACTOR` from 3 to 1. Revert to 3 when the ratio falls below 2.0. Hypothesis: when comfortably ahead, a 3× production garrison floor wastes ships that could finish the game. A 1× floor when winning by 2:1 frees ships for aggressive endgame closers without exposing the agent when the ratio is closer.

- **Combined (agent_v38)**: All mechanics from Candidates S–V that individually achieve ≥ 55% score vs agent_v33, stacked on agent_v33.

### Key Entities

- **Candidate Mechanic**: A single behavioral change tested in isolation; characterized by a hypothesis, agent file, and score vs agent_v33.
- **Combined Agent**: A new agent stacking all mechanics that passed ≥ 55% vs agent_v33; evaluated vs agent_v33 as the final gate.
- **Pass Threshold**: ≥ 55% score over 50 games vs agent_v33. Score = (wins + 0.5 × draws) / 50.
- **Promotion Gate**: ≥ 65% score for the combined agent over 50 games vs agent_v33.
- **Baseline Agent**: agent_v33 for all Round 6 candidate evaluations.
- **In-transit fleet**: A friendly fleet currently flying toward a target, not yet arrived; identified in the game observation as `Fleet` objects with `owner == my_id` and `destination == target`.
- **Projected garrison**: `target.ships + target.production × travel_turns` — the estimated ship count on a planet when the fleet arrives.
- **Garrison floor**: `max(GARRISON_FLOOR_FACTOR × production, threat_override)` — the minimum ships a source planet keeps before dispatching.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 4 candidate mechanics are individually evaluated with documented hypotheses, results, and conclusions.
- **SC-002**: At least one mechanic achieves ≥ 55% score vs agent_v33 over 50 games (score counts draws as 0.5).
- **SC-003**: A combined agent achieves ≥ 65% score vs agent_v33 over 50 games with 0 sun/OOB losses verified via `diagnose_v9.py`.
- **SC-004**: The README Agents table and Makefile are updated after each evaluation; the new best agent is bolded.
- **SC-005**: If SC-003 is not met in Round 6, a revised hypothesis set is produced before the feature is closed, enabling Round 7 to begin immediately.

## Assumptions

- agent_v33 (60% vs agent_v32 over 50 games, 0 sun/OOB losses) is the local self-play baseline for all Round 6 evaluations.
- 50 games (seeds 0–49) is the standard evaluation window for this round, increased from 20 to reduce variance with the production²-ROI agent that produces decisive (no-draw) outcomes.
- `eval.py` and `diagnose_v9.py` are not modified — all experimental changes are confined to new agent files.
- The leaderboard uses 4-player games; local self-play evaluations use 2-player. A local win-rate improvement does not guarantee leaderboard score improvement, but it is a necessary intermediate signal.
- In-transit fleet deduplication (Candidate S) requires access to the `fleets` list in the observation, which is documented in CONTEST.md. If the field format differs from expectations, the candidate will be adjusted or skipped.
- Transit-adjusted sizing (Candidate T) assumes enemy planets do not receive reinforcements during transit (only garrison growth from production). If enemies actively reinforce threatened planets, the buffer may still be insufficient — this is acceptable for a first implementation.
- Mechanics from prior rounds that failed are not retried unless the hypothesis changes substantially. Candidate I (reactive defense) failed at 16% vs v20 and 5% vs v32; it is not retried here.
- Agent file slots v34–v37 are reserved for Round 6 candidates; v38 is reserved for the combined agent.
