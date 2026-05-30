# Tasks: Beat the Getting Started Agent

**Input**: Design documents from `specs/001-beat-starter-agent/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Not requested — no test tasks generated.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [ ] T001 Create `experiments/` directory at project root
- [ ] T002 [P] Create experiment log skeleton at `experiments/2026-05-29-production-weighted-baseline.md` with required fields: Hypothesis, Change, Self-play result, Conclusion (required by Constitution Principle IV before any Kaggle submission)

**Checkpoint**: Experiment log skeleton in place — constitution gate satisfied

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core agent scaffolding that both the agent and eval harness depend on

**⚠️ CRITICAL**: Must be complete before user story phases begin

- [ ] T003 Create `agent_v2.py` at project root with the module docstring, imports (`math`, `Planet` from `kaggle_environments.envs.orbit_wars.orbit_wars`), and the empty `agent(obs)` function signature — no logic yet
- [ ] T004 Create `eval.py` at project root with imports (`argparse`, `importlib.util`, `kaggle_environments.make`) and the CLI argument parser (`--games`, `--agent0`, `--agent1`) — no game loop yet

**Checkpoint**: Both files exist and are importable; foundation ready for story implementation

---

## Phase 3: User Story 1 - New Agent Beats Baseline (Priority: P1) 🎯 MVP

**Goal**: `agent_v2.py` uses production-weighted targeting and wins ≥70% of 10 seeded games against `main.py`

**Independent Test**: `uv run python eval.py --games 10` — win rate printed to stdout must be ≥70%

### Implementation for User Story 1

- [ ] T005 [US1] In `agent_v2.py`, implement turn-level planet filtering: parse `obs` with dict/attribute fallback, build `my_planets` (owner == player) and `targets` (owner != player) lists — early return `[]` if either list is empty
- [ ] T006 [US1] In `agent_v2.py`, implement the `score_target(mine, target)` inline expression: `target.production / math.hypot(target.x - mine.x, target.y - mine.y)` — guard against zero distance with a small epsilon
- [ ] T007 [US1] In `agent_v2.py`, implement the main per-planet targeting loop: for each owned planet, find the highest-scoring target using the scoring expression, check `mine.ships >= target.ships + 1`, compute `math.atan2` angle, append `[mine.id, angle, target.ships + 1]` to moves
- [ ] T008 [US1] Smoke-test `agent_v2.py` against `random` using `make test AGENT=agent_v2.py` — confirm no exceptions and a non-zero move list on most turns
- [ ] T009 [US1] In `eval.py`, implement the game loop: for each seed in `range(games)`, call `env.make('orbit_wars', configuration={'seed': seed})`, `env.run([agent0_path, agent1_path])`, extract final rewards from `env.steps[-1]`, determine winner (higher reward wins; equal = draw), print per-game result line per the contract in `contracts/agent-interface.md`
- [ ] T010 [US1] In `eval.py`, implement the summary block: count wins/draws, compute win rate, print the formatted summary matching the contract output format
- [ ] T011 [US1] Run `uv run python eval.py --games 10` and verify win rate ≥70%; if below threshold, revisit T007 scoring logic before proceeding

**Checkpoint**: US1 complete — `agent_v2.py` beats `main.py` ≥7/10 games; `eval.py` prints correct results

---

## Phase 4: User Story 2 - Observable Strategy Difference (Priority: P2)

**Goal**: A replay shows the new agent bypassing a nearby low-production planet to attack a farther high-production one

**Independent Test**: Run one game, inspect stdout turn actions or render notebook — identify at least one turn where agent_v2 targets a farther planet with higher production score

### Implementation for User Story 2

- [ ] T012 [P] [US2] Add `--verbose` flag to `eval.py` that, when set, prints each move as `Turn N | Planet {id} → Target {id} (score={score:.3f}, ships={n})` so strategy differences are visible without a full replay render
- [ ] T013 [US2] In `agent_v2.py`, add a `__name__ == '__main__'` block that runs a single game against `main.py` with seed 42 and renders it via `env.render(mode='ipython')` — for use in `getting-started.ipynb` if desired (does not affect agent logic)

**Checkpoint**: US2 complete — verbose mode surfaces the targeting decisions; strategy difference observable

---

## Phase 5: User Story 3 - Local Test Harness (Priority: P3)

**Goal**: `eval.py` accepts `--agent0` / `--agent1` path args; full 10-game eval runs in <60 seconds

**Independent Test**: `uv run python eval.py --agent0 agent_v2.py --agent1 main.py --games 10` completes in <60s with correct output; no code edits needed to swap agents

### Implementation for User Story 3

- [ ] T014 [P] [US3] In `eval.py`, implement agent loading via `importlib.util.spec_from_file_location` + `module_from_spec` so `--agent0` and `--agent1` accept arbitrary file paths and the loaded `agent` function is passed to `env.run()`
- [ ] T015 [US3] Add a `Makefile` target `eval` that runs `uv run python eval.py --agent0 agent_v2.py --agent1 main.py --games 10` for convenience
- [ ] T016 [US3] Time the full 10-game run with `time uv run python eval.py --games 10` and confirm <60s; if over budget, reduce per-game overhead (e.g., disable debug logging in env.make)

**Checkpoint**: US3 complete — single command runs full eval; any two agent files can be compared without code edits

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Experiment log, Makefile integration, readability review

- [ ] T017 Fill in `experiments/2026-05-29-production-weighted-baseline.md` with actual self-play results from T011: hypothesis, change made, win rate over 10 games, conclusion — required by Constitution Principle IV before any Kaggle submission
- [ ] T018 [P] Add `selfplay` Makefile target: `uv run python eval.py --agent0 agent_v2.py --agent1 agent_v2.py --games 10` for symmetric self-play baseline
- [ ] T019 [P] Review `agent_v2.py` for readability: variable names match the domain model (`mine`, `target`, `score`, `angle`), no nested comprehensions in inner loop, epsilon guard is named `EPSILON` constant at module level
- [ ] T020 Update `specs/001-beat-starter-agent/checklists/requirements.md` — mark all items complete now that implementation is done

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately; T001 and T002 can run in parallel
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — T003 and T004 can run in parallel
- **Phase 3 (US1)**: Depends on Phase 2 — T005→T006→T007 are sequential (same file); T009→T010 are sequential (same file); T008 and T009 can start in parallel after T007
- **Phase 4 (US2)**: Depends on Phase 3 checkpoint (agent must work); T012 and T013 can run in parallel
- **Phase 5 (US3)**: Depends on Phase 3 checkpoint (eval.py must work); T014→T015→T016 sequential
- **Phase 6 (Polish)**: Depends on all story phases complete; T018 and T019 can run in parallel

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Depends on US1 checkpoint (agent must produce observable moves)
- **US3 (P3)**: Depends on US1 checkpoint (eval.py game loop must work)

### Within User Story 1

- T005 (filtering) → T006 (scoring) → T007 (main loop) — sequential, same file
- T008 (smoke test) can run after T007
- T009 (game loop) → T010 (summary) — sequential, same file; can start in parallel with T008

---

## Parallel Opportunities

```bash
# Phase 1 — run together:
Task T001: mkdir experiments/
Task T002: Create experiments/2026-05-29-production-weighted-baseline.md skeleton

