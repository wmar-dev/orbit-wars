# Feature Specification: Experiments Round 6

**Feature Branch**: `029-experiments-round-6`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Do another round of experiments"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resolve Baseline Ambiguity (Priority: P1)

The project recently re-bolded `agent_v58` as "current best" after finding that the `agent_v58 → ... → agent_v65` improvement chain is non-transitive: `agent_v65` (≡`agent_v64`) loses to `agent_v58` 43.3% in a 30-game head-to-head. However, `agent_v60`'s own record states it beat `agent_v58` 54% (50 games) and scored higher on Kaggle (916.9 vs 851.0–880.7). These two facts are in tension — before forking new candidates, the project needs to know which agent (`agent_v58`, `agent_v60`, or `agent_v64`) is actually the strongest, so the round doesn't build on top of an agent that a sibling agent already beats.

**Why this priority**: Every other activity in this round forks from "the baseline." If the wrong agent is chosen as the fork point, the whole round's results are built on a weaker foundation and any "win" may not represent real progress.

**Independent Test**: Run pairwise 50-game `--swap` head-to-head evals among `agent_v58`, `agent_v60`, and `agent_v64`, producing a win-rate matrix. The agent with the strongest aggregate record becomes the "Round 6 baseline."

**Acceptance Scenarios**:

1. **Given** the three candidate agents (`agent_v58`, `agent_v60`, `agent_v64`), **When** each pairing is evaluated over 50 `--swap` games, **Then** a win-rate matrix covering all three pairings is produced and recorded.
2. **Given** the win-rate matrix, **When** the strongest agent is identified (best aggregate record, with at least one pairing won at ≥52%), **Then** that agent is designated the "Round 6 baseline" and the choice is documented with rationale.
3. **Given** the designated Round 6 baseline, **When** its recorded Kaggle score is compared against the other two agents' Kaggle scores in `SUBMISSIONS.md`, **Then** any contradiction (local h2h winner with a lower Kaggle score) is noted as a follow-up rather than blocking the round.

---

### User Story 2 - Replay-Informed Gap Analysis vs Top Local Opponent (Priority: P2)

