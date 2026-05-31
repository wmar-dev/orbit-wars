# Tasks: Replay-Informed Agent Improvements

**Input**: Design documents from `specs/012-replay-informed-improvements/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: No test tasks — not requested in spec. Evaluation via `eval.py` is the verification mechanism.

**Organization**: Tasks grouped by user story (P1 = production priority, P2 = coordinated attacks, P3 = banking phase), preceded by foundational scaffolding shared across all stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create agent_v40.py from agent_v38.py and establish variant flag scaffolding. No functional changes yet.

- [x] T001 Copy agent_v38.py to agent_v40.py at repo root
- [x] T002 Add variant flag constants to top of agent_v40.py: `BANKING_VARIANT = "B"`, `FALLBACK_VARIANT = "C"`, and all new constants from data-model.md (`PROD_WEIGHT`, `DIST_WEIGHT`, `MAX_PROD`, `MAX_DIST`, `HIGH_PROD_THRESHOLD`, `ENEMY_PENALTY`, `MAX_SHIPS_ESTIMATE`, `BANK_PROD_THRESHOLD`, `BANK_FIXED_THRESHOLD`, `BANK_TURNS_FACTOR`, `BANK_STEP_CAP`, `BANK_ADAPTIVE_THRESHOLD`, `RACE_EPSILON`)
- [x] T003 Verify agent_v40.py passes smoke test: `make test` or `python eval.py --agent0 agent_v40.py --agent1 random --games 3 --seed 0` passes without errors

**Checkpoint**: agent_v40.py is a clean copy of agent_v38.py with new constants — functionally identical to agent_v38 at this point.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared helper functions used by all three user stories. Must complete before any US1/US2/US3 work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Add `_planet_value(planet, source_x, source_y)` function to agent_v40.py: returns `PROD_WEIGHT * (planet.production / MAX_PROD) - DIST_WEIGHT * (math.hypot(planet.x - source_x, planet.y - source_y) / MAX_DIST)` — used by US1, US2, US3
- [x] T005 [P] Add `_enemy_incoming(target_x, target_y, raw_fleets, player)` function to agent_v40.py: iterates enemy fleets, uses `_angle_diff` with `RACE_EPSILON=0.2` to count ships heading toward target — used by US1 race-condition logic
- [x] T006 [P] Add `_banking_mode(my_planets, enemy_planets, step, variant)` function to agent_v40.py: implements all three variants (A/B/C) from data-model.md BankingPhaseState — used by US3
- [x] T007 Verify T004–T006 are importable and callable: run `python -c "import agent_v40"` with no errors

**Checkpoint**: Shared helpers exist and import cleanly. agent_v40 still behaves identically to agent_v38 (helpers not yet wired into `agent()`).

---

## Phase 3: User Story 1 — Production-Weighted Planet Priority (Priority: P1) 🎯 MVP

**Goal**: Replace the ROI-based scoring in agent_v40 with the production-weighted value function, and add race-condition fleet scaling. The agent should now prefer high-production planets over close low-production ones.

**Independent Test**: `python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0` — agent_v40 should show measurably different planet selection vs agent_v38 (check via game logs or replay inspection).

- [x] T008 [US1] In `agent()` in agent_v40.py, compute scored target list: for each non-owned planet, call `_planet_value(t, mine.x, mine.y)` (using nearest owned planet as source) and sort descending — replace the `_roi`-based candidate selection
- [x] T009 [US1] Wire `_enemy_incoming` into fleet size calculation in agent_v40.py: for each candidate neutral target, compute `enemy_inc = _enemy_incoming(tx, ty, raw_fleets, player)` and set `ships_needed = max(target.ships + 1, target.ships + enemy_inc + 1)`
- [x] T010 [US1] Implement FallbackTargetSet logic in agent_v40.py: when no neutral planets with `production >= HIGH_PROD_THRESHOLD` exist, activate fallback mode per `FALLBACK_VARIANT` — Variant A: target highest-value enemy high-prod planet; Variant C: target lowest `ships/production` enemy high-prod planet while also queuing neutral targets as secondaries
- [x] T011 [US1] Run smoke test to confirm no errors: `python eval.py --agent0 agent_v40.py --agent1 random --games 5 --seed 0`

**Checkpoint**: agent_v40 uses production-weighted scoring and scales fleet size for contested targets. Can be evaluated vs agent_v38 independently.

---

## Phase 4: User Story 2 — Coordinated Multi-Planet Assault (Priority: P2)

**Goal**: Replace the single-sender `best_sender` model with top-target grouping so multiple planets send toward the same target in the same turn.

**Independent Test**: In a replayed game vs agent_v38, inspect that ≥2 owned planets send fleets at nearly identical angles (within 0.3 rad) in the same turn during mid-game.

- [x] T012 [US2] Remove `best_sender` dict and single-sender loop from `agent()` in agent_v40.py
- [x] T013 [US2] Implement top-target grouping in `agent()` in agent_v40.py: (1) get sorted target list from T008; (2) `primary_target` = top of list; (3) for each owned planet with `surplus > 0` and not departing/evacuating, compute predicted position of `primary_target` via `_converged_orbit_lead` or `_comet_two_pass`, check `_path_safe`, then append `[mine.id, angle, ships_to_send]` — all surplus planets join the wave
- [x] T014 [US2] Implement secondary target assignment in agent_v40.py: after assigning all surplus planets to `primary_target`, collect planets that could not send to primary (path blocked, zero surplus) and assign them to `secondary_target` (second item in scored list) using same orbit-lead + path-safe logic
- [x] T015 [US2] Run smoke test: `python eval.py --agent0 agent_v40.py --agent1 random --games 5 --seed 0`

**Checkpoint**: agent_v40 sends coordinated waves. Multiple planets targeting the same destination in a single turn. Can be evaluated vs agent_v38 independently.

---

## Phase 5: User Story 3 — Ship-Banking Phase (Priority: P3)

**Goal**: Add banking mode so agent_v40 suppresses attacks when it holds a production advantage and ships are below threshold, then launches a coordinated assault once the threshold is met.

**Independent Test**: In a game where agent_v40 holds production advantage by step 100, observe ≥20 consecutive turns of ship accumulation before a large offensive wave.

- [x] T016 [US3] Wire `_banking_mode()` into `agent()` in agent_v40.py: at the top of the main targeting loop, call `_banking_mode(my_planets, enemy_planets, step, BANKING_VARIANT)` — if True, skip the coordinated attack loop entirely (return only evacuation moves)
- [x] T017 [US3] Extract `step` from observation in agent_v40.py: `step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)` — needed by Variant C banking logic
- [x] T018 [US3] Extract enemy planet list in agent_v40.py: `enemy_planets = [p for p in planets if p.owner != player and p.owner != -1]` — needed by `_banking_mode` for production advantage calculation
- [x] T019 [US3] Run smoke test: `python eval.py --agent0 agent_v40.py --agent1 random --games 5 --seed 0`

**Checkpoint**: agent_v40 enters banking mode when conditions are met. All three user stories now implemented in agent_v40.py.

---

## Phase 6: Variant Evaluation & Selection

**Purpose**: Run all 6 variant combinations, record results, select winner as agent_v40.

- [x] T020 Run eval for variant A-A (BANKING_VARIANT="A", FALLBACK_VARIANT="A"): set constants at top of agent_v40.py, run `python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0`, record win rate
- [x] T021 [P] Run eval for variant A-C (BANKING_VARIANT="A", FALLBACK_VARIANT="C"): set constants, run eval, record win rate
- [x] T022 [P] Run eval for variant B-A (BANKING_VARIANT="B", FALLBACK_VARIANT="A"): set constants, run eval, record win rate
- [x] T023 [P] Run eval for variant B-C (BANKING_VARIANT="B", FALLBACK_VARIANT="C"): set constants, run eval, record win rate
- [x] T024 [P] Run eval for variant C-A (BANKING_VARIANT="C", FALLBACK_VARIANT="A"): set constants, run eval, record win rate
- [x] T025 [P] Run eval for variant C-C (BANKING_VARIANT="C", FALLBACK_VARIANT="C"): set constants, run eval, record win rate
- [x] T026 Create experiment record `experiments/012-replay-informed.md` with results table: columns = Run, Banking Variant, Fallback Variant, Win Rate vs agent_v38 (50 games seed 0), Notes
- [ ] T027 Set winning variant constants (highest win rate) permanently in agent_v40.py
- [ ] T028 Run final confirmation eval: `python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0` — confirm ≥60% win rate (SC-001)

**Checkpoint**: Best variant locked in. agent_v40 beats agent_v38 in local eval.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Update project metadata and validate Principle VI compliance.

- [ ] T029 Update README.md Agents table: add agent_v40 row with win rate vs agent_v38, bold it as current best agent
- [ ] T030 Update Makefile: set `AGENT` and `RENDER_AGENT` to `agent_v40.py`
- [ ] T031 Run Principle VI compliance check on agent_v40.py: `grep -n "^from \|^import " agent_v40.py | grep -v "kaggle_environments\|math\|random\|collections\|itertools\|functools\|heapq\|copy\|typing\|abc\|os\|sys"` — output must be empty
- [ ] T032 Run final `make test` to confirm agent_v40 passes smoke tests

**Checkpoint**: Project metadata updated. agent_v40 is the documented current best agent.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — blocks all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — can start immediately after
- **US2 (Phase 4)**: Depends on Phase 3 — builds on the scoring changes from US1
- **US3 (Phase 5)**: Depends on Phase 4 — banking mode interacts with the coordination loop
- **Variant Eval (Phase 6)**: Depends on Phase 5 — all three stories must be implemented
- **Polish (Phase 7)**: Depends on Phase 6 — winner must be selected first

### Within-Phase Parallelism

- T004, T005, T006 (Phase 2 helpers) can be written in parallel — different functions, no inter-dependency
- T020–T025 (variant eval runs) can be run in parallel if multiple terminals available — each uses a different constant combination

---

## Parallel Execution Example: Phase 2

```bash
# Write all three helper functions in parallel (different functions, same file — sequence carefully):
# T004: _planet_value()
# T005: _enemy_incoming()
# T006: _banking_mode()
# Then T007: verify all import cleanly
```

## Parallel Execution Example: Phase 6

```bash
# Run variant evals in parallel (6 terminal windows, different constant settings):
# T020: BANKING_VARIANT="A", FALLBACK_VARIANT="A"
# T021: BANKING_VARIANT="A", FALLBACK_VARIANT="C"
# T022: BANKING_VARIANT="B", FALLBACK_VARIANT="A"
# T023: BANKING_VARIANT="B", FALLBACK_VARIANT="C"
# T024: BANKING_VARIANT="C", FALLBACK_VARIANT="A"
# T025: BANKING_VARIANT="C", FALLBACK_VARIANT="C"
# All 50-game runs take ~same wall time; results ready simultaneously
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T007)
3. Complete Phase 3: User Story 1 (T008–T011)
4. **STOP and VALIDATE**: Run `python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 20 --seed 0`
5. If win rate improvement visible, proceed to US2

### Full Incremental Delivery

1. Setup + Foundational → agent_v40 is agent_v38 clone with helpers
2. US1 → production-weighted scoring live → quick eval check
3. US2 → coordinated attacks live → quick eval check
4. US3 → banking phase live → full 6-variant eval
5. Phase 6 → winner selected → Phase 7 → done

---

## Notes

- [P] tasks = parallelizable (different functions or eval runs)
- Phases 3–5 are sequential — each story builds on the previous one's changes to `agent()`
- `make test` = smoke test vs random agent; `eval.py --games 50` = proper benchmark
- The variant flags (`BANKING_VARIANT`, `FALLBACK_VARIANT`) allow running all 6 evals from a single agent file by changing two constants
- Kaggle submission is out of scope — stop after Phase 7
