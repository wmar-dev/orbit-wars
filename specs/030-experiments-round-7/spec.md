# Feature Specification: Experiments Round 7

**Feature Branch**: `030-experiments-round-7`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Do another round of experiments with goal of improving the agent as much as possible."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish a Strong, Loadable Benchmark Opponent (Priority: P1)

The single biggest methodological weakness in Round 6 was the benchmark opponent. The established toughest local opponent (`opponent_agents/slawekbiel_agent.py`, historically 0/7 vs our agent) could not be loaded — it imports `torch`, which has no wheel for this environment's Python 3.14 and is absent from `pyproject.toml`/`uv.lock`. Round 6 fell back to `agent_v60` for replay generation, but `agent_v64` already beats `agent_v60` 80% (4/1), so the resulting replays gave almost no signal about real weaknesses. Before doing any gap analysis, Round 7 needs a benchmark opponent that (a) actually loads in this environment and (b) is genuinely challenging for `agent_v64` — otherwise the round repeats Round 6's mistake of analyzing games we already dominate.

**Why this priority**: Every candidate direction this round comes from analyzing `agent_v64`'s losses/struggles against the benchmark opponent. If the benchmark is one we already crush, the analysis surfaces noise instead of real gaps, and the round produces no improvement (exactly what happened in Round 6).

**Independent Test**: Run `agent_v64` head-to-head over at least 20 `--swap` games against each loadable opponent in `opponent_agents/` (and against the strongest prior-lineage agents `agent_v58`/`agent_v60` as internal sparring), producing a win-rate table. Optionally attempt to make `slawekbiel_agent` loadable (install `torch`, or stub the dependency). The opponent against which `agent_v64` has the **lowest** win rate becomes the "Round 7 benchmark opponent."

**Acceptance Scenarios**:

1. **Given** the set of downloaded opponents in `opponent_agents/`, **When** each is loaded under the local eval harness, **Then** opponents that fail to import (e.g., missing `torch`) are recorded, and a one-time attempt to make `slawekbiel_agent` loadable is made and its outcome documented.
2. **Given** every loadable opponent, **When** `agent_v64` plays at least 20 `--swap` games against each, **Then** a win-rate table is produced and the opponent yielding `agent_v64`'s lowest win rate is designated the "Round 7 benchmark opponent."
3. **Given** the designated benchmark opponent, **When** its `agent_v64` win rate is below 65%, **Then** it is accepted as a useful signal source; if every loadable opponent yields ≥65%, the lowest-win-rate opponent is still used but the round notes that local opponents may be saturated and self-play stress (vs `agent_v58`/`agent_v60`) should supplement the analysis.

---

### User Story 2 - Replay-Informed Gap Analysis vs the Benchmark Opponent (Priority: P2)

