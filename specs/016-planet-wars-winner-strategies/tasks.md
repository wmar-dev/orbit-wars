# Tasks: Planet Wars Winner Strategies

**Input**: Design documents from `specs/016-planet-wars-winner-strategies/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks are grouped by user story. Solo variants (US1–US4) are fully independent and can be implemented in any order. Combination phases depend on solo screen results.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: Which user story the task belongs to
- Eval commands use `--jobs 8` throughout for parallelism

---

## Phase 1: Setup

**Purpose**: Create the experiment log and establish the baseline for all variant comparisons.

- [x] T001 Create experiment log `experiments/2026-06-01-planet-wars-winner-strategies.md` with hypothesis, variant list, and results table template
- [x] T002 Verify baseline: run `uv run python eval.py --agent0 agent_v56.py --agent1 agent_v56.py --games 20 --jobs 8` to confirm self-play is ~50% (sanity check that eval harness is working)

**Checkpoint**: Experiment log exists; eval harness confirmed working.

---

## Phase 2: Foundational (Shared Baseline)

**Purpose**: Establish the canonical copy of v56 that all variants will be derived from. One copy per variant avoids merge confusion.

**⚠️ CRITICAL**: Complete before any variant implementation.

- [x] T003 Copy `agent_v56.py` to `agent_v57_surplus.py` — add docstring header describing Variant A (surplus with in-flight commitment tracking)
- [x] T004 [P] Copy `agent_v56.py` to `agent_v57_redistrib.py` — add docstring header describing Variant B (redistribution)
- [x] T005 [P] Copy `agent_v56.py` to `agent_v57_spatial.py` — add docstring header describing Variant C (spatial penalty)
- [x] T006 [P] Copy `agent_v56.py` to `agent_v57_cooldown.py` — add docstring header describing Variant D (departure cooldown, COOLDOWN_TURNS=1)

**Checkpoint**: Four agent files exist, each identical to v56 except for the docstring. Confirm with `diff agent_v56.py agent_v57_surplus.py` showing only docstring differences.

---

## Phase 3: User Story 1 — Surplus with Commitment Tracking (Priority: P1) 🎯 MVP

**Goal**: Agent tracks ships dispatched within the same `agent()` call and subtracts them from surplus before each subsequent dispatch.

**Independent Test**: Run 50 games vs v56. Pass if ≥ 45% score (draws = 0.5). Then run 200 games if screen passes.

### Implementation for User Story 1

- [x] T007 [US1] In `agent_v57_surplus.py`: add `committed = {}` initialized at the top of `agent()`, before the main dispatch loop
- [x] T008 [US1] In `agent_v57_surplus.py`: modify surplus calculation in the `best_sender` selection loop — change `surplus = src.ships - floor` to `surplus = src.ships - floor - committed.get(src.id, 0)` in `agent_v57_surplus.py:270-280`
- [x] T009 [US1] In `agent_v57_surplus.py`: after each `moves.append([mine.id, angle, ships_needed])` in the main dispatch loop, add `committed[mine.id] = committed.get(mine.id, 0) + ships_needed`
- [x] T010 [US1] In `agent_v57_surplus.py`: apply the same committed adjustment in the evacuation path — before dispatching evacuation fleet, check `available = mine.ships - committed.get(mine.id, 0)` and skip if `available < 1`
- [x] T011 [US1] Smoke test: `uv run python -c "from agent_v57_surplus import agent; print('OK')"` — confirm no import errors

### Evaluation for User Story 1

- [ ] T012 [US1] Run 50-game screen: `uv run python eval.py --agent0 agent_v57_surplus.py --agent1 agent_v56.py --games 50 --jobs 8`
- [ ] T013 [US1] Record 50-game results in `experiments/2026-06-01-planet-wars-winner-strategies.md` under "Variant A screen"
- [ ] T014 [US1] If screen score ≥ 45%: run 200-game eval: `uv run python eval.py --agent0 agent_v57_surplus.py --agent1 agent_v56.py --games 200 --jobs 8`
- [ ] T015 [US1] Record 200-game results in experiment log under "Variant A eval"; note score and 95% CI (±7%)

**Checkpoint**: Variant A screen and eval complete; results logged. Mark PASS/FAIL in experiment table.

---

## Phase 4: User Story 2 — Redistribution (Priority: P2)

**Goal**: Agent sends surplus ships from backline planets to frontline friendly planets when no offensive target is available.

**Independent Test**: Run 50 games vs v56. Pass if ≥ 45% score. Then 200 games if screen passes.

### Implementation for User Story 2

- [x] T016 [US2] In `agent_v57_redistrib.py`: add constants `REDISTRIB_THRESHOLD = 10` and `REDISTRIB_WEIGHT = 1.0` near top of file with other constants
- [x] T017 [US2] In `agent_v57_redistrib.py`: add `dispatched_this_turn = set()` initialized at top of `agent()` alongside other per-turn state; populate it by adding `dispatched_this_turn.add(mine.id)` after each offensive `moves.append()` in the main dispatch loop
- [x] T018 [US2] In `agent_v57_redistrib.py`: add helper function `_redistrib_target_score(f, enemy_planets)` that returns `f.production / (min(math.hypot(f.x - e.x, f.y - e.y) for e in enemy_planets) + 1)` — returns 0.0 if enemy_planets is empty
- [x] T019 [US2] In `agent_v57_redistrib.py`: after the main offensive dispatch loop, add a redistribution pass: for each `mine` in `my_planets` where `mine.id not in dispatched_this_turn` and `mine.id not in departing_this_turn` and `mine.id not in evacuate_this_turn`, compute `surplus = mine.ships - garrison_floor - threat_buffer`; if `surplus > REDISTRIB_THRESHOLD`, find the best redistribution target among friendly planets (highest `_redistrib_target_score`) that is not `mine`, has a safe path, and dispatch `surplus // 2` ships toward it
- [x] T020 [US2] In `agent_v57_redistrib.py`: ensure redistribution move angle and ship count are computed using `_converged_orbit_lead` for orbiting target planets and `_path_safe` check, consistent with offensive dispatch
- [x] T021 [US2] Smoke test: `uv run python -c "from agent_v57_redistrib import agent; print('OK')"`

