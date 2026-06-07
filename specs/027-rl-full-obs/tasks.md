---
description: "Task list for RL full observation overhaul"
---

# Tasks: RL Full Observation

**Input**: Design documents from `/specs/027-rl-full-obs/`

**Organization**: Tasks are grouped by user story for independent implementation.

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Update shared constants and interfaces that both US1 and US2 depend on.

- [ ] T001 Update MAX_PLANETS=40, MAX_FLEETS=50 (hot 8 + summary 42), NEW_OBS_SIZE in rl/obs.py
- [ ] T002 [P] Update PolicyNet input to 560, add 5× action head slots in rl/ppo.py
- [ ] T003 [P] Update env.py action_space to 5 × MultiDiscrete([40,40,4]) in rl/env.py
- [ ] T004 Update decode_action signature in rl/obs.py to handle 15-value action array
- [ ] T005 [P] Update export.py constants and numpy_forward call sites

---

## Phase 2: User Story 1 — Full-Board Observation (Priority: P1)

**Goal**: Encode all 40 planets, 50 fleets (hot + summary bins), planet type flags, comet waypoints. Action mask covers 80 bits.

**Independent Test**: `uv run python -c "from rl.obs import encode_obs, OBS_SIZE; assert OBS_SIZE == 560; print('OK')"`

- [ ] T006 [P] [US1] Add `is_orbiting` flag (8th planet feature) in rl/obs.py encode_obs
- [ ] T007 [P] [US1] Add fleet-summary binned encoding (42 bins × 3 owners) in rl/obs.py
- [ ] T008 [US1] Replace raw fleet slots with 8 nearest hot slots + 42 summary bins in rl/obs.py
- [ ] T009 [US1] Update action mask to 80 bits (0-39 source-valid, 40-79 target-valid) in rl/obs.py
- [ ] T010 [US1] Update encode_obs global to include planet_count in rl/obs.py

---

## Phase 3: User Story 2 — Multi-Fleet Action Space (Priority: P1)

**Goal**: Dispatch up to 5 fleets per turn, each with independent source/target/fraction, max 1 per source planet.

**Independent Test**: `uv run python -c "from kaggle_environments import make; env=make('orbit_wars'); env.run(['agent_v65.py', 'random']); print('OK')"` — counts average fleets dispatched per turn.

- [ ] T011 [US2] Implement 5 independent action heads (actor_src_i, actor_tgt_i, actor_frac_i) in rl/ppo.py PolicyNet
- [ ] T012 [US2] Implement multi-fleet decode_action in rl/obs.py (decodes 5×3 values → up to 5 fleets)
- [ ] T013 [US2] Enforce FR-007: max 1 fleet per source planet per turn in rl/obs.py decode_action
- [ ] T014 [US2] Update env.py step() to pass 15-value action array to decode_action
- [ ] T015 [US2] Update export.py numpy_forward to output 5×(40+40+4) logits
- [ ] T016 [US2] Update export.py agent template _encode and _forward for new OBS_SIZE and multi-fleet
- [ ] T017 [US2] Verify Principle VI: export checkpoint, test agent file in kaggle env

---

## Phase 4: User Story 3 — Train vs Strong Heuristic (Priority: P2)

**Goal**: Verify pipeline runs, train vs v64, measure win rate.

**Independent Test**: `make eval-rl GAMES=30` reports win rate after training.

- [ ] T018 [US3] Run 20-episode pipeline verification vs v64 (check no crashes, multi-fleet encodes correctly)
- [ ] T019 [US3] Train 5000 episodes vs agent_v64 with --no-curriculum
- [ ] T020 [US3] Evaluate every 500 episodes vs v64, log results to experiments/

---

## Phase 5: Polish

- [ ] T021 Finalize Makefile targets if any eval paths changed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundational)**: Must complete first. Blocks US1 and US2.
- **Phase 2 (US1)**: Can start after Phase 1. No dependency on US2.
- **Phase 3 (US2)**: Can start after Phase 1. No dependency on US1.
- **Phase 4 (US3)**: Needs Phase 1 + Phase 2 + Phase 3 complete.
- **Phase 5 (Polish)**: Any time after US1+US2 verified.

### Parallel Opportunities

- T002, T003, T005 are independent (different files) — parallel
- T006, T007 are independent — parallel
- US1 (Phase 2) and US2 (Phase 3) can proceed in parallel

### Implementation Strategy

**MVP** (Phase 1 + US1 + US2): Get the new observation and multi-fleet action working end-to-end. Run a 20-episode smoke test. This is the minimum viable step before training.

**Full delivery**: All 5 phases → train 5000 episodes vs v64.