With a genuinely challenging benchmark opponent in hand, generate fresh replays of `agent_v64` against it and run the `analyze-replay` skill to surface where `agent_v64` actually loses or stalls. This round must produce candidate directions that are distinct from everything already tried in `agent_v57`–`agent_v67`, and should incorporate the two explicit follow-up leads recorded at the end of Round 6: (a) a *local, per-planet, threat-detection-based* garrison adjustment (Round 6's *global* ship-ratio version was a wash at 48%), and (b) the affordable-fallback idea only if the interaction with `MULTI_TURN_PLAN_ENABLED` beam search is first isolated (Round 6's version regressed to 6% by short-circuiting the lookahead's deliberate "wait and accumulate" choice).

**Why this priority**: Candidate quality is the binding constraint on this round's success. Round 6's two candidates failed partly because they re-derived ideas adjacent to already-discarded mechanics; Round 7's candidates must target a real, currently-unaddressed gap and must respect the known interaction traps.

**Independent Test**: Generate at least 5 replays of `agent_v64` vs the Round 7 benchmark opponent, compute win rate, median divergence turn, and per-phase dispatch/planet-count/fleet-size metrics (matching `experiments/2026-06-13-replay-analysis.md`'s format), and document 2–3 new candidate improvements, each with a hypothesis, predicted effect, risk, and an explicit novelty check against `agent_v57`–`agent_v67`.

**Acceptance Scenarios**:

1. **Given** at least 5 replays of `agent_v64` vs the benchmark opponent, **When** behavioral metrics are computed in the established replay-analysis format, **Then** a report documents win rate, median divergence turn, the decisive divergence window, and 2–3 named candidate directions each with hypothesis, predicted effect, and risk.
2. **Given** the candidate directions, **When** each is checked against mechanics already adopted or discarded across `agent_v57`–`agent_v67` (early/multi-planet/splinter dispatch, dynamic garrison, weighted beam eval, multi-turn plan skip, multi-source attacks, fleet-size convergence, FFA adaptation, endgame focus, affordable fallback, global relative-strength garrison scaling), **Then** each new candidate is confirmed distinct, and any candidate adjacent to a discarded one explicitly states how it avoids the prior failure mode.

---

### User Story 3 - Independently Test and Combine New Candidates (Priority: P3)

Following the established project pattern (Rounds 2–6), each candidate direction from User Story 2 is implemented as an independently-toggled change in a new agent file (`agent_v68.py`) forked from `agent_v64`, evaluated head-to-head against `agent_v64`, and combined into a single configuration only if it individually passes the threshold. Passing candidates are also re-checked against the Round 7 benchmark opponent to confirm the local-self-play win translates to a tougher opponent.

**Why this priority**: This is the experiment itself — it depends on User Story 1 (a credible opponent) and User Story 2 (what to try) being settled first.

**Independent Test**: For each candidate, create a togglable implementation in `agent_v68.py`, run a 50-game `--swap` h2h eval vs `agent_v64`, and record the win rate. Combine all passing candidates (≥52% win rate) into one configuration, run a confirmation 50-game `--swap` eval vs `agent_v64`, and run the resulting best configuration vs the Round 7 benchmark opponent to confirm it does not regress there.

**Acceptance Scenarios**:

1. **Given** `agent_v68.py` forked from `agent_v64` with one candidate toggled on, **When** evaluated over 50 `--swap` games vs `agent_v64`, **Then** a win rate is recorded and compared against the 52% pass threshold.
2. **Given** all candidates evaluated independently, **When** one or more pass (≥52%), **Then** all passing candidates are combined into a single configuration and a 50-game `--swap` eval vs `agent_v64` confirms the combined win rate is ≥52% with per-turn timing within the 800ms budget (p99 < 100ms).
3. **Given** the round's resulting best configuration (combined, single best candidate, or `agent_v64` itself if all fail), **When** it plays at least 30 `--swap` games vs the Round 7 benchmark opponent, **Then** its win rate vs that opponent is recorded and is no worse than `agent_v64`'s baseline win rate vs the same opponent.
4. **Given** zero candidates pass, **When** the round concludes, **Then** `agent_v64` remains the current best and the all-discarded result is documented per project convention (cf. Rounds 5 and 6).

---

### Edge Cases

- What happens if `torch` cannot be installed for Python 3.14 and `slawekbiel_agent` stays unloadable? Proceed with the strongest loadable opponent from the User Story 1 round-robin; document the unresolved `slawekbiel` dependency as a known limitation and a follow-up (e.g., pin a Python version with torch wheels in a future round).
- What happens if `agent_v64` beats every loadable opponent at ≥65%, leaving no genuinely hard benchmark? Use the lowest-win-rate opponent anyway, and supplement the gap analysis with self-play replays vs `agent_v58`/`agent_v60` to surface intra-lineage weaknesses; note the local-opponent saturation explicitly.
- What happens if a candidate passes its 50-game eval vs `agent_v64` but regresses against the benchmark opponent (Acceptance Scenario 3 fails)? Document the discrepancy, prefer the configuration that does not regress against the tougher opponent, and flag the self-play-vs-benchmark divergence for a future round.
- What happens if a candidate passes individually but the combination fails the confirmation eval? Document which combination was tested, retain the best single passing candidate as the round's output, and note the interaction effect.
- What happens if a candidate is adjacent to a Round 6 discard (affordable fallback, global garrison scaling)? It MUST first demonstrate it avoids the documented failure mode (e.g., the affordable-fallback variant must isolate or respect the `MULTI_TURN_PLAN_ENABLED` "wait and accumulate" choice) before being counted as a distinct candidate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The round MUST establish a "Round 7 benchmark opponent" by evaluating `agent_v64` over at least 20 `--swap` games against every loadable opponent in `opponent_agents/`, and selecting the opponent against which `agent_v64` has the lowest win rate.
- **FR-002**: The round MUST make a documented one-time attempt to render `slawekbiel_agent` loadable (install `torch` or stub its import); if unsuccessful, the failure and the chosen fallback opponent MUST be recorded.
- **FR-003**: The round MUST generate and analyze at least 5 fresh replays of `agent_v64` vs the Round 7 benchmark opponent, following the established replay-analysis format (win rate, divergence turn, decisive divergence window, per-phase dispatch/planet/fleet-size metrics).
- **FR-004**: The round MUST identify 2–3 new candidate tactical improvements from the replay analysis, each with a stated hypothesis, predicted effect, and risk, and each confirmed distinct from mechanics already adopted or discarded across `agent_v57`–`agent_v67`.
- **FR-005**: Any candidate adjacent to a Round 6 discard (affordable fallback, global relative-strength garrison scaling) MUST explicitly document how it avoids the prior failure mode before being implemented.
- **FR-006**: Each candidate MUST be implemented as an independently togglable constant in `agent_v68.py`, forked from `agent_v64.py`, leaving `agent_v64.py` unmodified.
- **FR-007**: Each candidate MUST be evaluated independently via a 50-game `--swap` head-to-head eval vs `agent_v64` before any combination is attempted.
- **FR-008**: Candidates achieving at least 52% win rate vs `agent_v64` MUST be combined into a single configuration and re-evaluated via a 50-game `--swap` eval vs `agent_v64`.
- **FR-009**: The round's resulting best configuration MUST be evaluated over at least 30 `--swap` games vs the Round 7 benchmark opponent, and its win rate there compared against `agent_v64`'s baseline win rate vs the same opponent.
- **FR-010**: All new agents produced in this round MUST remain within the 800ms per-turn time budget, with p99 per-turn timing under 100ms.
- **FR-011**: All results (benchmark-opponent selection, replay analysis, per-candidate evals, combination result, benchmark re-check) MUST be documented in `experiments/` following the established naming and format conventions.
- **FR-012**: If the resulting best configuration beats `agent_v64` at ≥52% win rate over at least 50 games without regressing against the benchmark opponent, the README Agents table MUST be updated with the new agent bolded as current best, and the Makefile's `AGENT`/`RENDER_AGENT` variables MUST point at it, per `CLAUDE.md`.
- **FR-013**: If no candidate beats `agent_v64`, the README Agents table MUST record `agent_v68` as a discarded round (toggles default off, `v68 ≡ v64`), `agent_v64` MUST remain bolded as current best, and all discarded candidates MUST be documented with their measured win rates.

### Key Entities

- **Round 7 benchmark opponent**: The loadable opponent against which `agent_v64` has the lowest measured win rate; the source of all replay-driven gap analysis this round.
- **Opponent win-rate table**: `agent_v64`'s win rate (≥20 `--swap` games) against each loadable opponent plus `agent_v58`/`agent_v60`, used to select the benchmark opponent and detect local-opponent saturation.
- **Replay analysis report**: A markdown document recording win rate, divergence turn, decisive divergence window, and per-phase behavioral metrics of `agent_v64` vs the benchmark opponent, ending in 2–3 candidate directions.
- **Candidate direction**: A hypothesis-driven, independently-toggled tactical change forked from `agent_v64`, targeting a gap identified in the replay analysis and confirmed distinct from prior rounds.
- **Combined configuration**: `agent_v68.py` with every candidate that individually passed the 52% win-rate threshold enabled together.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Round 7 benchmark opponent is selected, backed by a documented win-rate table of `agent_v64` (≥20 `--swap` games) vs every loadable opponent, with the `slawekbiel` loadability attempt recorded.
- **SC-002**: A replay analysis report covering at least 5 games of `agent_v64` vs the benchmark opponent identifies the decisive divergence window and 2–3 named candidate directions, each with hypothesis, predicted effect, and risk.
- **SC-003**: Each candidate is evaluated independently over 50 `--swap` games vs `agent_v64`, with win rates recorded regardless of pass or fail.
- **SC-004**: If at least one candidate passes (≥52%), a combined configuration is produced and confirmed at ≥52% win rate vs `agent_v64` over 50 `--swap` games.
- **SC-005**: The round's resulting best configuration is measured over ≥30 `--swap` games vs the benchmark opponent and does not regress below `agent_v64`'s baseline win rate vs that opponent.
- **SC-006**: The round's resulting best agent shows zero sun-collision or out-of-bounds losses across all evaluation games, and maintains p99 per-turn timing under 100ms.
- **SC-007**: README.md's Agents table and the Makefile's `AGENT`/`RENDER_AGENT` variables reflect this round's outcome by the end of the round.

## Assumptions

- "Another round of experiments" continues the heuristic agent-improvement lineage (Rounds 1–6), not the RL training lineage (specs `026`–`028`), which failed to converge (0% win rate vs `agent_v64`) across three rounds. The current best, `agent_v64`, is the fork point.
- The bottleneck on Round 6's outcome was opponent quality, not candidate-testing rigor; Round 7's P1 story directly addresses that by selecting the hardest *loadable* opponent rather than defaulting to an already-beaten one.
- `torch` likely cannot be installed for this environment's Python 3.14 (no wheel), so `slawekbiel_agent` may remain unloadable; the round is designed to succeed using the strongest loadable opponent regardless.
- 52% win rate over 50 `--swap` games is the established pass threshold for individual candidates, consistent with Rounds 2–6.
- 2-player self-play results remain directionally valid for the 4-player Kaggle FFA scoring context, consistent with prior rounds; the benchmark-opponent re-check (FR-009) is added this round to partially hedge that assumption.
- Any Kaggle submission happens manually and only after local evals confirm an improvement, per the project constitution (Principles III and IV).