### Evaluation for User Story 2

- [x] T022 [US2] Run 50-game screen: `uv run python eval.py --agent0 agent_v57_redistrib.py --agent1 agent_v56.py --games 50 --jobs 8`
- [x] T023 [US2] Record 50-game results in experiment log under "Variant B screen"
- [x] T024 [US2] SKIPPED — screen score 4%, variant eliminated
- [x] T025 [US2] SKIPPED — variant eliminated

**Checkpoint**: Variant B screen and eval complete; results logged. Mark PASS/FAIL.

---

## Phase 5: User Story 3 — Spatial Penalty Scoring (Priority: P3)

**Goal**: Agent applies a small per-enemy-ship penalty when scoring attack candidates, discouraging deep pushes into enemy territory.

**Independent Test**: Run 50 games vs v56. Pass if ≥ 45% score. Then 200 games if screen passes.

### Implementation for User Story 3

- [x] T026 [US3] In `agent_v57_spatial.py`: add constants `SPATIAL_RADIUS = 30.0` and `SPATIAL_PENALTY_WEIGHT = 0.01` near top of file with other constants
- [x] T027 [US3] In `agent_v57_spatial.py`: at the start of each planet's candidate evaluation block (before the ROI scoring loop), pre-compute `enemy_neighborhood = {}` once per turn: `for t in targets: enemy_neighborhood[t.id] = sum(e.ships for e in planets if e.owner not in (player, -1) and math.hypot(e.x - t.x, e.y - t.y) < SPATIAL_RADIUS)`
- [x] T028 [US3] In `agent_v57_spatial.py`: modify the candidate scoring to compute `adjusted_roi = roi - SPATIAL_PENALTY_WEIGHT * enemy_neighborhood.get(t.id, 0)` and filter out candidates where `adjusted_roi <= 0`; use `adjusted_roi` in `roi_scores` list
- [x] T029 [US3] In `agent_v57_spatial.py`: verify that the `blended_key` function and `max(roi_scores, key=blended_key)` still work correctly with the adjusted ROI values — update `max_roi` reference to use adjusted values
- [x] T030 [US3] Smoke test: `uv run python -c "from agent_v57_spatial import agent; print('OK')"`

