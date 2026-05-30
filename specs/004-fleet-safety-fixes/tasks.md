# Tasks: Fleet Safety Validation & Fixes

**Input**: Design documents from `specs/004-fleet-safety-fixes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create output directories and the experiment record required by the constitution before any code is written.

- [x] T001 Create `logs/` directory at repo root (if it does not exist)
- [x] T002 Create experiment record `experiments/2026-05-30-fleet-safety-v10.md` with hypothesis, change list, and placeholder result fields (Constitution IV gate)

**Checkpoint**: `logs/` exists; experiment record drafted — implementation may begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared diagnostic infrastructure that all user stories depend on.

- [x] T003 Create `diagnose_v9.py` at repo root with CLI argument parsing (`--games`, `--agent`, `--seed-start`, `--jobs`) matching `eval.py` conventions
- [x] T004 Implement `LaunchRecord` dataclass in `diagnose_v9.py` with fields: `game_seed`, `turn_launched`, `fleet_id`, `source_id`, `target_id`, `aimed_x`, `aimed_y`, `ships`, `outcome`, `turn_resolved`
- [x] T005 Implement agent wrapper in `diagnose_v9.py` that intercepts `agent(obs)` calls and logs every fleet launch to an in-memory list of `LaunchRecord`
- [x] T006 Implement fleet-tracking logic in `diagnose_v9.py`: each turn, compare current fleet list to prior turn's fleet list to detect fleet disappearances, recording `turn_resolved`
- [x] T007 Implement outcome inference in `diagnose_v9.py`: when a fleet disappears, check target planet ownership/garrison delta — if changed → `captured`; if not → `transit_loss`; if ambiguous → `unknown`
- [x] T008 Implement CSV writer in `diagnose_v9.py` that writes one file per run to `logs/diagnose_<agent>_<seed_start>_<games>.csv`

**Checkpoint**: `diagnose_v9.py` is runnable end-to-end and produces a CSV in `logs/`.

---

## Phase 3: User Story 1 — Diagnose Fleet Loss Root Causes (Priority: P1) 🎯 MVP

**Goal**: Run agent_v9 over 20 matches and produce a numeric baseline showing the rate of transit losses, captures, and unknowns per fleet launch.

**Independent Test**: Run `uv run python diagnose_v9.py --games 20 --agent agent_v9.py` and verify a CSV is written to `logs/` with `outcome` populated for every launched fleet.

- [x] T009 [US1] Wire `diagnose_v9.py` main loop: instantiate the agent wrapper, run N games via `kaggle_environments.make`, collect `LaunchRecord` lists, write CSV after each game
- [x] T010 [US1] Add summary printout at end of `diagnose_v9.py` run: total launches, count per outcome type, transit_loss percentage
- [x] T011 [US1] Run `uv run python diagnose_v9.py --games 20 --agent agent_v9.py --jobs 4` and record baseline results in `experiments/2026-05-30-fleet-safety-v10.md` under "Baseline (agent_v9)"

**Checkpoint**: Baseline numbers recorded — proportion of wasted fleet quantified for agent_v9.

---

## Phase 4: User Story 2 — Fix Sun-Crossing Fleets (Priority: P2)

**Goal**: agent_v10 never dispatches a fleet on a path that crosses the sun exclusion zone. (agent_v9 already has this but it is included in the safety audit.)

**Independent Test**: Run head-to-head and verify `transit_loss` rate attributed to sun is 0% in diagnose output for agent_v10.

- [x] T012 [P] [US2] Create `agent_v10.py` at repo root as a copy of `agent_v9.py` — this is the base for all subsequent fixes
- [x] T013 [US2] In `agent_v10.py`, audit `_path_safe(ox, oy, tx, ty)` — confirm the full-ray sun check from v9 is intact and correct; add an inline comment confirming it checks to the board edge via `_ray_exits_board`

**Checkpoint**: Sun-avoidance logic confirmed correct in agent_v10 — no regression from v9.

---

## Phase 5: User Story 3 — Fix Out-of-Bounds Target Predictions (Priority: P3)

**Goal**: agent_v10 rejects any predicted target position outside [0, 100] × [0, 100]. (agent_v9 already has this; audit for correctness and add comet path clamping.)

**Independent Test**: Verify no launched fleet in the diagnose output for agent_v10 has `aimed_x` or `aimed_y` outside [0, 100].

- [x] T014 [US3] In `agent_v10.py`, audit the `0 <= tx <= BOARD_SIZE and 0 <= ty <= BOARD_SIZE` guard in `_path_safe` — confirm it rejects boundary-exactly-100 positions correctly (use strict inequalities or confirm inclusive boundary is safe per CONTEST.md)
- [x] T015 [US3] In `agent_v10.py`, fix comet path index access: replace `future_idx = int(path_index + travel_turns)` with `future_idx = min(int(path_index + travel_turns), len(path) - 1)` in both the candidate loop and the fallback loop; add `if not path: continue` guard before index access

**Checkpoint**: OOB guards and comet index clamping confirmed in agent_v10.

---

## Phase 6: User Story 4 — Fix Intermediate Planet Obstruction (Priority: P3)

**Goal**: agent_v10 rejects launches whose ray passes within clearance distance of any non-target planet, not just the sun.

**Independent Test**: Manually verify that a launch from a planet whose straight-line path to a target would pass through another orbiting planet is correctly rejected in the candidate selection loop.

- [x] T016 [P] [US4] In `agent_v10.py`, add constant `PLANET_MARGIN = 1.0` alongside `SUN_EXCLUSION`
- [x] T017 [US4] In `agent_v10.py`, update `_path_safe(ox, oy, tx, ty)` signature to `_path_safe(ox, oy, tx, ty, all_planets=None, target_id=None)` — existing callers use default `None` and are unaffected
- [x] T018 [US4] In `agent_v10.py`, inside `_path_safe`, after the existing sun check, add loop: for each planet in `all_planets` (skip if `planet.id == target_id`), compute `_segment_dist_to_sun`-style distance from the full ray to that planet's center; return `False` if distance < `planet.radius + PLANET_MARGIN`
- [x] T019 [US4] In `agent_v10.py`, update every `_path_safe(...)` call site in `agent()` to pass `all_planets=planets` and `target_id=t.id` — covers the candidate loop, the fallback loop, and the evacuate-comet branch

**Checkpoint**: `_path_safe` now checks all intermediate planets. agent_v10 candidate selection rejects paths blocked by any planet.

---

## Phase 7: User Story 4 (continued) — Fix Intercept Accuracy (Priority: P3)

**Goal**: Orbit-lead predicted positions use a refined travel_turns estimate so fleets arrive at the planet's actual location.

**Independent Test**: Run diagnose on agent_v10 and verify `transit_loss` rate drops versus the agent_v9 baseline; orbit-lead intercept accuracy improves by ≥10 percentage points.

- [x] T020 [US4] In `agent_v10.py`, in the candidate loop for non-comet orbiting planets, replace the single `travel_turns = dist / fleet_speed(mine.ships + 1)` estimate with a one-step refinement: compute `t0`, predict planet pos at `t0`, recompute distance to predicted pos, compute `t1`, then use `_predict_planet_pos(..., t1)` as the final `(x_pred, y_pred)`
- [x] T021 [US4] Apply the same one-step refinement in the fallback loop for non-comet orbiting planets in `agent_v10.py`

**Checkpoint**: Orbit-lead intercept uses refined travel time in both candidate and fallback loops.

---

## Phase 8: Evaluation & Documentation

**Purpose**: Run the head-to-head evaluation, record results, update README and experiment log.

- [x] T022 Run `uv run python diagnose_v9.py --games 20 --agent agent_v10.py --jobs 4` and record agent_v10 baseline numbers in `experiments/2026-05-30-fleet-safety-v10.md` under "Fixed Agent (agent_v10)"
- [x] T023 Run `uv run python eval.py --games 20 --agent0 agent_v10.py --agent1 agent_v9.py --jobs 4` and record head-to-head win rate in `experiments/2026-05-30-fleet-safety-v10.md`
- [x] T024 Verify SC-002 (0% sun losses), SC-003 (0% OOB losses), SC-004 (≥10pp intercept improvement), SC-005 (≥75% win rate vs v9) — document pass/fail in experiment record
- [x] T025 Update `README.md` Agents table to include agent_v10 with win rates (bold if best agent)
- [x] T026 [P] Add `if __name__ == "__main__":` block to `agent_v10.py` matching v9's self-test pattern

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story phases
- **Phase 3 (US1 — Diagnose)**: Depends on Phase 2 — must complete before Phases 4–7 (baseline needed)
- **Phase 4 (US2 — Sun fix)**: Depends on Phase 3 baseline; T012 creates `agent_v10.py` which Phases 5–7 build on — **Phase 4 must complete before Phases 5–7**
- **Phases 5, 6, 7 (US3, US4)**: Depend on Phase 4 (agent_v10.py exists); can be applied sequentially in order
- **Phase 8 (Eval)**: Depends on all fix phases complete

### User Story Dependencies

- **US1 (Diagnose)**: Unblocked after Phase 2
- **US2 (Sun)**: Unblocked after US1 baseline run; T012 is the gate task for subsequent phases
- **US3 (OOB)**: Unblocked after T012 (agent_v10.py created)
- **US4 (Planet obstruction + intercept)**: Unblocked after T012; T016–T021 can follow T015 directly

### Within Each Phase

- Tasks with `[P]` can run in parallel with other `[P]` tasks in the same phase
- Non-`[P]` tasks in a phase must run in dependency order

---

## Parallel Opportunities

```bash
# Phase 2 (Foundational) — all independent files:
T003  # diagnose_v9.py skeleton (CLI)
T004  # LaunchRecord dataclass

