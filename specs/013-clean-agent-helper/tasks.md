# Tasks: Clean Agent with Helper Module

**Input**: Design documents from `specs/013-clean-agent-helper/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not requested in spec — no test tasks generated.

**Organization**: Tasks are grouped by user story. US1 (helper.py importable) is foundational for US2 (agent_v41.py) and US3 (standalone library UX).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Create the new files and experiment record skeleton.

- [x] T001 Create `helper.py` as an empty module at repo root with module docstring and empty `__all__ = []`
- [x] T002 [P] Create `agent_v41.py` as an empty skeleton at repo root with module docstring, imports block, and empty `agent(obs)` stub returning `[]`
- [x] T003 [P] Create `experiments/013-clean-agent-helper.md` with hypothesis, change description, and placeholder rows for eval results

**Checkpoint**: Three new files exist. `python -c "import helper"` and `python agent_v41.py` both run without errors.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Populate `helper.py` with all constants and pure functions. This MUST be complete before agent_v41.py can be implemented.

**⚠️ CRITICAL**: US2 (agent_v41.py) and US3 (standalone UX) both depend on this phase.

- [x] T004 Add all constants to `helper.py`: copy confirmed constant values from data-model.md constants table (`GARRISON_FLOOR_FACTOR`, `EVACUATE_THRESHOLD`, `ORBIT_LEAD_EPS`, `ORBIT_LEAD_MAX_ITER`, `REWARD_ALPHA`, `ANGLE_EPSILON`, `RACE_EPSILON`, `SUN_RADIUS`, `SAFETY_MARGIN`, `SUN_EXCLUSION`, `PLANET_MARGIN`, `BOARD_SIZE`, `_SUN_X`, `_SUN_Y`, `W_CAPTURE`, `W_SHIP`, `CAPTURE_SCALE`, `SHIP_SCALE`, `PROD_WEIGHT`, `DIST_WEIGHT`, `MAX_PROD`, `MAX_DIST`, `HIGH_PROD_THRESHOLD`, `ENEMY_PENALTY`, `MAX_SHIPS_ESTIMATE`, `BANK_PROD_THRESHOLD`, `BANK_TURNS_FACTOR`, `EPSILON`) in `helper.py`
- [x] T005 [P] Implement geometry primitives in `helper.py`: `segment_dist_to_point`, `segment_dist_to_sun`, `ray_exits_board` — public names (no underscore prefix), copied and renamed from agent_v38.py
- [x] T006 [P] Implement `path_safe` and `angle_to` and `angle_diff` in `helper.py` — `path_safe` renamed from `_path_safe` in agent_v38.py; `angle_to(x1, y1, x2, y2)` is a new convenience wrapper returning `math.atan2(y2-y1, x2-x1)`; `angle_diff` renamed from `_angle_diff`
- [x] T007 [P] Implement fleet and orbital functions in `helper.py`: `fleet_speed` (unchanged), `predict_planet_pos` (renamed from `_predict_planet_pos`), `converged_orbit_lead` (renamed from `_converged_orbit_lead`) — copy from agent_v38.py, rename only
- [x] T008 [P] Implement comet functions in `helper.py`: `build_comet_path_lookup`, `comet_predicted_pos`, `comet_two_pass` — renamed from `_build_comet_path_lookup`, `_comet_predicted_pos`, `_comet_two_pass` in agent_v38.py
- [x] T009 Implement scoring functions in `helper.py`: `roi` (renamed from `_roi`), `reward_estimate` (renamed from `_reward_estimate`), `planet_value` (renamed from `_planet_value` in agent_v40.py), `enemy_incoming` (renamed from `_enemy_incoming` in agent_v40.py) — depends on T004 (constants)
- [x] T010 Implement strategy helpers in `helper.py`: `banking_mode` (renamed from `_banking_mode` in agent_v40.py, remove variant parameter — hardcode Variant B logic directly) and `predict_target` (renamed from `_predict_target` in agent_v40.py) in `helper.py` — depends on T005–T009
- [x] T011 Populate `__all__` in `helper.py` with all public function and constant names per contracts/helper-api.md — depends on T004–T010

**Checkpoint**: `python -c "import helper; print(helper.__all__)"` prints all expected names without errors. `python -c "import helper; print(helper.fleet_speed(100))"` returns a float.

---

## Phase 3: User Story 1 - Human-Crafted Agent Development (Priority: P1) 🎯 MVP

**Goal**: `helper.py` is importable in isolation, all public functions are callable, and a developer can write a working agent using only `helper.py`.

**Independent Test**: `python -c "import helper; print(helper.fleet_speed(100), helper.angle_to(0,0,1,1))"` succeeds; a 10-line agent using two helper functions runs without errors in eval.

- [x] T012 [US1] Verify `helper.py` has no `kaggle_environments` import and no global mutable state — review the file and fix any violations found during T004–T011
- [x] T013 [US1] Smoke-test `helper.py` standalone: run `uv run python -c "import helper; print(helper.__all__)"` and confirm all 17+ functions and all constants appear in the output; fix any missing exports

**Checkpoint**: US1 independently verified — `helper.py` imports cleanly and all functions are accessible.

---

## Phase 4: User Story 2 - New Best Agent (Priority: P2)

**Goal**: `agent_v41.py` imports from `helper.py`, incorporates all proven mechanics from v38/v40 with dead code removed, and achieves competitive eval results.

**Independent Test**: `uv run python eval.py --agent0 agent_v41.py --agent1 agent_v38.py --games 50 --seed 0` completes and win rate is reported; same for agent_v40.

- [x] T014 [US2] Implement observation parsing block in `agent_v41.agent()` in `agent_v41.py`: extract `player`, `raw_planets`, `initial_planets_raw`, `angular_velocity`, `raw_fleets`, `step` from obs (supports both dict and namedtuple forms); build `planets`, `my_planets`, `enemy_planets`, `targets`, `initial_planets_map`
- [x] T015 [US2] Implement threat detection in `agent_v41.agent()` in `agent_v41.py`: build `threat` dict by iterating `raw_fleets`, skipping player-owned fleets, calling `helper.angle_diff` with `ANGLE_EPSILON` — no inline reimplementation of angle diff
- [x] T016 [US2] Implement comet setup in `agent_v41.agent()` in `agent_v41.py`: call `helper.build_comet_path_lookup(obs)`, derive `comet_planet_ids`, build `departing_this_turn` and `evacuate_this_turn` sets using `EVACUATE_THRESHOLD`
- [x] T017 [US2] Implement early exits and banking check in `agent_v41.agent()` in `agent_v41.py`: guard `if not my_planets or not targets: return moves`; call `helper.banking_mode(my_planets, enemy_planets, step)` (no variant parameter — locked to Variant B)
- [x] T018 [US2] Implement comet evacuation loop in `agent_v41.agent()` in `agent_v41.py`: iterate `my_planets` where `mine.id in evacuate_this_turn`; use `helper.predict_target` for both comet and non-comet planets; score owned planets by production/distance and non-owned by `helper.roi`; append move; call `helper.angle_to` for final angle
- [x] T019 [US2] Implement best-sender assignment in `agent_v41.agent()` in `agent_v41.py`: build `best_sender` dict mapping target_id → sender planet_id using dist/surplus scoring; apply threat-aware garrison floor: `max(production * GARRISON_FLOOR_FACTOR, threat.get(src.id, 0))`
- [x] T020 [US2] Implement attack loop in `agent_v41.agent()` in `agent_v41.py`: iterate `my_planets` skipping departing/evacuating; filter candidates where `best_sender[t.id] == mine.id`; call `helper.predict_target` for orbit-lead/comet; compute blended ROI key using `helper.roi` and `helper.reward_estimate` with `REWARD_ALPHA`; add `helper.enemy_incoming` to ships_needed for neutral targets; append move using `helper.angle_to`
- [x] T021 [US2] Verify `agent_v41.py` line count is ≤350 lines (SC-004) — 195 lines ✅
- [x] T022 [US2] Run smoke test: `make test` (agent_v41 vs random, 1 game) — Makefile updated, smoke test passes
- [x] T023 [US2] Run eval vs agent_v38: 52% win rate (26W/24L/0D, 50 games) ✅
- [x] T024 [US2] Run eval vs agent_v40: 52% win / 56% score (26W/20L/4D, 50 games) ✅
- [x] T025 [US2] Both gates pass — agent_v41 promoted as new best agent

**Checkpoint**: Both eval runs complete. Win rates recorded. If both pass, agent_v41 is the new best agent.

---

## Phase 5: User Story 3 - Reusable Helper Library UX (Priority: P3)

**Goal**: `helper.py` is usable as a standalone reference — clean function names, one-line docstrings on non-obvious functions, no surprises for a developer reading it cold.

**Independent Test**: A developer reading only `helper.py` and the contracts doc can write a working 20-line agent without reading any agent_vNN.py file.

- [x] T026 [P] [US3] Add one-line docstrings to non-obvious functions in `helper.py`: `converged_orbit_lead`, `comet_two_pass`, `predict_target`, `banking_mode`, `planet_value`, `enemy_incoming` — keep docstrings to one line each per project style
- [x] T027 [US3] Final standalone import test in `helper.py`: run `uv run python -c "import helper; print(helper.__all__)"` in a clean subprocess and confirm no errors

**Checkpoint**: US3 verified — `helper.py` is self-documenting and importable in isolation.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T028 Update README.md Agents table: add agent_v41 row with strategy description and eval win rates vs v38 and v40; bold agent_v41 if it is the new best agent (per CLAUDE.md instructions)
- [x] T029 [P] Complete `experiments/013-clean-agent-helper.md`: fill in conclusion, confirm hypothesis result, note any interesting findings from the eval runs
- [x] T030 [P] Verify Makefile `AGENT` and `RENDER_AGENT` point to `agent_v41.py` ✅
- [x] T031 [P] Pre-submission package check: only `helper` is local import; `helper.py` is at repo root ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story phases
- **Phase 3 (US1)**: Depends on Phase 2 — validates helper.py is clean
- **Phase 4 (US2)**: Depends on Phase 2 and Phase 3 — agent_v41.py imports from helper.py
- **Phase 5 (US3)**: Depends on Phase 2 — adds docstrings, can run concurrently with Phase 4
- **Phase 6 (Polish)**: Depends on Phase 4 (eval results needed for README/experiments)

### Within Phase 2

- T004 (constants) → T005, T006, T007, T008 [all parallel] → T009 (scoring, needs constants) → T010 (strategy helpers, needs everything) → T011 (__all__)

### Within Phase 4

- T014 (parsing) → T015, T016 [parallel] → T017 → T018, T019 [parallel] → T020 → T021 → T022 → T023, T024 [parallel] → T025

### Parallel Opportunities

- Phase 1: T002, T003 can run in parallel with T001
- Phase 2: T005, T006, T007, T008 can all run in parallel after T004
- Phase 4: T015/T016 parallel; T018/T019 parallel; T023/T024 parallel
- Phase 5: T026/T027 parallel
- Phase 6: T028/T029/T030/T031 all parallel

---

## Parallel Example: Phase 2

```text
# After T004 (constants) — launch these 4 together:
T005: segment_dist_to_point, segment_dist_to_sun, ray_exits_board in helper.py
T006: path_safe, angle_to, angle_diff in helper.py
T007: fleet_speed, predict_planet_pos, converged_orbit_lead in helper.py
T008: build_comet_path_lookup, comet_predicted_pos, comet_two_pass in helper.py

