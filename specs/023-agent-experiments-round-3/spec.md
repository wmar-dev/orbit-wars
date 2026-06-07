# Feature Specification: Agent Experiments Round 3

**Feature Branch**: `023-agent-experiments-round-3`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Do another round of experiments"

## Clarifications

### Session 2026-06-06

- Q: What baseline should experiments be tested against — v60 (old) or v62 (current best)? → A: All experiments evaluated against v62 as the baseline control, not v60. SC-001/003 and FR-001/007 updated accordingly.
- Q: Should this round create a new agent file (agent_v63.py) or add toggles to v62? → A: Create `agent_v63.py` from v62 + all new experiments. v62 remains frozen as the baseline control. FR-002 updated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Evaluate Defense Interceptor (Priority: P1)

The agent detects incoming enemy fleets that will overpower their target planet's garrison before arrival, then preemptively dispatches a reinforcing fleet from the nearest allied planet to intercept. This experiment is already implemented and togglable in the v62 codebase (`DEFENSE_INTERCEPT_ENABLED = True`) but has not been independently evaluated.

**Why this priority**: The interceptor is the only unevaluated experiment inherited from v62. Its theory is sound (prevent preventable losses) and it requires zero development time to evaluate.

**Independent Test**: Copy v62 to `agent_v63.py`. Run a 50-game head-to-head eval: v63 with `DEFENSE_INTERCEPT_ENABLED=True` vs v63 with `DEFENSE_INTERCEPT_ENABLED=False` (all other toggles identical). Measure win rate and average garrison lost to enemy capture per game.

**Acceptance Scenarios**:

1. **Given** an enemy fleet is en route to an ally planet with garrison < fleet ships, **When** a nearby allied planet can reinforce before the fleet arrives, **Then** the agent dispatches a reinforcing fleet.
2. **Given** an enemy fleet is en route to a planet with sufficient garrison to survive, **When** the garrison-at-arrival exceeds the fleet size, **Then** the agent does NOT dispatch a wasteful intercept.
3. **Given** the intercept source planet would itself be left undefended, **When** sending intercept ships would drop its garrison below its threat-adjusted floor, **Then** the intercept is suppressed.
4. **Given** the intercept runs independently of other dispatch logic, **When** the intercept and normal greedy dispatch both target the same planet, **Then** ships are not double-counted or wasted.

---

### User Story 2 — Deeper / Wider Beam Search (Priority: P2)

The agent increases beam search depth from 10 to 15+ or beam width from 3 to 5+ to evaluate more candidate plans before committing. The slawekbiel opponent (0% win rate) likely uses a deeper search — 800ms on Kaggle hardware may support wider exploration with the current fast simulator.

**Why this priority**: The slawekbiel opponent exposes the current agent as tactically outclassed. Deeper search allows the agent to see further into the game tree and avoid short-term greedy traps. This is the most likely path to closing the slawekbiel gap.

**Independent Test**: In `agent_v63.py`, run 50-game evals comparing depth=15/20 and beam width=5 vs baseline v62 (depth=10, K=3). If depth=15 improves win rate vs slawekbiel, proceed to full eval. Monitor per-turn timing to ensure 800ms budget compliance.

**Acceptance Scenarios**:

1. **Given** the search depth is increased from 10 to 15, **When** running a 50-game eval vs v60, **Then** win rate is at least as high as the baseline depth=10 configuration.
2. **Given** the beam width is increased from 3 to 5, **When** running the same eval, **Then** timing stays under 800ms per-turn (p95 < 780ms on local hardware).
3. **Given** depth=15 is selected, **When** compared to the current depth=10, **Then** the agent does not regress on any opponent in the opponent sweep.
4. **Given** deeper search is deployed, **When** the agent faces slawekbiel, **Then** win rate improves from 0% to ≥20%.

---

### User Story 3 — Production-Weighted Beam Eval (Revised) (Priority: P3)

The beam search evaluation function accumulates production score over the simulation horizon rather than sampling only at the final state, but the previous attempt (v61 US3, discarded at 40%) had a bug: transit-weight was being accumulated every step before fleets arrived, inflating dispatch scores. A corrected version zeros out transit weight during cumulative steps and only counts production differential, then applies transit weight at the horizon.

**Why this priority**: The concept is sound (capture timing matters) and the v61 failure was a specific implementation bug, not a fundamental flaw. Fixing the weight accumulation approach may provide the anticipated 3-5pp improvement.

**Independent Test**: In `agent_v63.py`, run a 50-game eval with `WEIGHTED_EVAL_FIXED_ENABLED=True` vs baseline v62 (which has no weighted eval). Target: ≥52% win rate. If it passes, add to the combined configuration for a full combined test.

**Acceptance Scenarios**:

1. **Given** two candidate plans where one captures a planet at depth 3 and another at depth 9, **When** both achieve the same final production differential, **Then** the depth-3 plan scores higher.
2. **Given** the corrected weighted eval is used, **When** compared to the baseline horizon-only eval for unambiguous candidates, **Then** both evals rank the candidates in the same relative order (regression check).
3. **Given** the cumulative scoring path does NOT include transit-weight in intermediate steps, **When** a fleet is in transit for 9 of 10 simulation steps, **Then** it contributes transit-weight only in the final step, not all 9 intermediate steps.
4. **Given** the corrected eval passes the independent test, **When** combined with the best4 configuration, **Then** overall win rate vs v60 improves compared to best4 alone (66% → ≥70%).

---

### Edge Cases

- What happens when the interceptor and the normal greedy dispatch try to use the same source planet in the same turn? The `intercept_senders` set prevents double-use, but this could leave the greedy dispatch with fewer viable sources. Monitor dispatch count in interceptor-enabled vs disabled evals.
- What happens when deeper search hits the 800ms timeout more frequently? The beam search currently breaks early on timeout — deeper depth means fewer candidates may be evaluated. If timing is tight, reduce BEAM_K proportionally (e.g., K=2 at depth=15).
- What happens when the corrected weighted eval interacts with the existing EVAL_ENHANCED (planet count + ship count weights)? The enhanced eval adds its own scoring terms — ensure they compound correctly rather than competing.
- What happens when deeper search changes the relative ordering of beam candidates compared to depth=10? The greedy baseline is the same regardless of search depth — depth only affects the beam choice overlay. If depth=15 consistently makes worse decisions than depth=10, the deeper simulation may be introducing noise from the opponent model.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The DEFENSE_INTERCEPT_ENABLED experiment MUST be independently evaluated for win rate impact vs v62 (with DEFENSE_INTERCEPT toggled off) before being included or discarded in any combined configuration.
- **FR-002**: The search depth and beam width MUST be independently tunable via constants (`SEARCH_DEPTH`, `BEAM_K`) to allow systematic A/B testing.
- **FR-003**: Timing instrumentation MUST be added to report per-turn p50/p95/p99 timing when running eval, to verify 800ms budget compliance.
- **FR-004**: The corrected weighted eval MUST accumulate only production differential (`own_prod - opp_prod`) over intermediate steps, with transit weight applied only at the horizon (final step).
- **FR-005**: The corrected weighted eval MUST be independently togglable via a constant (`WEIGHTED_EVAL_FIXED_ENABLED`).
- **FR-006**: The slawekbiel opponent MUST be included in the opponent sweep for any configuration considered for submission.
- **FR-007**: All experiments MUST be evaluated against v62 (current best agent) as the baseline control, not v60. This ensures measured improvements are additive to the best known configuration. Each eval uses 50 games with --swap.

### Key Entities

- **Defense Interceptor**: A pre-pass in `_greedy_moves()` that scans enemy fleets angle-matched to allied planets, computes garrison-at-arrival, and dispatches a reinforcing fleet from the nearest safe allied source if the planet would be lost.
- **Search depth (`SEARCH_DEPTH`)**: Number of forward-simulation steps used by beam/MCTS/N-ply search to evaluate candidate plans. Currently 10.
- **Beam width (`BEAM_K`)**: Number of top-scoring target candidates considered per source planet for beam search alternatives. Currently 3.
- **Weighted eval**: A scoring function for beam search that accumulates per-step scores over the simulation horizon rather than taking a single snapshot at the end.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Defense interceptor evaluation yields win rate vs v62 (with DEFENSE_INTERCEPT toggled off as control) — if ≥52%, keep; if <50%, discard.
- **SC-002**: Deep search (depth≥15) completes within 800ms p99 on local hardware and improves win rate vs slawekbiel from 0% to ≥20%.
- **SC-003**: Corrected weighted eval achieves ≥54% vs v62 standalone (vs 40% for the buggy version).
- **SC-004**: Combined configuration (v62 + any passing experiments) improves win rate vs v62 over the current best4 baseline.
- **SC-005**: All experiment results are logged in `experiments/2026-06-06-experiments-round3.md` with win rates, sample counts, and conclusions.
- **SC-006**: Kaggle submission score after this round exceeds the current best (916.9).

## Assumptions

- All experiments are evaluated against v62 (the current best agent) as the baseline control, not v60. This ensures measured improvements are additive to the best known configuration.
- `agent_v63.py` is created as a copy of v62 serving as the experimental platform. v62 remains frozen as the baseline for all comparisons.
- The slawekbiel opponent's advantage comes from deeper search or better tactical reasoning, not from a fundamentally different architecture (e.g., neural net).
- The 800ms per-turn budget on Kaggle is similar to local timing; deeper depth will be tested with timing instrumentation before submission.
- The v62 best4 configuration (SPLINTER, EVAL_ENHANCED, OPPONENT_MODEL_V2, DYNAMIC_GARRISON) remains the baseline for combined tests, with new experiments added as toggles on top.
- The corrected weighted eval fix (zeroing transit weight in intermediate steps) addresses the root cause of the v61 failure and does not introduce a new bias in the opposite direction.