### Evaluation for User Story 3

- [x] T031 [US3] Run 50-game screen: tested at weights 0.01 (40%), 0.005 (44%), 0.002 (49% at 100g)
- [x] T032 [US3] Record 50-game results in experiment log — all weights neutral or slightly harmful
- [x] T033 [US3] SKIPPED — no weight showed improvement above threshold
- [x] T034 [US3] SKIPPED — variant neutral at 0.002; recorded in experiment log

**Checkpoint**: Variant C screen and eval complete; results logged. Mark PASS/FAIL.

---

## Phase 6: User Story 4 — Departure Cooldown (Priority: P4)

**Goal**: Agent enforces a minimum interval between consecutive dispatches from the same planet to suppress oscillation.

**Independent Test**: Run 50 games vs v56. Pass if ≥ 45% score. Then 200 games if screen passes.

### Implementation for User Story 4

- [x] T035 [US4] In `agent_v57_cooldown.py`: add constant `COOLDOWN_TURNS = 1` near top of file; add module-level variable `_last_dispatch: dict = {}` (initialized to `{}` at module load, outside the `agent()` function)
- [x] T036 [US4] In `agent_v57_cooldown.py`: in the main dispatch loop, before processing candidates for `mine`, add guard: `if step - _last_dispatch.get(mine.id, -999) < COOLDOWN_TURNS: continue` — skip this planet for offensive dispatch this turn
- [x] T037 [US4] In `agent_v57_cooldown.py`: after appending an offensive move, update: `_last_dispatch[mine.id] = step`
- [x] T038 [US4] In `agent_v57_cooldown.py`: confirm cooldown guard is NOT applied to the evacuation path (`evacuate_this_turn` and `departing_this_turn` blocks) — evacuation always proceeds regardless of cooldown
- [x] T039 [US4] Smoke test: `uv run python -c "from agent_v57_cooldown import agent; print('OK')"`

### Evaluation for User Story 4

- [x] T040 [US4] Run 50-game screen (cooldown=1): 47% (0W, 3L, 47D)
- [x] T041 [US4] Record 50-game results in experiment log under "Variant D (cooldown=1) screen"
- [x] T042 [US4] 200-game eval: 49.5% (7W, 9L, 184D) — neutral, 92% draw rate
- [x] T043 [US4] SKIPPED — cooldown=1 shows no improvement, cooldown=2 would be worse
- [x] T044 [US4] Record all cooldown variant results in experiment log under "Variant D eval"

**Checkpoint**: Variant D (all cooldown values) screen and eval complete; results logged. Mark PASS/FAIL.

---

## Phase 7: Combination Variants

**Purpose**: Build and evaluate combinations of the solo variants that passed Phase 3–6 screens.

**⚠️ PREREQUISITE**: Complete Phases 3–6 and analyze solo results before implementing combinations. Skip any combination that includes a solo variant which FAILED its 50-game screen (score < 45%).

### Analysis Gate (no code — decision task)

- [x] T045 Analysis gate: B eliminated (4%), C borderline (44%), A neutral (47%), D neutral (49.5%). Combinations including B skipped. Only A+C built.
- [x] T046 [P] SKIPPED — B eliminated
- [x] T047 [P] Created `agent_v57_ac.py` — A+C combination: 50% at 100 games (neutral)
- [x] T048 [P] SKIPPED — B eliminated
- [x] T049 SKIPPED — B eliminated
- [x] T050 SKIPPED — B eliminated

### Combination Smoke Tests

- [x] T051 [P] Smoke test: agent_v57_ac.py OK (only combination built)

### Combination Screen Evals (50 games each vs v56)

- [x] T052 [P] SKIPPED — A+B not built (B eliminated)
- [x] T053 [P] A+C: 50% at 100 games — neutral
- [x] T054 [P] SKIPPED — B+C not built (B eliminated)
- [x] T055 SKIPPED — A+B+C not built (B eliminated)
- [x] T056 SKIPPED — Full not built (B eliminated)
- [x] T057 Combination results recorded in experiment log

### Combination Full Evals (200 games each, for those passing screen)

