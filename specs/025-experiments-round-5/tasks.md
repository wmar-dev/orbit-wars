---
description: "Task list for experiments round 5 implementation"
---

# Tasks: Experiments Round 5

**Input**: Design documents from `/specs/025-experiments-round-5/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each experiment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different functions, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P2, US3=P3)
- Include exact file paths and line references

## Path Conventions

- **Single file agent**: `agent_v65.py` at repository root
- **Experiment log**: `experiments/2026-06-06-experiments-round5.md`
- **Config**: `Makefile` (update AGENT variable)

---

## Phase 1: Setup

**Purpose**: Create agent_v65.py from frozen v64 baseline, add experiment toggle constants

- [ ] T001 Create agent_v65.py by copying agent_v64.py
- [ ] T002 Update docstring header in agent_v65.py to reflect round 5 experiments
- [ ] T003 Add three new toggle constants (MULTI_SOURCE_ENABLED, FLEET_SIZE_OPT_ENABLED, FFA_ADAPT_ENABLED) after the v64 toggle section in agent_v65.py
- [ ] T004 [P] Add _count_opponents helper function before _greedy_moves in agent_v65.py

---

## Phase 2: Foundational (No blocking prerequisites — all exp independent)

**Purpose**: Each experiment is independently togglable and modifies different functions. No shared prerequisites.

---

## Phase 3: User Story 1 — Multi-Source Coordinated Attack (Priority: P1)

**Goal**: Generate beam search candidates where 2+ source planets target the same enemy planet simultaneously, enabling coordinated multi-prong attacks that the current single-source swap cannot produce.

**Independent Test**: Run `make selfplay AGENT1=agent_v65.py AGENT2=agent_v64.py GAMES=50 SWAP=true` with only MULTI_SOURCE_ENABLED=True (others False). Expect ≥52% win rate vs v64.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Add _build_target_to_sources_map helper after _compute_top_k_targets in agent_v65.py
- [ ] T006 [US1] Add multi-source candidate generation block inside _gen_beam_candidates (before the empty-dispatch fallback) in agent_v65.py, gated by MULTI_SOURCE_ENABLED

**Implementation Detail**: See research.md "Target → Source Mapping" section and quickstart.md Step 3 for exact algorithm.

**Checkpoint**: P1 should be testable independently of P2/P3. Run 50-game eval vs v64 with only MULTI_SOURCE_ENABLED=True.

---

## Phase 4: User Story 2 — Fleet-Size-Optimized Dispatch (Priority: P2)

**Goal**: Fix the single-correction inaccuracy in `_enemy_fleet_size` by iterating until convergence (max 5 iterations). For distant high-production targets, optionally oversend 1.2–1.5× to benefit from fleet speed scaling. Also fix neutral capture sizing (currently ignores production during transit).

**Independent Test**: Run `make selfplay AGENT1=agent_v65.py AGENT2=agent_v64.py GAMES=50 SWAP=true` with only FLEET_SIZE_OPT_ENABLED=True (others False). Expect ≥52% win rate vs v64.

### Implementation for User Story 2

- [ ] T007 [US1,US2] Add fleet_speed cache dict (optional optimization) near fleet_speed function in agent_v65.py
- [ ] T008 [US2] Replace _enemy_fleet_size body with iterative convergence loop (gated by FLEET_SIZE_OPT_ENABLED) in agent_v65.py
- [ ] T009 [US2] Add oversend logic at end of _enemy_fleet_size: apply 1.2–1.5× multiplier when target.production ≥ 8 and distance > 40 in agent_v65.py
- [ ] T010 [US2] Fix neutral capture sizing in _greedy_moves (line ~672 in v64): replace `ships_needed = best_target.ships + 1` with production-aware formula gated by FLEET_SIZE_OPT_ENABLED in agent_v65.py

**Implementation Detail**: See research.md "Fleet-Size-Optimized Dispatch" and quickstart.md Step 4 for exact code.

**Checkpoint**: P2 should be testable independently of P1/P3. Run 50-game eval vs v64 with only FLEET_SIZE_OPT_ENABLED=True.

---

## Phase 5: User Story 3 — 4-Player State Adaptation (Priority: P3)

**Goal**: Adjust garrison floor factor and splinter window based on number of surviving opponents. Higher garrisons (1.2×) when 3 opponents alive (4-player FFA), lower garrisons (0.8×) when 1 opponent (endgame).

**Independent Test**: Run `make selfplay AGENT1=agent_v65.py AGENT2=agent_v64.py GAMES=50 SWAP=true` with only FFA_ADAPT_ENABLED=True (others False). Expect ≥52% win rate vs v64. Also run 4-player eval: `python -c "from kaggle_environments import make; env=make('orbit_wars', debug=True); env.run(['agent_v65.py','agent_v64.py','agent_v64.py','agent_v64.py']); scores=[s.reward for s in env.steps[-1]]; print(f'v65: {scores[0]} / v64 avg: {sum(scores[1:])/3:.1f}')"` and verify v65's score is higher.

### Implementation for User Story 3

- [ ] T011 [US3] Modify _greedy_moves garrison floor computation to apply gff_mult based on opponent_count (gated by FFA_ADAPT_ENABLED) in agent_v65.py
- [ ] T012 [US3] Modify _greedy_moves SPLINTER_WINDOW reference to use adapted splinter_window value (gated by FFA_ADAPT_ENABLED) in agent_v65.py
- [ ] T013 [US3] Wire _count_opponents into _greedy_moves: compute opponent_count once at start of dispatch loop in agent_v65.py

**Implementation Detail**: See research.md "4-Player State Adaptation" and quickstart.md Step 5 for exact parameter values.

**Checkpoint**: P3 should be testable independently of P1/P2. Run 50-game eval vs v64 with only FFA_ADAPT_ENABLED=True.

---

## Phase 6: Combined Evaluation

**Purpose**: Enable all passing experiments simultaneously and re-evaluate vs v64 baseline.

- [ ] T014 Set all three toggles (MULTI_SOURCE_ENABLED, FLEET_SIZE_OPT_ENABLED, FFA_ADAPT_ENABLED) to True in agent_v65.py (only include experiments that passed their individual evals)
- [ ] T015 Run combined 50-game eval vs v64 with --swap: record win rate, per-turn timing
- [ ] T016 Run 4-player eval: v65 vs 3 copies of v64, record average scores
- [ ] T017 Update Makefile AGENT variable to point to agent_v65.py
- [ ] T018 Write experiment log in experiments/2026-06-06-experiments-round5.md with hypothesis, change, results, and conclusion for each experiment + combined

---

## Phase 7: Polish & Cleanup

- [ ] T019 Verify all three discarded experiments from v64 have their toggles set to False (OPPONENT_MODEL_V3_ENABLED, PHASE_DETECTION_ENABLED)
- [ ] T020 Run lint/typecheck: `flake8 agent_v65.py` or `python -m py_compile agent_v65.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **User Stories (Phase 3-5)**: All depend on Phase 1 completion only. No cross-story dependencies.
  - P1 (US1): T005 → T006
  - P2 (US2): T007 → T008 → T009 → T010
  - P3 (US3): T011 ≡ T012 ≡ T013 (parallel within story)
