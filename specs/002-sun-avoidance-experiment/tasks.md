# Tasks: Sun Avoidance Experiment

**Input**: Design documents from `specs/002-sun-avoidance-experiment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/agent-interface.md, quickstart.md

**Organization**: Tasks are grouped by user story. No tests requested — implementation tasks only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify environment and confirm all prerequisite infrastructure is in place before writing new code.

- [ ] T001 Verify eval.py supports arbitrary --agent0 and --agent1 flags by running `uv run python eval.py --agent0 agent_v2.py --agent1 main.py --games 1` and confirming it exits cleanly
- [ ] T002 [P] Verify experiments/ directory exists at project root; create it if missing

**Checkpoint**: Setup complete — ready to implement agent_v3.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the sun-path safety helper that all agent logic depends on. Must be complete before any user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 Implement `_segment_dist_to_sun(ax, ay, bx, by) -> float` as a module-level helper in `agent_v3.py` using the formula from plan.md Phase 1 Core Algorithm Delta. Constants: `CENTER = 50.0`, `SUN_RADIUS = 10.0`, `SAFETY_MARGIN = 2.0`, `SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN`. Verify with a quick sanity check: `_segment_dist_to_sun(10, 50, 90, 50)` should return ~0 (path crosses center); `_segment_dist_to_sun(10, 10, 90, 10)` should return ~40 (path far from sun).
- [ ] T004 Copy the full `agent(obs)` function body from `agent_v2.py` into `agent_v3.py` as the starting point, preserving all constants (`EPSILON`, `RANGE_FACTOR`) and the `Planet` import. File: `agent_v3.py`

**Checkpoint**: Foundation ready — `agent_v3.py` exists with helper and base agent logic

---

## Phase 3: User Story 1 — Sun-Safe Agent Survives Where Others Are Destroyed (Priority: P1) 🎯 MVP

**Goal**: The new agent never routes fleets through the sun; zero sun-collision losses across 10 seeded games.

**Independent Test**: Run `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10` and confirm the game log contains no unexpected early-termination patterns (fleets disappearing mid-flight). Also run `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 1 --verbose` and inspect move log for evidence that sun-crossing targets are skipped.

### Implementation for User Story 1

- [ ] T005 [US1] In `agent_v3.py`, replace the candidate-filter block in `agent()` with the sun-safe version from plan.md Phase 1 Core Algorithm Delta: filter candidates to `sun_safe AND in_range`; add fallback to all sun-safe targets if no in-range safe candidates exist; add `continue` if no safe candidates at all. File: `agent_v3.py`
- [ ] T006 [US1] Add module docstring to `agent_v3.py` describing the strategy: production-weighted targeting (inherited from agent_v2) plus sun-path avoidance via segment-distance check. File: `agent_v3.py`
- [ ] T007 [US1] Smoke-test `agent_v3.py` against `main.py` for 1 game to confirm no crashes and valid return format: `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 1`

**Checkpoint**: User Story 1 complete — agent_v3.py runs cleanly without sun collisions

---

## Phase 4: User Story 2 — Comparative Win Rate Evaluated Against Baseline and v2 (Priority: P2)

**Goal**: Run both evaluation pairings (agent_v3 vs main.py, agent_v3 vs agent_v2) and produce clear win-rate results for analysis.

**Independent Test**: `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10` prints aggregate win rate. `uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 10` prints aggregate win rate. Both complete within 30 seconds each.

### Implementation for User Story 2

- [ ] T008 [US2] Run head-to-head evaluation — agent_v3 vs baseline: `uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10` and record the per-game results and aggregate win rate.
- [ ] T009 [US2] Run head-to-head evaluation — agent_v3 vs agent_v2: `uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 10` and record the per-game results and aggregate win rate.
- [ ] T010 [US2] Run a 3-game verbose comparison to observe strategy differences: `uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 3 --verbose` and note any turns where agent_v3 skips a target that agent_v2 would attack.

**Checkpoint**: Both win rates measured; developer can draw a conclusion about whether sun avoidance is a net positive strategy.

---

## Phase 5: User Story 3 — Experiment Results Recorded (Priority: P3)

**Goal**: Results documented in the experiments log so the finding persists and satisfies Constitution Principle IV before any Kaggle submission.

**Independent Test**: File `experiments/2026-05-29-sun-avoidance.md` exists, contains all required fields (hypothesis, change, self-play results for both pairings, conclusion), and a reviewer can understand the strategic trade-off without running code.

### Implementation for User Story 3

- [ ] T011 [US3] Create `experiments/2026-05-29-sun-avoidance.md` with all required constitution fields: **Hypothesis** (sun avoidance eliminates fleet losses and may improve overall win rate), **Change** (segment-distance filter added to target selection in agent_v3.py), **Self-play result** (win rates from T008 and T009), **Conclusion** (net positive / neutral / negative assessment of sun avoidance strategy). File: `experiments/2026-05-29-sun-avoidance.md`
- [ ] T012 [US3] Update `README.md` agents table to add a row for `agent_v3.py` with strategy description and win rate vs baseline (result from T008). File: `README.md`

**Checkpoint**: All three user stories complete. Constitution IV satisfied. Experiment documented.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup across all deliverables.

- [ ] T013 [P] Verify `agent_v3.py` is self-contained (no imports beyond `math` and `kaggle_environments.envs.orbit_wars.orbit_wars.Planet`) and compatible with Kaggle submission format by reviewing all import statements
- [ ] T014 Run the full quickstart.md validation sequence: smoke test (T007), both 10-game evals (T008, T009), confirm all print within 30 seconds each

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 — implements the agent
- **User Story 2 (Phase 4)**: Depends on Phase 3 (needs agent_v3.py working) — runs evaluations
- **User Story 3 (Phase 5)**: Depends on Phase 4 (needs eval results) — records findings
- **Polish (Phase 6)**: Depends on Phase 5 — final check

### Task-Level Dependencies

- T003 → T004 (helper must exist before agent body is copied in; they go in the same file)
- T004 → T005 (base agent body must exist before modifying candidate filter)
- T005 → T006 → T007 (implement, document, then smoke test)
- T007 → T008, T009 (agent must pass smoke test before full evals)
- T008, T009, T010 → T011 (eval results needed for experiment log)
- T011 → T012 (experiment conclusion needed before README update)

### Parallel Opportunities

- T001 and T002 can run in parallel (Phase 1)
- T008, T009, T010 can run in parallel once T007 passes (different agent pairings)
- T013 can run in parallel with any phase after T004

---

## Parallel Example: Phase 4 Evaluations

```bash
# Once agent_v3.py passes smoke test (T007), launch all three eval runs together:
Task T008: "uv run python eval.py --agent0 agent_v3.py --agent1 main.py --games 10"
Task T009: "uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 10"
Task T010: "uv run python eval.py --agent0 agent_v3.py --agent1 agent_v2.py --games 3 --verbose"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T007)
4. **STOP and VALIDATE**: Confirm agent_v3 runs without crashes and skips sun-crossing targets
5. Proceed to Phase 4 for comparative evaluation

### Full Experiment Sequence

1. Setup + Foundational → `agent_v3.py` exists and has helper
2. User Story 1 → Agent filters sun-crossing targets; smoke test passes
3. User Story 2 → Both eval pairings run; win rates recorded
4. User Story 3 → Experiment log and README updated
5. Polish → Final import/format check; quickstart validated

---

## Notes

- [P] tasks = different files or independent runs, no shared state
- [Story] label maps task to the user story it delivers
- No tests requested — implementation and evaluation tasks only
- Commit after each phase checkpoint
- Constitution IV gate: `experiments/2026-05-29-sun-avoidance.md` MUST exist before any Kaggle submission
- The `eval.py` harness is used unchanged — no modifications to that file
