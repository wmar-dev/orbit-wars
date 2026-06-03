# Tasks: Agent Strategic Improvements — Beam Search, Fleet Coordination, Defense

**Input**: Design documents from `specs/019-agent-mcts-coordination-defense/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks grouped by user story (experiment variant) for independent implementation and evaluation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to spec.md user stories (US1=Beam Search, US2=Coordination, US3=Defense, US4=Combined)

---

## Phase 1: Setup

**Purpose**: Create experiment doc skeleton before writing any agent code.

- [x] T001 Create experiment doc at `experiments/2026-06-02-019-agent-strategic-improvements.md` with sections for each variant (Coordination, Defense, Beam Search, Combined): Hypothesis, Change, Self-play result, Conclusion

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Verify timing budget and establish the forward simulation model shared by all experiments.

- [x] T002 Measure agent_v58 per-turn timing to confirm beam search budget: run `uv run python -c "..."` to time 500 calls to agent over a full game and confirm avg < 2ms (already measured at 0.29ms avg — document in experiment doc)
- [x] T003 Prototype the `_SimState` forward model in a scratch script `scratch_sim.py`: implement `SimPlanet(id, owner, ships, production)`, `SimFleet(owner, target_id, ships, eta)`, `SimState.step()` (grow ships, decrement eta, resolve arrivals), and `SimState.score(player)` — verify with a 3-planet manual test case that simulation matches expected outcome after 5 steps

**Checkpoint**: Forward model validated — all story implementations can proceed.

---

## Phase 3: User Story 2 — Fleet Coordination (Priority: P2) 🎯 MVP

**Goal**: Eliminate redundant fleet dispatches by checking in-transit own fleet coverage before dispatching.

**Independent Test**: Run `uv run python eval.py --agent0 agent_v59_coord.py --agent1 agent_v58.py --games 50 --jobs 4` and verify win rate ≥53%. Also: manually inspect a game trace to confirm no two own fleets head to the same neutral.

### Implementation for User Story 2

- [x] T004 [US2] Create `agent_v59_coord.py` by copying `agent_v58.py` and updating the docstring to describe the coverage fix
- [x] T005 [US2] Add coverage dict to `agent_v59_coord.py`: after the fleet parsing loop (~line 260), scan `raw_fleets` for own in-transit fleets and build `coverage = {target_planet_id: ships_in_transit}` by finding which planet each fleet is heading toward (use `_angle_diff` against all planet positions to find best-matching target)
- [x] T006 [US2] Add coverage check to the dispatch loop in `agent_v59_coord.py` (~line 406): before `moves.append`, check `if coverage.get(best_target.id, 0) >= ships_needed: continue` and after dispatching update `coverage[best_target.id] += ships_needed`
- [x] T007 [US2] Run 50-game eval: `uv run python eval.py --agent0 agent_v59_coord.py --agent1 agent_v58.py --games 50 --jobs 4` and record win rate
- [x] T008 [US2] Record Experiment A (Coordination) results in `experiments/2026-06-02-019-agent-strategic-improvements.md`

**Checkpoint**: Fleet coordination complete with documented win rate vs v58.

---

## Phase 4: User Story 3 — Defensive Reinforcement (Priority: P2)

**Goal**: Dispatch reinforcement to owned planets with incoming enemy fleets when economically justified.

**Independent Test**: Run 50-game eval vs v58; expect win rate ≥53%. Also: trace a game where the agent defends a threatened high-production planet that v58 would lose.

### Implementation for User Story 3

- [x] T009 [P] [US3] Create `agent_v59_defense.py` by copying `agent_v58.py` and updating the docstring
- [x] T010 [US3] Add `_threat_eta(planet, raw_fleets, player)` helper to `agent_v59_defense.py`: scan raw_fleets for enemy fleets (owner != player), use `_angle_diff(f_angle, math.atan2(planet.y - f_y, planet.x - f_x)) < ANGLE_EPSILON` to identify threats to that planet, estimate eta as `math.hypot(f_x - planet.x, f_y - planet.y) / fleet_speed(f_ships)`, return `(incoming_ships, eta_steps)` for the worst/nearest threat fleet
- [x] T011 [US3] Add defense pre-pass to `agent_v59_defense.py` inside `agent()`, after `threat` dict is built and before `best_sender` loop: for each owned planet P where `threat.get(P.id, 0) > 0` and `P.production >= 2.0`, call `_threat_eta`, skip if planet can hold alone (`P.ships + P.production * eta >= incoming`), otherwise find nearest allied planet Q (not in `dispatched_defenders`) that has `surplus >= reinforcement_needed` and can arrive at P before or with the enemy fleet (`math.hypot(Q.x-P.x, Q.y-P.y) / fleet_speed(needed) <= eta`), dispatch reinforcement, add Q.id to `dispatched_defenders` set; skip Q in the main loop if it's in `dispatched_defenders`
- [x] T012 [US3] Run 50-game eval: `uv run python eval.py --agent0 agent_v59_defense.py --agent1 agent_v58.py --games 50 --jobs 4` and record win rate
- [x] T013 [US3] Record Experiment B (Defense) results in `experiments/2026-06-02-019-agent-strategic-improvements.md`

**Checkpoint**: Defensive reinforcement complete with documented win rate vs v58.

---

## Phase 5: User Story 1 — Beam Search (Priority: P1)

**Goal**: Evaluate multiple candidate action sets using a forward simulation, selecting the one with the highest projected production advantage.

**Independent Test**: Run 50-game eval vs v58; expect win rate ≥55%. Also: verify per-turn timing stays < 800ms by adding a timing assertion in debug mode.

### Implementation for User Story 1

- [x] T014 [US1] Create `agent_v59_beam.py` by copying `agent_v58.py` and updating docstring; add constants `BEAM_DEPTH = 5`, `BEAM_CANDIDATES = 30`, `BEAM_TIMEOUT_MS = 800`
- [x] T015 [US1] Inline the forward simulation classes into `agent_v59_beam.py` (before the `agent` function): implement `_SimPlanet`, `_SimFleet`, `_SimState` with `step()` and `score(player)` methods — port the validated logic from `scratch_sim.py` (T003)
- [x] T016 [US1] Add `_build_sim_state(planets, raw_fleets, initial_planets_map, angular_velocity)` to `agent_v59_beam.py`: convert live Planet objects and raw fleet tuples into `_SimState`; compute fleet ETAs using `math.hypot(fleet_x - target_x, fleet_y - target_y) / fleet_speed(fleet_ships)`; use planet closest to fleet angle as target identification
- [x] T017 [US1] Add `_gen_candidates(my_planets, targets, greedy_moves, planets, initial_planets_map, angular_velocity)` to `agent_v59_beam.py`: produce up to BEAM_CANDIDATES action sets — (1) greedy baseline, (2) for each owned planet swap its greedy target to 2nd-best ROI candidate, (3) for the top-3 ROI neutrals generate a "swarm" variant sending all mines there, (4) hold-all; return list of `(label, dispatches_list)` tuples where each dispatch is `(source_id, target_angle, ships)`
- [x] T018 [US1] Add `_beam_search(obs, greedy_moves, planets, my_planets, targets, initial_planets_map, angular_velocity, raw_fleets, step)` to `agent_v59_beam.py`: build base `_SimState`, iterate candidates, for each apply dispatches to a copy of the state via `_sim_step` loop (BEAM_DEPTH iterations), score the terminal state, track best-scoring candidate; include timeout guard (`time.perf_counter()` check after each candidate — return greedy_moves if elapsed > BEAM_TIMEOUT_MS/1000); return best candidate's dispatches as `moves` list
- [x] T019 [US1] Wire up `_beam_search` at the end of `agent()` in `agent_v59_beam.py`: replace the final `return moves` with `return _beam_search(obs, moves, planets, my_planets, targets, initial_planets_map, angular_velocity, raw_fleets, step)`
- [x] T020 [US1] Run 50-game eval: `uv run python eval.py --agent0 agent_v59_beam.py --agent1 agent_v58.py --games 50 --jobs 4` and record win rate
- [x] T021 [US1] Record Experiment C (Beam Search) results in `experiments/2026-06-02-019-agent-strategic-improvements.md`

**Checkpoint**: Beam search complete with documented win rate and timing confirmation.

---

## Phase 6: User Story 4 — Combined Agent (Priority: P3)

**Goal**: Combine all three improvements into `agent_v59.py` and confirm win rate ≥55% vs v58.

**Independent Test**: Run 50-game eval vs v58; expect ≥55%. If ≥55% confirmed, run 100-game eval for submission confidence.

### Implementation for User Story 4

- [x] T022 [US4] Create `agent_v59.py` by copying `agent_v59_beam.py` and updating docstring to describe all three improvements
- [x] T023 [US4] Add fleet coordination coverage dict and check to `agent_v59.py` (from T005-T006): build `coverage` from in-transit own fleets; check coverage before each dispatch in both the normal loop and the beam search candidate generation
- [x] T024 [US4] Add defense pre-pass to `agent_v59.py` (from T010-T011): run `_threat_eta` and defense dispatch before beam search; pass `dispatched_defenders` to `_gen_candidates` to exclude defending mines from beam search candidate generation
- [x] T025 [US4] Run 50-game eval: `uv run python eval.py --agent0 agent_v59.py --agent1 agent_v58.py --games 50 --jobs 4` and record win rate
- [x] T026 [US4] If win rate ≥55%: run 100-game confirmation `uv run python eval.py --agent0 agent_v59.py --agent1 agent_v58.py --games 100 --jobs 4`
- [x] T027 [US4] Record Experiment D (Combined) results in `experiments/2026-06-02-019-agent-strategic-improvements.md` with conclusion and submission recommendation

**Checkpoint**: Combined agent evaluated; submission candidate identified.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T028 [P] Update `README.md` agents table: add row for `agent_v59.py` with win rate vs v58; bold best agent
- [x] T029 Update `Makefile`: set `AGENT := agent_v59.py` and `RENDER_AGENT ?= agent_v59.py` only if win rate vs v58 > 50% (verified ≥50 games)
- [ ] T030 Delete `scratch_sim.py` after forward model is validated and inlined into agent_v59_beam.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No deps — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1
- **Phase 3 (US2)** and **Phase 4 (US3)**: Both depend on Phase 2; can run in parallel with each other
- **Phase 5 (US1)**: Depends on Phase 2 (forward model from T003); independent of Phase 3/4
- **Phase 6 (US4)**: Depends on Phases 3, 4, 5 all complete
- **Polish (Phase 7)**: Depends on Phase 6

### User Story Dependencies

- **US2 (Coordination) and US3 (Defense)**: Independent — can develop in parallel (T004–T008 ∥ T009–T013)
- **US1 (Beam Search)**: Depends on T003 forward model prototype only
- **US4 (Combined)**: Depends on US1+US2+US3

### Parallel Opportunities

- T004–T008 (coordination) ∥ T009–T013 (defense) — different files, no shared state
- T014–T019 (beam search) can overlap with T007–T008 and T012–T013 (eval + recording)
- T028 (README) ∥ T029 (Makefile) in Phase 7

---

## Implementation Strategy

### MVP First (User Story 2 — Fleet Coordination only)

1. T001–T003: Setup + forward model prototype
2. T004–T008: Fleet coordination variant
3. **STOP and VALIDATE**: 50-game eval vs v58
4. If ≥53%: proceed to Defense (US3) and Beam Search (US1) in parallel

### Incremental Delivery

1. T001–T003: Foundation
2. T004–T008: Coordination (simplest, validates pattern)
3. T009–T013: Defense (moderate complexity)
4. T014–T021: Beam search (largest, highest ceiling)
5. T022–T027: Combined v59
6. T028–T030: Polish

### Parallel Strategy (two tracks)

After Phase 2:
- Track A: T004–T008 (coordination)
- Track B: T009–T013 (defense) and T014–T021 (beam search, sequential within B)

---

## Notes

- Eval commands: `uv run python eval.py --agent0 X --agent1 agent_v58.py --games 50 --jobs 4`
- Timing: agent_v58 is 0.29ms avg — beam search with 30 candidates × 5 turns ≈ 5ms, well under 800ms guard
- Fleet target identification in coverage/ETA: use `_angle_diff(fleet_angle, atan2(planet.y-fy, planet.x-fx)) < ANGLE_EPSILON` (same pattern as existing threat detection in agent_v58.py:270-273)
- Defense threshold: `P.production >= 2.0` — avoids defending low-value planets
- Beam search score: `sum(p.production for p in sim.planets if p.owner == player) - sum(p.production for p in sim.planets if p.owner != player and p.owner >= 0)`
- Delete `scratch_sim.py` (T030) before committing final code