- **Combined (Phase 6)**: Depends on all three user stories
- **Polish (Phase 7)**: Depends on Phase 6

### User Story Dependencies

- **US1 (P1)**: No dependency on US2 or US3
- **US2 (P2)**: No dependency on US1 or US3
- **US3 (P3)**: No dependency on US1 or US2

### Within Each User Story

- Models/helpers before main logic
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 T001-T004**: T004 can run in parallel with T001-T003 (different sections of code)
- **Phase 3-5 (User Stories)**: All three stories can run in parallel since they modify DIFFERENT functions in the same file:
  - US1: _build_target_to_sources_map (new), _gen_beam_candidates (modify)
  - US2: _enemy_fleet_size (modify), _greedy_moves neutral section (modify)
  - US3: _greedy_moves gff section (modify), SPLINTER_WINDOW ref (modify), _count_opponents (already T004)
- **Phase 6**: All eval tasks can run in parallel with writing the experiment log

---

## Parallel Example: User Story 1

```bash
# Launch both P1 tasks in parallel:
Task: "Add _build_target_to_sources_map helper" -> modifies agent_v65.py (new function)
Task: "Add multi-source candidate generation in _gen_beam_candidates" -> modifies agent_v65.py (existing function)
```

## Parallel Example: All Three User Stories

```bash
# All three US's can run in parallel (different functions):
Task: "[US1] Add multi-source beam candidates" (agent_v65.py: _gen_beam_candidates)
Task: "[US2] Iterative fleet size convergence" (agent_v65.py: _enemy_fleet_size)
Task: "[US3] 4-player state adaptation" (agent_v65.py: _greedy_moves)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 3: User Story 1 (T005-T006)
3. **STOP and VALIDATE**: Run 50-game eval vs v64
4. If P1 passes (≥52%): Keep, proceed to P2
5. If P1 fails (<50%): Set toggle to False, proceed to P2

### Incremental Delivery

1. Phase 1: Setup complete → agent_v65.py ready
2. Phase 3: Add P1 → Test → Keep/Discard
3. Phase 4: Add P2 → Test → Keep/Discard
4. Phase 5: Add P3 → Test → Keep/Discard
5. Phase 6: Combine kept experiments → Final eval
6. Phase 7: Polish → Agent v65 ready

### Parallel Strategy

All three user stories can be implemented simultaneously since they modify different functions:

- Developer thread A: P1 (T005-T006)
- Developer thread B: P2 (T007-T010)
- Developer thread C: P3 (T011-T013)

Each thread toggles ONLY its experiment, runs independent eval. After all pass/fail decisions, Phase 6 combines.
