# Tasks: Agent Experiments Round 3

**Input**: Design documents from `specs/023-agent-experiments-round-3/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not separately requested — eval is done via `uv run python eval.py h2h` (50 games, --swap per direction).

**Organization**: Tasks grouped by user story. All three modify `agent_v63.py` (copy of v62). US1 is already implemented (just needs eval). US2 and US3 require new code changes. US2 and US3 are independent of each other but both depend on Phase 1.

## Phase 1: Setup

**Purpose**: Create the experimental agent file and experiment log.

- [x] T001 Copy `agent_v62.py` to `agent_v63.py`; update the module docstring to describe the three round-3 experiments; add `WEIGHTED_EVAL_FIXED_ENABLED = True` toggle constant; set `DEFENSE_INTERCEPT_ENABLED = True` (preserved from v62)
- [x] T002 Create experiment log file `experiments/2026-06-06-experiments-round3.md` with hypothesis, change description, and placeholder rows for all three directions + combined results

**Checkpoint**: `agent_v63.py` exists, imports cleanly (`uv run python -c "import agent_v63"`), and produces identical output to v62 when `WEIGHTED_EVAL_FIXED_ENABLED=False`, `SEARCH_DEPTH=10`, `BEAM_K=3`, `DEFENSE_INTERCEPT_ENABLED` same as v62.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add timing instrumentation missing from the eval harness (FR-003).

**⚠️ CRITICAL**: Timing data is needed before any deep search (US2) evaluation can verify 800ms budget compliance.

- [x] T003 Add `--timing` flag to `eval.py` h2h subcommand: collect per-turn `time.perf_counter()` elapsed from the `t_start` already in the agent; report p50/p95/p99 timing across all turns of all games in the result summary

**Checkpoint**: `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v63.py --games 5 --timing` prints timing metrics (p50/p95/p99) alongside win rate.

---

## Phase 3: User Story 1 — Defense Interceptor Evaluation (Priority: P1) 🎯 MVP

**Goal**: Evaluate the already-implemented `DEFENSE_INTERCEPT_ENABLED` experiment to determine whether it improves win rate vs v62.

**Independent Test**: `DEFENSE_INTERCEPT_ENABLED=True` vs `DEFENSE_INTERCEPT_ENABLED=False` (all other toggles identical). Run 50-game eval. Target: ≥52% win rate.

### Implementation for User Story 1

- [x] T004 [US1] Set `DEFENSE_INTERCEPT_ENABLED = False` in `agent_v63.py`; run `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap` and record win rate in the experiment log under Direction 1 with `DEFENSE_INTERCEPT_ENABLED=True` restored after eval
- [x] T005 [US1] Set `DEFENSE_INTERCEPT_ENABLED = True` in `agent_v63.py`; run `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap` with intercept enabled; compare win rate to the disabled result; record conclusion (KEEP if ≥52%, DISCARD if <50%)

**Checkpoint**: US1 result recorded in experiment log. Decision made: keep or discard the interceptor.

---

## Phase 4: User Story 2 — Deeper / Wider Beam Search (Priority: P2)

**Goal**: Increase beam search depth from 10 to 15+ and/or beam width from 3 to 5+ to improve tactical play against strong opponents like slawekbiel (0% win rate).

**Independent Test**: `SEARCH_DEPTH=15, BEAM_K=3` vs v62 (depth=10, K=3). 50-game eval. Target: ≥52% win rate vs v62, ≥20% vs slawekbiel. Verify timing p95 < 780ms.

### Implementation for User Story 2

- [x] T006 [US2] Set `SEARCH_DEPTH = 15` in `agent_v63.py`; run `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap --timing`; record win rate and p95/p99 timing in experiment log under Direction 2
- [x] T007 [US2] If T006 timing exceeds p95 < 780ms, test `SEARCH_DEPTH=15, BEAM_K=2` instead and re-eval; if timing is within budget, test `SEARCH_DEPTH=20, BEAM_K=3` and record timing
- [ ] T008 [US2] SKIPPED — all variants failed (40–44%, all below 50%). No best-performing config to sweep.

**Checkpoint**: US2 result recorded. Best depth/width chosen. slawekbiel win rate measured.

---

## Phase 5: User Story 3 — Production-Weighted Beam Eval (Priority: P3)

**Goal**: Re-implement the production-weighted beam eval with correct transit-weight handling (accumulate production differential turn-by-turn, apply transit weight at horizon only).

**Independent Test**: `WEIGHTED_EVAL_FIXED_ENABLED=True` vs v62 (no weighted eval). 50-game eval. Target: ≥52% win rate.

### Implementation for User Story 3

- [x] T009 [US3] In `agent_v63.py`, locate the `_beam_search()` function candidate evaluation loop (around line 798 in v62). Replace the current single `state.score()` call with cumulative scoring when `WEIGHTED_EVAL_FIXED_ENABLED`: initialize `score = 0.0`, inside the step loop add `score += (own_prod - opp_prod)` each step, then after the loop apply transit weight `score += TRANSIT_WEIGHT * (own_transit - opp_transit)` plus any enhanced eval terms (preserve `EVAL_ENHANCED_ENABLED` logic at the horizon only)
- [x] T010 [US3] Run unit sanity check: manually verify that a depth-3 capture candidate scores higher than a depth-9 capture candidate with identical final state (by temporarily adding debug print to `_beam_search` and running a single game with `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 1 --verbose`)
- [x] T011 [US3] Set `WEIGHTED_EVAL_FIXED_ENABLED=True`, `DEFENSE_INTERCEPT_ENABLED` at v62 default, `SEARCH_DEPTH=10`, `BEAM_K=3`; run `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap` and record win rate in experiment log under Direction 3

**Checkpoint**: US3 result recorded. Decision made: keep or discard the weighted eval. ✅ KEEP — 52% vs v62 (up from 40% buggy)

---

## Phase 6: Polish & Combination

**Purpose**: Combine all passing directions, run final eval, record results, and prepare for Kaggle submission if threshold is met.

- [x] T012 Set all passing toggles (from US1, US2, US3 decisions) to `True` in `agent_v63.py`; set any failing to `False` with an explanatory comment
- [x] T013 Run `uv run python eval.py h2h --agent0 agent_v63.py --agent1 agent_v62.py --games 50 --swap` with the combined configuration; record combined win rate in experiment log
- [x] T014 Run `uv run python eval.py opponents --agent agent_v63.py --games 20` with the combined configuration; record full opponent sweep table including slawekbiel win rate
- [x] T015 Record conclusion for each direction in `experiments/2026-06-06-experiments-round3.md`: direction result (keep/discard), combined win rate, opponent sweep table, and whether the config beats v62 above statistical noise
- [x] T016 Update `Makefile` `AGENT` variable to point to `agent_v63.py` if combined win rate > 50% vs v62
- [x] T017 [P] Update `README.md` Agents table to add `agent_v63.py` row with win rate vs v62; bold it if it beats v62
- [ ] T018 SKIPPED — combined win rate 52% is not > 52% threshold. Submission deferred.

**Checkpoint**: Experiment log complete. README and Makefile updated. Submission made (if threshold met).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001–T002 complete)
- **US1 (Phase 3)**: Depends on Phase 1 only (no eval timing instrumentation needed for interceptor)
- **US2 (Phase 4)**: Depends on Phase 1 AND Phase 2 (timing instrumentation required for timing verification)
- **US3 (Phase 5)**: Depends on Phase 1 only (no timing instrumentation needed for eval)
- **Polish (Phase 6)**: Depends on all three direction evals recorded

### User Story Dependencies

- US1 (P1) and US3 (P3) have no dependency on Phase 2 — they can start immediately after Phase 1
- US2 (P2) depends on Phase 2 (timing instrumentation) — start after T003
- US1, US2, and US3 are otherwise independent (different constants/functions in the same file)
- When running sequentially: US1 → US2 → US3 is natural (priority order)

### Within Each User Story

- Implementation tasks must run sequentially (each task builds on the previous)
- Eval task (last task per story) must run after all implementation tasks in that story

### Parallel Opportunities

- T001 and T002 (Phase 1) are sequential
- T003 (Phase 2) is sequential
- US1 (Phase 3) and US3 (Phase 5) can run in parallel if staffing allows (they modify different constants/functions)
- T016 and T017 (Phase 6) can run in parallel
- US1 eval and US3 implementation can overlap (different toggles)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 3: US1 defense interceptor eval (T004–T005)
3. **STOP and VALIDATE**: Interceptor eval result — KEEP or DISCARD
4. Proceed to US2 and/or US3 based on priority

### Incremental Delivery

1. Phase 1 → agent_v63.py and experiment log created
2. Phase 2 → timing instrumentation added
3. US1 → interceptor evaluated → decision made
4. US2 → deep search depth evaluated → decision made
5. US3 → weighted eval implemented and evaluated → decision made
6. Combination → combined eval → opponent sweep → submission if passing

### Important Notes

- US1 requires NO code changes — the interceptor is already implemented in v62 (copied to v63 in T001). The eval is toggling it off for the control run.
- US2 requires only changing `SEARCH_DEPTH` / `BEAM_K` constants — no algorithmic changes.
- US3 requires a structural change to `_beam_search()` evaluation loop — this is the only new code in this round.
- All evals use `--swap` for fairness.
- Record all results in the experiment log immediately after each eval completes.
