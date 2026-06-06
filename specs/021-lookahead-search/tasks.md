# Tasks: Agent Lookahead Decision Search

**Input**: Design documents from `specs/021-lookahead-search/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: No test tasks — this feature is validated by win-rate evals against v58, not unit tests.

**Organization**: Tasks grouped by user story for independent implementation and validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent function scope, different sections)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create the skeleton file and experiment log.

- [X] T001 Create `agent_v60.py` at repo root with the full constant block at top (SEARCH_STRATEGY, SEARCH_DEPTH, TRANSIT_WEIGHT, SEARCH_TIMEOUT_MS, BEAM_K, MCTS_C, NPLY_BEAM_WIDTH) plus all existing constants copied from agent_v58.py; leave function bodies as `pass` stubs
- [X] T002 Create `experiments/2026-06-05-lookahead-search.md` with hypothesis/change/result/conclusion template sections for each algorithm variant (beam, mcts, nply)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core simulator and greedy baseline — required by all three user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Port `_SimPlanet`, `_SimFleet`, `_SimState` classes from `agent_v59_beam.py` into `agent_v60.py`; extend `_SimState.score()` to accept `transit_weight` parameter and add in-transit ships term: `score += transit_weight × (own_transit_ships - opp_transit_ships)` per data-model.md formula
- [X] T004 Port `_build_sim_state()` from `agent_v59_beam.py` into `agent_v60.py` (converts live observation into `_SimState`, resolving fleet ETAs from distance/speed)
- [X] T005 Extract greedy dispatch logic from `agent_v58.py agent()` body into a standalone `_greedy_moves(obs, planets, my_planets, targets, ...)` function in `agent_v60.py` that returns the standard `moves` list; this is the greedy baseline and fallback for all search strategies
- [X] T006 Implement the `_lookahead_search(greedy_moves, obs, ...)` dispatcher stub in `agent_v60.py` that reads `SEARCH_STRATEGY` and calls the appropriate search function (stubs for now); returns `greedy_moves` as fallback if strategy unknown
- [X] T007 Implement `agent(obs)` entry point in `agent_v60.py`: calls `_greedy_moves()`, then `_lookahead_search()`, returns result; verify `make test AGENT=agent_v60.py` passes (no crash, produces valid moves)

**Checkpoint**: `make test AGENT=agent_v60.py` passes — foundational layer ready.

---

## Phase 3: User Story 1 — Lookahead Beats Greedy Agent (Priority: P1) 🎯 MVP

**Goal**: Implement all three search strategies in a single agent file and identify which achieves ≥55% win rate vs v58.

**Independent Test**: `AGENT=agent_v60.py make eval` (vs main.py sanity check), then 50-game head-to-head eval for each strategy vs v58.

### Implementation

- [X] T008 [P] [US1] Implement `_gen_beam_candidates(my_planets, targets, greedy_moves, planet_map, ...)` in `agent_v60.py`: for each mine, compute top-BEAM_K targets by ROI; generate candidates by varying one mine's target at a time (M × (K-1) candidates) plus hold-all; return list of `(dispatches, moves)` pairs as per plan.md candidate generation design
- [X] T009 [US1] Implement `_beam_search(obs, greedy_moves, ...)` in `agent_v60.py`: iterate candidates from `_gen_beam_candidates`, copy sim state, apply dispatches, run SEARCH_DEPTH steps, score with `_SimState.score(TRANSIT_WEIGHT)`; track best score; return best moves; check wall clock before each candidate and return best-so-far if `SEARCH_TIMEOUT_MS` exceeded (depends on T008)
- [X] T010 [P] [US1] Implement `_mcts_rollout(state, player, depth)` in `agent_v60.py`: apply an action set, simulate `depth` turns using simplified greedy for both players (each mine dispatches to nearest non-owned planet with surplus, no orbit-lead), return terminal score with TRANSIT_WEIGHT
- [X] T011 [US1] Implement `_mcts_search(obs, greedy_moves, ...)` in `agent_v60.py`: dict-based UCB1 tree; each iteration — select node by UCB1, expand with sampled action (each mine samples uniformly from its top-BEAM_K targets), rollout via `_mcts_rollout`, backpropagate; run iterations until SEARCH_TIMEOUT_MS; return action with highest average score from root children (depends on T010)
- [X] T012 [P] [US1] Implement `_nply_search(obs, greedy_moves, ...)` in `agent_v60.py`: enumerate top-2 targets per mine; at each ply level keep only top-NPLY_BEAM_WIDTH branches by intermediate score (beam pruning); after SEARCH_DEPTH turns return first-turn actions of highest-scoring leaf; guard with wall-clock check and return greedy_moves on timeout
- [X] T013 [US1] Wire all three strategies into `_lookahead_search()` dispatcher in `agent_v60.py`: `"beam"` → `_beam_search()`, `"mcts"` → `_mcts_search()`, `"nply"` → `_nply_search()` (depends on T009, T011, T012)
- [X] T014 [US1] Smoke-test all three strategies locally: set SEARCH_STRATEGY to each value in turn, run `make test AGENT=agent_v60.py`; verify no timeouts, no crashes, moves are non-empty for a mid-game state
- [X] T015 [US1] Eval beam strategy: set `SEARCH_STRATEGY="beam"` in `agent_v60.py`, run `python eval.py h2h --agent0 agent_v60.py --agent1 agent_v58.py --games 50 --swap`; record win rate in `experiments/2026-06-05-lookahead-search.md`
- [X] T016 [US1] Eval MCTS strategy: set `SEARCH_STRATEGY="mcts"`, run 50-game eval vs v58, record win rate in experiment log (depends on T015 completing so file is ready)
- [X] T017 [US1] Eval N-ply strategy: set `SEARCH_STRATEGY="nply"`, run 50-game eval vs v58, record win rate in experiment log
- [X] T018 [US1] Document algorithm comparison in `experiments/2026-06-05-lookahead-search.md`: note best strategy, win rates for all three, and conclusion (proceed/tune/abandon for each)

**Checkpoint**: All three strategies evaluated vs v58. Best strategy identified. Experiment log updated.

---

## Phase 4: User Story 2 — Lookahead Depth Sensitivity Study (Priority: P2)

**Goal**: Determine the optimal SEARCH_DEPTH for the best-performing strategy from US1.

**Independent Test**: Each depth variant produces a win rate vs v58 over 20 games. At least one depth achieves ≥55%. No timeouts at any depth.

### Implementation

- [X] T019 [US2] Set SEARCH_STRATEGY to best algorithm from US1 in `agent_v60.py`; set SEARCH_DEPTH=5; run `python eval.py h2h --agent0 agent_v60.py --agent1 agent_v58.py --games 20 --swap`; record win rate and confirm no timeouts in `experiments/2026-06-05-lookahead-search.md`
- [X] T020 [US2] Set SEARCH_DEPTH=10; run 20-game eval vs v58; record win rate and timing in experiment log
- [X] T021 [US2] Set SEARCH_DEPTH=15; run 20-game eval vs v58; record win rate and timing in experiment log
- [X] T022 [US2] Set SEARCH_DEPTH=20; run 20-game eval vs v58; record win rate; if any turn exceeds 0.8s, note it and disqualify this depth
- [X] T023 [US2] Document depth sensitivity findings in `experiments/2026-06-05-lookahead-search.md`: rank depths by win rate, identify optimal depth (highest win rate with no timeout risk); set SEARCH_DEPTH to optimal value in `agent_v60.py`

**Checkpoint**: Optimal SEARCH_DEPTH selected and set in agent_v60.py. Experiment log updated.

---

## Phase 5: User Story 3 — Opponent Modeling Quality (Priority: P3)

**Goal**: Determine whether simulating the opponent's moves during rollout improves decision quality.

**Independent Test**: Opponent-model-on vs opponent-model-off at the best depth from US2, 20 games each vs v58.

### Implementation

- [X] T024 [US3] Add `OPPONENT_MODEL = False` constant to top of `agent_v60.py`; add simplified opponent dispatch to `_SimState.step()`: when `OPPONENT_MODEL=True`, after production and before fleet resolution, for each non-owned planet with owner≥0, if ships > floor, dispatch to nearest non-owned planet (simplified: no orbit-lead, just current position angle)
- [X] T025 [US3] Verify baseline: run 20-game eval of best config with `OPPONENT_MODEL=False` vs v58 (should match US2 result — serves as control group)
- [X] T026 [US3] Set `OPPONENT_MODEL=True`; run 20-game eval vs v58; record win rate; compare to T025 result
- [X] T027 [US3] Document opponent model comparison in `experiments/2026-06-05-lookahead-search.md`: which variant won, set `OPPONENT_MODEL` to better value in `agent_v60.py`

**Checkpoint**: Final agent_v60.py configuration locked (SEARCH_STRATEGY, SEARCH_DEPTH, OPPONENT_MODEL all set to best values).

---

## Phase 6: Polish & Submission

**Purpose**: Final validation, constitution compliance check, Kaggle submission.

- [X] T028 Verify `agent_v60.py` passes constitution pre-submission check: run `grep -n "^from \|^import " agent_v60.py | grep -v "kaggle_environments\|math\|time\|random\|copy"` and confirm empty output (no local module imports per Principle VI)
- [X] T029 Run final 50-game eval of locked config vs v58 for submission confidence: `python eval.py h2h --agent0 agent_v60.py --agent1 agent_v58.py --games 50 --swap`; require ≥50% win rate to proceed (per Principle VII, 95% confidence gate)
- [X] T030 [P] Update `README.md` agents table with agent_v60 strategy description and win rate vs v58; bold agent_v60 if it beats v58 by ≥55%
- [X] T031 [P] Update `Makefile` `AGENT` and `RENDER_AGENT` to point to `agent_v60.py` if it is the new best agent
- [ ] T032 Submit `agent_v60.py` manually to Kaggle; record submission in `SUBMISSIONS.md` with publicScore once available; update experiment log with Kaggle result

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion
- **US2 (Phase 4)**: Depends on Phase 3 (needs best algorithm from US1)
- **US3 (Phase 5)**: Depends on Phase 4 (needs best depth from US2)
- **Polish (Phase 6)**: Depends on Phase 5 (needs locked config)

### Within Phase 3 (US1)

```
T008 ─────────────────────────┐
T010 ──────────────────────┐  │
T012 ──────────┐           │  │
               ▼           ▼  ▼
              T011        T009
               │           │
               └────┬──────┘
                    ▼
                  T013 → T014 → T015 → T016 → T017 → T018