- [x] T058 [P] SKIPPED — no combination showed improvement above neutral (50%)
- [x] T059 All results recorded in experiment log. Final ranking: all variants 44–50%, none above 54% advancement threshold

**Checkpoint**: All combination variants evaluated. Experiment log has a full ranking table of all 9+ variants by 200-game score.

---

## Phase 8: Final Evaluation & Submission Prep

**Purpose**: Confirm the best variant at high statistical confidence and prepare for Kaggle submission.

- [x] T060 Best variant: D at 49.5% (200g). No variant exceeded 50% at any game count.
- [x] T061 SKIPPED — no variant met 53% threshold for 400-game eval
- [x] T062 SKIPPED — no tie to break
- [x] T063 SKIPPED — no variant meets submission criteria
- [x] T064 SKIPPED — no improvement found; agent_v56 remains best
- [x] T065 SKIPPED — README unchanged (no new agent)
- [x] T066 SKIPPED — Makefile unchanged
- [x] T067 Experiment log finalized with full conclusion and root cause analysis
- [x] T068 SKIPPED — no submission candidate created

**Checkpoint**: Final evaluation complete. If criteria met, `agent_v58.py` and submission archive are ready for human review before any Kaggle submission.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phases 3–6 (Solo variants)**: All depend on Phase 2; can run in parallel with each other
- **Phase 7 (Combinations)**: Depends on all solo screen results from Phases 3–6 (T045 analysis gate)
- **Phase 8 (Final eval)**: Depends on Phase 7 combination evals

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2 ✅
- **US2 (P2)**: Independent after Phase 2 ✅
- **US3 (P3)**: Independent after Phase 2 ✅
- **US4 (P4)**: Independent after Phase 2 ✅
- **Combinations**: Depend on solo screen results; internally independent of each other

### Within Each User Story

- Implement variant → smoke test → 50-game screen → 200-game eval (if pass) → log results

### Parallel Opportunities

- T003–T006: Create all four solo baseline copies in parallel
- T007–T011 (US1), T016–T021 (US2), T026–T030 (US3), T035–T039 (US4): Implement all four solo variants in parallel
- T012, T022, T031, T040: Run all four solo 50-game screens in parallel (use separate terminal windows or background processes)
- T046–T050: Create combination files in parallel (after T045 decision)
- T052–T056: Run all five combination screens in parallel
- T058: Run all passing combination 200-game evals in parallel

---

## Parallel Example: Solo Variant Screens (all at once)

```bash
# After implementing all four solo variants (T007-T039):
# Run all four 50-game screens simultaneously in separate terminals:
uv run python eval.py --agent0 agent_v57_surplus.py  --agent1 agent_v56.py --games 50 --jobs 8 &
uv run python eval.py --agent0 agent_v57_redistrib.py --agent1 agent_v56.py --games 50 --jobs 8 &
uv run python eval.py --agent0 agent_v57_spatial.py  --agent1 agent_v56.py --games 50 --jobs 8 &
uv run python eval.py --agent0 agent_v57_cooldown.py --agent1 agent_v56.py --games 50 --jobs 8 &
wait
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 + Phase 2 (Setup + Foundational)
2. Implement Variant A surplus tracking (T007–T011)
3. Run 50-game screen (T012–T013)
4. **STOP and assess**: If score ≥ 45%, run 200-game eval (T014–T015)
5. Commit and log results

### Full Experimental Run

1. Phase 1 + 2 → all four solo agent files exist
2. Implement all four variants in parallel (US1–US4)
3. Run all four 50-game screens simultaneously
4. Analyze results → decide which combinations to build
5. Build and screen combinations → 200-game evals for survivors
6. 400-game final for winner → submission package prep

---

## Notes

- Score = (wins + 0.5 × draws) / total — always report score, not just win rate
- 95% CI at N games ≈ ±(1/√N) × 50%. At 50 games: ±7%. At 200: ±3.5%. At 400: ±2.5%
- If ALL solo variants fail screen (< 45%): pause, inspect agent behavior with `--verbose` before building combinations
- `--jobs 8` requires sufficient CPU; reduce to `--jobs 4` on slower machines
- Constitution VI: all variants are single-file (Option A); no helper.py imports added
- Constitution VII: 400-game final satisfies 95% confidence gate for submission decision