# Phase 2 — run together:
Task T003: Create agent_v2.py scaffold
Task T004: Create eval.py scaffold

# Phase 3 — after T007 completes:
Task T008: Smoke test agent_v2.py        # independent of eval.py work
Task T009: Implement eval.py game loop   # independent of agent smoke test

# Phase 6 — run together:
Task T018: Add selfplay Makefile target
Task T019: Readability review of agent_v2.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: US1 (T005–T011)
4. **STOP and VALIDATE**: `uv run python eval.py --games 10` → win rate ≥70%
5. Constitution gate: fill experiment log (T017) before any Kaggle submission

### Incremental Delivery

1. Setup + Foundational → scaffolds ready
2. US1 → working agent + eval harness (MVP)
3. US2 → observable strategy diff (verbose mode)
4. US3 → polished CLI harness
5. Polish → experiment log filled, Makefile complete

---

## Notes

- `main.py` is the baseline — **do not modify it**
- `agent_v2.py` must be a single self-contained file (Kaggle submission format)
- Experiment log at `experiments/2026-05-29-production-weighted-baseline.md` is a **constitution gate** — must be filled before any `make submit` invocation
- `eval.py` is not submitted to Kaggle — it is a local development tool only
- [P] tasks operate on different files and have no shared state; safe to parallelize