```

T008, T010, T012 can be implemented concurrently (different functions, no shared state).

### Parallel Opportunities

- T008, T010, T012 can be developed simultaneously (beam candidates, MCTS rollout, N-ply are independent functions)
- T030 and T031 (README + Makefile update) can run in parallel during Phase 6

---

## Parallel Example: User Story 1

```bash
# Implement search strategy internals concurrently (different functions):
Task T008: "_gen_beam_candidates() — alternative-target beam candidate generation"
Task T010: "_mcts_rollout() — simplified greedy rollout for MCTS"
Task T012: "_nply_search() — depth-limited exhaustive with beam pruning"

# Then wire up (sequential — depends on all three):
Task T013: "_lookahead_search() dispatcher"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T007) — **CRITICAL GATE**
3. Complete Phase 3: US1 — implement and compare all three strategies (T008–T018)
4. **STOP and VALIDATE**: Do any strategies achieve ≥55% vs v58?
5. If yes, proceed to depth study. If no, tune BEAM_K / MCTS_C / NPLY_BEAM_WIDTH before proceeding.

### Incremental Delivery

1. Setup + Foundational → `make test AGENT=agent_v60.py` passes
2. US1 (all three strategies) → Best algorithm identified
3. US2 (depth study) → Optimal depth set
4. US3 (opponent model) → Final config locked
5. Polish → Kaggle submission

### Tuning Guidance (if US1 ≤50% win rate)

- Beam search: increase BEAM_K from 3 to 5; add two-mine variation candidates
- MCTS: increase SEARCH_TIMEOUT_MS to use more budget; tune MCTS_C (try 0.7, 1.0, 2.0)
- N-ply: increase NPLY_BEAM_WIDTH; reduce min mine count threshold for N-ply activation
- All: tune TRANSIT_WEIGHT (try 0.05, 0.2, 0.5); tune SEARCH_DEPTH

---

## Notes

- All evals use `--swap` flag to alternate starting sides and reduce positional bias
- Record every eval result in `experiments/2026-06-05-lookahead-search.md` immediately after running (Principle IV)
- Never submit without ≥50% win rate in 50-game final eval (Principle V + VII)
- If all three strategies regress vs v58, experiment is still complete per FR-009 — document findings and conclude
- Each `SEARCH_STRATEGY` change requires editing the constant at the top of `agent_v60.py` and re-running eval
