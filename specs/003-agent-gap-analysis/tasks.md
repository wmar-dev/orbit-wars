# Tasks: Agent Gap Analysis & Improvement Experiments

**Input**: Design documents from `specs/003-agent-gap-analysis/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/agent-interface.md ✅

**Tests**: Not requested — manual eval via `eval.py` is the validation method.

**Organization**: Isolated experiments (US1–US4) are fully independent and can be implemented and
evaluated in parallel. US5 (combined agent) gates on US1–US4 results.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent of other in-progress tasks)
- **[Story]**: Which user story / experiment this belongs to

---

## Phase 1: Setup

**Purpose**: Verify environment and shared helper infrastructure before any experiment agent.

- [ ] T001 Confirm `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10 --jobs 4` reproduces ~90% win rate baseline
- [ ] T002 Read `specs/003-agent-gap-analysis/research.md` and `data-model.md` to internalize all formulas before writing any agent

**Checkpoint**: Baseline confirmed; formulas understood.

---

## Phase 2: Foundational (Shared Helpers)

**Purpose**: Utility functions used by multiple experiment agents. Implement once, copy-paste as
needed (each agent must remain self-contained per Kaggle requirements — no shared module).

- [ ] T003 Verify `fleet_speed(n)` formula from CONTEST.md: `1.0 + 5.0 * (log(n)/log(1000))**1.5` — confirm reference values from research.md (1 ship=1.0, 10 ships≈1.96, 50 ships≈3.57)
- [ ] T004 Verify `_segment_dist_to_sun` in `agent_v3.py` is correct and reusable as-is (copy to new agents)
- [ ] T005 Verify `_heading_toward` dot-product formula from `research.md` R-3 works on a manually constructed test case (fleet pointing directly at planet → alignment=1.0)
- [ ] T005a [P] Establish sun-avoidance regression baseline: run `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 5 --verbose` and confirm zero fleets dispatched through sun exclusion zone (covers SC-3)
- [ ] T005b [P] Establish turn-timing baseline: run `uv run python agent_v3.py` and confirm `agent()` returns in <1 second per turn (covers SC-4); note any slow path to watch for in the defense pre-pass nested loop

**Checkpoint**: All three helper formulas verified; SC-3 and SC-4 baselines recorded. Ready to implement all four experiments in parallel.

---

## Phase 3: User Story 1 — Orbit-Lead Targeting (Priority: P1)

**Goal**: `agent_v4.py` predicts where orbiting planets will be when the fleet arrives, and aims there instead of at the current position.

**Independent Test**: `uv run python eval.py --agent0 agent_v4.py --agent1 agent_v3.py --games 20 --jobs 4` — record win rate. Pass ≥55% (11+ wins).

### Tasks — US1 Orbit-Lead

- [ ] T006 [P] [US1] Create `agent_v4.py` at project root as a copy of `agent_v3.py` — rename docstring to "Orbit-Lead Targeting Agent"
- [ ] T007 [P] [US1] Add `_predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns)` helper to `agent_v4.py` per research.md R-1 formula: compute `orbital_radius`, check `is_orbiting = orbital_radius + planet.radius < 50`, return `(x_pred, y_pred)` via `theta_pred = atan2(y-50, x-50) + angular_velocity * travel_turns`
- [ ] T008 [US1] In `agent_v4.py` `agent()` function, build `initial_planets_map = {p.id: Planet(*p) for p in initial_planets_raw}` at the top of each call, handling missing field gracefully with `obs.get("initial_planets", [])`
- [ ] T009 [US1] In `agent_v4.py` targeting loop, replace the direct `t.x, t.y` reference with `x_pred, y_pred = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel_turns)` before computing `angle` and sun-avoidance check — `travel_turns = hypot(t.x-mine.x, t.y-mine.y) / fleet_speed(ships_needed)`
- [ ] T010 [US1] Update `if __name__ == "__main__":` block in `agent_v4.py` to run `agent_v4 vs main.py` on seed 42
- [ ] T011 [US1] Run `uv run python agent_v4.py` — confirm it executes without error
- [ ] T012 [US1] Run `uv run python eval.py --agent0 agent_v4.py --agent1 agent_v3.py --games 20 --jobs 4` — record result
- [ ] T013 [US1] Write `experiments/2026-05-29-orbit-lead.md` with hypothesis, change description, self-play result table, and conclusion (pass/fail vs 55% threshold)
- [ ] T013a [US1] SC-3 regression check: run `uv run python eval.py --agent0 agent_v4.py --agent1 main.py --games 3 --verbose` and confirm sun-avoidance filter still fires correctly (no fleet crosses sun exclusion zone)

**Checkpoint**: agent_v4 complete and evaluated. Sun-avoidance regression confirmed. Result recorded in experiments/.

---

## Phase 4: User Story 2 — Comet Opportunism (Priority: P2)

**Goal**: `agent_v5.py` targets comets using predicted path positions, skipping comets about to leave the board.

**Independent Test**: `uv run python eval.py --agent0 agent_v5.py --agent1 agent_v3.py --games 20 --jobs 4` — record win rate. Pass ≥55%.

### Tasks — US2 Comet Opportunism

- [ ] T014 [P] [US2] Create `agent_v5.py` at project root as a copy of `agent_v3.py` — rename docstring to "Comet Opportunism Agent"
- [ ] T015 [P] [US2] Add `_build_comet_path_lookup(obs)` helper to `agent_v5.py`: iterate `obs.get("comets", [])`, for each group and each `planet_id` in `group["planet_ids"]` store `{planet_id: (path_list, path_index)}` — handle missing `comets` field gracefully
- [ ] T016 [US2] In `agent_v5.py` `agent()` function, build `comet_path_lookup` and `comet_planet_ids` set at top of each call; classify each owned comet: `departing_this_turn` if `remaining_steps == 0` (comet expires before fleet launch per turn order — cannot launch from it), `evacuate_next_turn` if `remaining_steps == 1` (will be gone next turn — must launch all ships off it now or lose them)
- [ ] T017 [US2] In `agent_v5.py` per-owned-planet loop: (a) skip `mine` entirely if `mine.id` is `departing_this_turn`; (b) if `mine.id` is `evacuate_next_turn`, override normal targeting and dispatch ALL of `mine.ships` toward the best sun-safe target regardless of affordability — ships are lost if not launched; (c) for comet *targets*: compute `travel_turns`, skip if `path_index + travel_turns + 5 >= len(path)`, else use `path[int(path_index + travel_turns)]` as predicted position; for non-comet targets use current `(t.x, t.y)` unchanged
- [ ] T018 [US2] Update `if __name__ == "__main__":` block in `agent_v5.py` to run `agent_v5 vs main.py` on seed 42
- [ ] T019 [US2] Run `uv run python agent_v5.py` — confirm it executes without error
- [ ] T020 [US2] Run `uv run python eval.py --agent0 agent_v5.py --agent1 agent_v3.py --games 20 --jobs 4` — record result
- [ ] T021 [US2] Write `experiments/2026-05-29-comet-opportunism.md` with hypothesis, change description, self-play result table, and conclusion
- [ ] T021a [US2] SC-3 regression check: run `uv run python eval.py --agent0 agent_v5.py --agent1 main.py --games 3 --verbose` and confirm sun-avoidance filter still fires correctly

**Checkpoint**: agent_v5 complete and evaluated. Sun-avoidance regression confirmed. Result recorded in experiments/.

---

## Phase 5: User Story 3 — Defensive Reinforcement (Priority: P3)

**Goal**: `agent_v6.py` dispatches reinforcements to owned planets threatened by inbound enemy fleets, holding at least `production × 10` ships in reserve.

**Independent Test**: `uv run python eval.py --agent0 agent_v6.py --agent1 agent_v3.py --games 20 --jobs 4` — record win rate. Pass ≥55%.

### Tasks — US3 Defensive Reinforcement

- [ ] T022 [P] [US3] Create `agent_v6.py` at project root as a copy of `agent_v3.py` — rename docstring to "Defensive Reinforcement Agent"
- [ ] T023 [P] [US3] Add `_heading_toward(fleet, planet)` helper to `agent_v6.py` per research.md R-3: dot-product of fleet direction vs vector to planet, return `True` if alignment > 0.95
- [ ] T024 [US3] Add `SAFETY_MULTIPLIER = 10` constant to `agent_v6.py`
- [ ] T025 [US3] In `agent_v6.py` `agent()` function, add a defense pre-pass before the attack loop: iterate enemy fleets, check `_heading_toward(f, mine)` for each owned planet, compute `arrival_turns = hypot(f.x-mine.x, f.y-mine.y) / fleet_speed(f.ships)`, compute `projected_garrison = mine.ships + mine.production * arrival_turns`, if `f.ships > projected_garrison` find nearest owned planet (other than `mine`) with `surplus = source.ships - source.production * SAFETY_MULTIPLIER > 0`, dispatch `min(surplus, int(f.ships - projected_garrison) + 1)` ships toward the threatened planet
- [ ] T026 [US3] Update `if __name__ == "__main__":` block in `agent_v6.py` to run `agent_v6 vs main.py` on seed 42
- [ ] T027 [US3] Run `uv run python agent_v6.py` — confirm it executes without error
- [ ] T028 [US3] Run `uv run python eval.py --agent0 agent_v6.py --agent1 agent_v3.py --games 20 --jobs 4` — record result
- [ ] T029 [US3] Write `experiments/2026-05-29-defensive-reinforce.md` with hypothesis, change description, self-play result table, and conclusion
- [ ] T029a [US3] SC-3 regression check: run `uv run python eval.py --agent0 agent_v6.py --agent1 main.py --games 3 --verbose` and confirm sun-avoidance filter still fires correctly; also spot-check turn time with a game that has many fleets (SC-4 — defense pre-pass is O(fleets × planets))

**Checkpoint**: agent_v6 complete and evaluated. Sun-avoidance and timing regressions confirmed. Result recorded in experiments/.

---

## Phase 6: User Story 4 — Fleet-Speed Scoring + Fast-Fleet Send (Priority: P2, bundled Gaps 4 & 5)

**Goal**: `agent_v7.py` scores targets by production/travel-turns (not raw distance) and always sends at least `MIN_FAST_FLEET = 10` ships to avoid crawling 1-ship fleets.

**Independent Test**: `uv run python eval.py --agent0 agent_v7.py --agent1 agent_v3.py --games 20 --jobs 4` — record win rate. Pass ≥55%.

### Tasks — US4 Fleet-Speed Scoring

- [ ] T030 [P] [US4] Create `agent_v7.py` at project root as a copy of `agent_v3.py` — rename docstring to "Fleet-Speed Scoring + Fast-Fleet Agent"
- [ ] T031 [P] [US4] Add `MIN_FAST_FLEET = 10` constant to `agent_v7.py`
- [ ] T032 [US4] In `agent_v7.py` targeting score, replace `production / (hypot(...) + EPSILON)` with `production / (hypot(...) / fleet_speed(mine.ships) + EPSILON)` so larger garrisons make far high-production planets score better
- [ ] T033 [US4] In `agent_v7.py` launch step, replace `ships_to_send = ships_needed` with `ships_to_send = max(ships_needed, MIN_FAST_FLEET)`, then cap at `mine.ships` — update `if mine.ships < ships_to_send: continue` guard accordingly
- [ ] T034 [US4] Update `if __name__ == "__main__":` block in `agent_v7.py` to run `agent_v7 vs main.py` on seed 42
- [ ] T035 [US4] Run `uv run python agent_v7.py` — confirm it executes without error
- [ ] T036 [US4] Run `uv run python eval.py --agent0 agent_v7.py --agent1 agent_v3.py --games 20 --jobs 4` — record result
- [ ] T037 [US4] Write `experiments/2026-05-29-fleet-speed-scoring.md` with hypothesis, change description, self-play result table, and conclusion
- [ ] T037a [US4] SC-3 regression check: run `uv run python eval.py --agent0 agent_v7.py --agent1 main.py --games 3 --verbose` and confirm sun-avoidance filter still fires correctly

**Checkpoint**: agent_v7 complete and evaluated. Sun-avoidance regression confirmed. All four isolated experiments done.

---

## Phase 7: User Story 5 — Combined Agent (Priority: P1 gate)

**Goal**: `agent_v8.py` stacks all mechanics from US1–US4 whose isolated agents passed ≥55% win rate, then is evaluated against agent_v3.

**Dependency**: Requires T013, T021, T029, T037 (all isolated experiment logs) to determine which mechanics to include.

**Independent Test**: `uv run python eval.py --agent0 agent_v8.py --agent1 agent_v3.py --games 20 --jobs 4` — pass ≥55%.

### Tasks — US5 Combined Agent

- [ ] T038 [US5] Review experiments/2026-05-29-orbit-lead.md, comet-opportunism.md, defensive-reinforce.md, fleet-speed-scoring.md — list which mechanics passed ≥55%
- [ ] T039 [US5] Create `agent_v8.py` at project root as a copy of `agent_v3.py` — rename docstring to "Combined Agent (stacked passing mechanics)"
- [ ] T040 [US5] Integrate orbit-lead prediction into `agent_v8.py` (from agent_v4) if it passed — add `_predict_planet_pos` and update targeting loop
- [ ] T041 [US5] Integrate comet opportunism into `agent_v8.py` (from agent_v5) if it passed — add `_build_comet_path_lookup` and update targeting loop
- [ ] T042 [US5] Integrate defensive reinforcement pre-pass into `agent_v8.py` (from agent_v6) if it passed — add `_heading_toward` and SAFETY_MULTIPLIER, add pre-pass before attack loop
- [ ] T043 [US5] Integrate fleet-speed scoring + MIN_FAST_FLEET into `agent_v8.py` (from agent_v7) if it passed — update score formula and launch logic
- [ ] T044 [US5] Update `if __name__ == "__main__":` block in `agent_v8.py` to run `agent_v8 vs main.py` on seed 42
- [ ] T045 [US5] Run `uv run python agent_v8.py` — confirm it executes without error
- [ ] T046 [US5] Run `uv run python eval.py --agent0 agent_v8.py --agent1 agent_v3.py --games 20 --jobs 4` — record result
- [ ] T047 [US5] Run second 20-game eval: `uv run python eval.py --agent0 agent_v8.py --agent1 agent_v3.py --games 20 --jobs 4` a second time (same seeds 0–19 — `eval.py` always uses `range(num_games)` as seeds). Confirm ≥55% win rate reproduces; same-seed reproducibility rules out run-to-run randomness (the engine is deterministic given a seed)
- [ ] T048 [US5] Write `experiments/2026-05-29-combined-agent.md` with hypothesis, stacked mechanics list, self-play result table, and conclusion

**Checkpoint**: Combined agent evaluated. Best agent identified.

---

## Phase 8: Polish

**Purpose**: Documentation and cleanup after experiments are complete.

- [ ] T049 [P] Update `specs/003-agent-gap-analysis/spec.md` Status field from "Draft" to "Complete"
- [ ] T050 [P] Confirm no agent file was modified (only new files created): `git diff agent_v3.py agent_v2.py main.py` should be empty

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all experiments
- **US1–US4 (Phases 3–6)**: All depend only on Phase 2 — **fully parallel with each other**
- **US5 (Phase 7)**: Depends on all four isolated experiment logs (T013, T021, T029, T037)
- **Polish (Phase 8)**: Depends on Phase 7

### User Story Dependencies

- **US1 (orbit-lead)**: Independent after Phase 2
- **US2 (comets)**: Independent after Phase 2
- **US3 (defense)**: Independent after Phase 2
- **US4 (speed scoring)**: Independent after Phase 2
- **US5 (combined)**: Depends on US1–US4 eval results

### Parallel Opportunities

- T006–T013 (US1), T014–T021 (US2), T022–T029 (US3), T030–T037 (US4) — all four experiment groups can run simultaneously in four terminal windows
- Within each experiment: T006/T007 (agent creation + helper) can run in parallel
- T049/T050 (polish) can run in parallel

---

## Parallel Execution Example: All Four Isolated Experiments

```bash
# Terminal 1 (US1)
uv run python eval.py --agent0 agent_v4.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 2 (US2)
uv run python eval.py --agent0 agent_v5.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 3 (US3)
uv run python eval.py --agent0 agent_v6.py --agent1 agent_v3.py --games 20 --jobs 4

# Terminal 4 (US4)
uv run python eval.py --agent0 agent_v7.py --agent1 agent_v3.py --games 20 --jobs 4
```

---

## Implementation Strategy

### MVP (US1 only — highest-impact gap)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (orbit-lead targeting — agent_v4)
4. **STOP and VALIDATE**: Did agent_v4 beat agent_v3 at ≥55%?
5. If yes: US1 mechanic is validated; continue to other experiments

### Full Isolated Experiment Run

1. Phases 1–2: Setup + Foundational
2. Phases 3–6: Implement all four experiment agents in parallel (one per terminal)
3. Record all four eval results
4. Phase 7: Build and eval combined agent with passing mechanics
5. Phase 8: Polish

### Single-Developer Sequential Order

If working alone, priority order: US1 → US2 → US4 → US3 (orbit-lead most impactful,
defense most complex).

---

## Notes

- [P] tasks = different files, no dependencies on other in-progress tasks
- Each agent file is fully self-contained — no shared module imports
- `eval.py` needs no modifications
- Never modify `agent_v3.py`, `agent_v2.py`, or `main.py`
- Each experiment log in `experiments/` is required before any Kaggle submission (constitution IV)
- Win rate threshold: ≥55% = 11+ wins out of 20 games