# Phase 4 + 5 after T012 creates agent_v10.py:
T013  # audit sun check (agent_v10.py)
T014  # audit OOB guard (agent_v10.py)  ← sequential with T013 (same file, different functions)

# Phase 6 setup:
T016  # add PLANET_MARGIN constant  ← [P] with T014
```

---

## Implementation Strategy

### MVP First (User Story 1 — Baseline Measurement)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational harness (T003–T008)
3. Complete Phase 3: Run baseline and record numbers (T009–T011)
4. **STOP and VALIDATE**: Confirm diagnose CSV looks correct and baseline is meaningful

### Incremental Fix Delivery

1. US2 (T012–T013): Create agent_v10, confirm sun check
2. US3 (T014–T015): Apply OOB audit and comet clamping
3. US4a (T016–T019): Planet obstruction check
4. US4b (T020–T021): Orbit-lead travel refinement
5. Phase 8 (T022–T026): Evaluate, document, update README

---

## Notes

- `[P]` tasks touch different files or independent functions — safe to parallelize
- `[Story]` label maps each task to its user story for traceability
- No test tasks generated (not requested in spec)
- Always run `diagnose_v9.py` baseline **before** creating agent_v10.py changes so numbers are comparable
- Constitution IV: experiment record must be drafted (T002) before any implementation begins
- Constitution V: at least 20 head-to-head games required before considering submission (T023)