# Then sequentially:
T009: roi, reward_estimate, planet_value, enemy_incoming in helper.py
T010: banking_mode, predict_target in helper.py
T011: __all__ in helper.py
```

---

## Implementation Strategy

### MVP First (US1 + helper.py foundation)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T011) — builds helper.py
3. Complete Phase 3: US1 (T012–T013) — validates helper.py is standalone
4. **STOP and VALIDATE**: `python -c "import helper; print(helper.__all__)"` passes

### Incremental Delivery

1. Phase 1 + 2 + 3 → `helper.py` is a working standalone library
2. Phase 4 → `agent_v41.py` is implemented and evaluated — new best agent decision
3. Phase 5 → `helper.py` polished for human use
4. Phase 6 → README, experiments, Makefile updated

---

## Notes

- All function implementations in Phase 2 should copy from agent_v38.py or agent_v40.py and rename only — do not rewrite logic
- `banking_mode` in helper.py drops the `variant` parameter; Variant B logic is hardcoded directly
- `predict_target` in helper.py is taken verbatim from `_predict_target` in agent_v40.py (already a helper there)
- Dead code NOT to port from agent_v40: `assigned_primary`, `assigned_secondary`, `high_prod_neutrals`, `high_prod_enemies`, `RANGE_FACTOR`, `BANKING_VARIANT`, `FALLBACK_VARIANT`
- If eval results in T025 fail the gates, the most likely fix is the banking mode (Variant B hardcoded may need tuning) or the `predict_target` integration