The most recent replay analysis against `slawekbiel_agent` (2026-06-04, predating `agent_v58`'s multi-planet dispatch and the v59–v65 chain) showed a 0% win rate (0/7 games) with a median divergence turn of 8, driven by slow early expansion and lower mid-game dispatch frequency. Some of those findings were already folded into `agent_v58` (multi-planet dispatch) and the v59–v65 chain (dynamic garrison, early dispatch, weighted eval). A fresh replay analysis of the Round 6 baseline against `slawekbiel_agent` (or the strongest available local opponent) is needed to find what gaps remain now.

**Why this priority**: New candidate directions should target the current largest behavioral gap, not gaps that `agent_v58` or the discarded v59–v65 chain already addressed.

**Independent Test**: Generate at least 5 replays of the Round 6 baseline vs `slawekbiel_agent`, compute win rate, median divergence turn, and per-phase dispatch/planet-count/fleet-size metrics (matching the format of `experiments/2026-06-04-replay-analysis.md`), and document exactly 2 new candidate improvements with hypotheses and predicted effects.

**Acceptance Scenarios**:

1. **Given** at least 5 replays of the Round 6 baseline vs `slawekbiel_agent`, **When** behavioral metrics are computed in the established replay-analysis format, **Then** a report documents win rate, median divergence turn, and at least 2 named candidate directions with hypotheses and predicted effects.
2. **Given** the 2 candidate directions identified, **When** compared against mechanics already implemented or discarded across `agent_v57`–`agent_v66` (early dispatch, multi-planet dispatch, dynamic garrison, weighted eval, multi-source attack, fleet-size optimization, FFA adaptation), **Then** each new candidate is confirmed as distinct from those prior attempts.

---

### User Story 3 - Independently Test and Combine New Candidates (Priority: P3)

Following the established project pattern (Rounds 2–5), each candidate direction from User Story 2 is implemented as an independently-toggled change in a new agent file forked from the Round 6 baseline, evaluated head-to-head against that baseline, and combined into a single agent only if it individually passes.

**Why this priority**: This is the experiment itself — it depends on User Story 1 (which agent to fork from) and User Story 2 (what to try) being settled first.

**Independent Test**: For each of the 2 candidates, create a togglable implementation in a new agent file forked from the Round 6 baseline, run a 50-game `--swap` h2h eval vs the Round 6 baseline, and record the win rate. Combine all passing candidates (≥52% win rate) into one agent and run a confirmation 50-game eval vs the Round 6 baseline.

**Acceptance Scenarios**:

1. **Given** a new agent file forked from the Round 6 baseline with Candidate 1 toggled on, **When** evaluated over 50 `--swap` games vs the baseline, **Then** a win rate is recorded and compared against the 52% pass threshold.
2. **Given** a new agent file forked from the Round 6 baseline with Candidate 2 toggled on, **When** evaluated over 50 `--swap` games vs the baseline, **Then** a win rate is recorded and compared against the 52% pass threshold.
3. **Given** one or more candidates pass, **When** all passing candidates are combined into a single agent, **Then** a 50-game `--swap` eval vs the Round 6 baseline confirms the combined agent's win rate is ≥52% and per-turn timing stays within the 800ms budget.
4. **Given** zero candidates pass, **When** the round concludes, **Then** the Round 6 baseline remains the current best and the all-discarded result is documented per project convention (cf. Round 5).

---

### Edge Cases

- What happens if the User Story 1 round-robin produces a non-transitive cycle (e.g., `agent_v58` beats `agent_v64`, `agent_v64` beats `agent_v60`, and `agent_v60` beats `agent_v58`)? Use the agent with the highest recorded Kaggle leaderboard score among the cycle as a tiebreaker, and document the cycle for future investigation.
- What happens if `slawekbiel_agent` (or another top local opponent referenced in prior replay analyses) is no longer available locally? Fall back to the strongest currently-downloaded opponent, or to the runner-up from the User Story 1 round-robin, for replay generation.
- What happens if a candidate passes its individual 50-game eval but the combined agent fails the confirmation eval? Document which combination was tested, retain the best-performing single candidate as a standalone agent, and note the interaction effect for a future round.
- What happens if the Round 6 baseline (from User Story 1) differs from the agent currently referenced by `AGENT`/`RENDER_AGENT` in the Makefile? Update the Makefile and README to point at the new baseline before generating candidates, per the project's existing maintenance convention.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The round MUST determine a single "Round 6 baseline" agent via head-to-head evaluation among the agents implicated in the non-transitivity finding (at minimum `agent_v58` and `agent_v60`; `agent_v64` included as a third pairing), with each pairing evaluated over at least 50 `--swap` games.
- **FR-002**: The round MUST document the baseline decision — including the win-rate matrix and any non-transitive cycle found — before generating new candidates.
- **FR-003**: The round MUST generate and analyze at least 5 fresh replays of the Round 6 baseline vs the strongest available local opponent (`slawekbiel_agent` if available), following the established replay-analysis format (win rate, divergence turn, per-phase dispatch/planet/fleet-size metrics).
- **FR-004**: The round MUST identify exactly 2 new candidate tactical improvements from the fresh replay analysis, each with a stated hypothesis and predicted effect, and each confirmed as distinct from mechanics already adopted or discarded in prior rounds.
- **FR-005**: Each candidate MUST be implemented as an independently togglable constant in a new agent file forked from the Round 6 baseline.
- **FR-006**: Each candidate MUST be evaluated independently via a 50-game `--swap` head-to-head eval vs the Round 6 baseline before any combination is attempted.
- **FR-007**: Candidates achieving at least 52% win rate vs the Round 6 baseline MUST be combined into a single agent and re-evaluated via a 50-game `--swap` eval vs the Round 6 baseline.
- **FR-008**: All new agents produced in this round MUST remain within the 800ms per-turn time budget, with p99 per-turn timing under 100ms.
- **FR-009**: All results (baseline decision, replay analysis, per-candidate evals, combination result) MUST be documented in `experiments/` following the established naming and format conventions.
- **FR-010**: If the combined agent (or the single best candidate) beats the Round 6 baseline at ≥52% win rate over at least 50 games, the README Agents table MUST be updated with the new agent bolded as current best, and the Makefile's `AGENT`/`RENDER_AGENT` variables MUST point at it, per `CLAUDE.md`.
- **FR-011**: If no candidate beats the Round 6 baseline, the README Agents table MUST still be updated to record the Round 6 baseline determination from User Story 1 (in case it differs from the agent previously marked "current best"), and all discarded candidates MUST be documented with their measured win rates.

### Key Entities

- **Round 6 baseline**: The agent designated strongest via the User Story 1 round-robin; the fork point for all new candidates in this round.
- **Win-rate matrix**: Pairwise `--swap` head-to-head results among `agent_v58`, `agent_v60`, and `agent_v64`, used to resolve the non-transitivity finding from Round 5.
- **Replay analysis report**: A markdown document recording win rate, divergence turn, and per-phase behavioral metrics of the Round 6 baseline vs the strongest local opponent.
- **Candidate direction**: A hypothesis-driven, independently-toggled tactical change forked from the Round 6 baseline, targeting a gap identified in the replay analysis report.
- **Combined agent**: A new agent file incorporating every candidate direction that individually passed the 52% win-rate threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single Round 6 baseline agent is identified, with a documented win-rate matrix covering all pairings among `agent_v58`, `agent_v60`, and `agent_v64` (50 `--swap` games each).
- **SC-002**: A replay analysis report covering at least 5 games of the Round 6 baseline vs the strongest local opponent identifies the current median divergence turn and exactly 2 named candidate directions with hypotheses.
- **SC-003**: Each of the 2 candidates is evaluated independently over 50 `--swap` games vs the Round 6 baseline, with win rates recorded regardless of pass or fail.
- **SC-004**: If at least one candidate passes (≥52% win rate), a combined agent is produced and confirmed at ≥52% win rate vs the Round 6 baseline over 50 `--swap` games.
- **SC-005**: The round's resulting best agent (the Round 6 baseline if no candidate passes, or the combined/best candidate if one does) shows zero sun-collision or out-of-bounds losses across all evaluation games in this round, and maintains p99 per-turn timing under 100ms.
- **SC-006**: README.md's Agents table and the Makefile's `AGENT`/`RENDER_AGENT` variables reflect this round's outcome by the end of the round.

## Assumptions

- "Another round of experiments" continues the heuristic agent-improvement lineage (Rounds 1–5, specs `010`/`023`–`025`), not the RL training lineage (Rounds 6–8, specs `026`–`028`). RL training has failed to converge (0% win rate vs `agent_v64`) across three rounds, and the project has explicitly reverted to the heuristic `agent_v58` baseline "for the next round of experiments" per the most recent commit.
- `slawekbiel_agent`, or an equivalent top-performing downloaded opponent referenced in `experiments/2026-06-04-replay-analysis.md`, remains available locally for replay generation; if not, the opponent-download step is re-run before User Story 2.
- 52% win rate over 50 `--swap` games is the established pass threshold for individual candidates in this project, consistent with Rounds 2–5.
- The Round 6 baseline determined in User Story 1 may turn out to be `agent_v58` (i.e., no change from the current README claim) — in that case User Story 1's value is confirming the current state with a 3-way matrix rather than changing it.
- 2-player self-play results remain directionally valid for the 4-player Kaggle FFA scoring context, consistent with prior rounds' assumptions.
