# Tasks: Fix Comet Fleet Targeting

**Input**: Design documents from `specs/015-fix-fleet-targeting/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅

**Source change**: `main.py` only — replace 2-pass `_comet_two_pass` with convergent iterative loop.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Confirm current code and reproduction

- [x] T001 Reproduce the miss: run `uv run python eval.py --agent0 main.py --agent1 agent_v47.py --games 5` and note any out-of-bounds fleet events in `main.py`

---

## Phase 2: Foundational

**Purpose**: Add the two new module-level constants needed by both user stories

**⚠️ CRITICAL**: Must be complete before Phase 3 and Phase 4

- [x] T002 Add `_COMET_INTERCEPT_MAX_ITER = 10` and `_COMET_INTERCEPT_EPS = 0.5` constants to `main.py` (after the existing `ANGLE_EPSILON` constant block, around line 33)

**Checkpoint**: Constants in place — user story implementation can begin

---

## Phase 3: User Story 1 — Fleets intercept comets correctly (Priority: P1) 🎯 MVP

**Goal**: Replace the 2-pass divergent fallback with a convergent iterative fixed-point loop that correctly identifies the interception point or declares the comet unreachable.

**Independent Test**: Run `uv run python eval.py --agent0 main.py --agent1 agent_v47.py --games 20`; observe zero out-of-bounds fleets in games where comets are active.

### Implementation for User Story 1

- [x] T003 [US1] Replace the body of `_comet_two_pass` in `main.py` with the iterative loop from the plan (lines ~158–161 current), keeping the function signature identical:
  ```python
  def _comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed):
      t = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
      for _ in range(_COMET_INTERCEPT_MAX_ITER):
          x, y, valid = _comet_predicted_pos(comet_planet, comet_path_lookup, t)
          if not valid:
              return comet_planet.x, comet_planet.y, False
          t_new = math.hypot(x - mine_x, y - mine_y) / speed
          if abs(t_new - t) < _COMET_INTERCEPT_EPS:
              return x, y, True
          t = t_new
      return comet_planet.x, comet_planet.y, False
  ```

- [x] T004 [US1] Run `make test` to confirm the agent runs without error against the random opponent

- [x] T005 [US1] Manually replay step 54 of `replays/78469577.json` through the new `_comet_two_pass` logic in a scratch cell or `python -c` snippet to confirm the result is now `valid=False` (comet unreachable) rather than a wrong intercept point

**Checkpoint**: User Story 1 complete — convergent intercept or correct rejection for all comets

---

## Phase 4: User Story 2 — No ships wasted on unreachable comets (Priority: P2)

**Goal**: Confirm that the non-convergence path (loop exhausted) and the near-expiry path both return `valid=False` and produce no fleet dispatch, redirecting those ships to other targets.

**Independent Test**: With only distant comets in range, observe that the agent dispatches ships to orbiting or static planets rather than wasting them on unreachable comets.

### Implementation for User Story 2

- [x] T006 [US2] Verify that the final `return comet_planet.x, comet_planet.y, False` in the new `_comet_two_pass` (non-convergence path) is reached — add a temporary `print` or confirm via replay trace, then remove the print before eval

**Checkpoint**: User Stories 1 and 2 complete — no ships wasted on bad intercepts

---

## Phase 5: Polish & Evaluation

**Purpose**: Validate against constitution requirements, document, and promote if passing

- [x] T007 Run `uv run python eval.py --agent0 main.py --agent1 agent_v50.py --games 50` to measure win rate vs. prior best — result: 66% (33W/17L)

- [x] T008 Create experiment log `experiments/2026-06-01-fix-comet-intercept.md` with: hypothesis, change description, self-play result, conclusion (per constitution Principle IV)

- [x] T009 If win rate ≥ 50% (improvement confirmed): copy fixed `main.py` to `agent_v56.py` (next available version), update the docstring to describe the fix, update `README.md` Agents table and `AGENT` / `RENDER_AGENT` in `Makefile`

- [x] T010 If win rate acceptable (≥45%): update `main.py` docstring to reflect the fix regardless, note the result in the experiment log

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS Phase 3 and Phase 4
- **User Story 1 (Phase 3)**: Depends on Phase 2
- **User Story 2 (Phase 4)**: Depends on Phase 3 (T003 must be complete — US2 verifies the non-convergence path introduced in T003)
- **Polish (Phase 5)**: Depends on Phases 3 and 4

### Within Each Phase

- T003 → T004 → T005 (sequential: write, smoke test, verify)
- T007 → T008 → T009/T010 (sequential: eval, document, promote)

---

## Implementation Strategy

### MVP (User Stories 1 + 2 only)

1. T001: Confirm reproduction
2. T002: Add constants
3. T003–T005: Replace function, smoke test, verify
4. T006: Confirm non-convergence path
5. **VALIDATE**: Run 20-game eval
6. T007–T010: Document and promote

Total: ~10 tasks, single file change, ~30 minutes of work + eval time.

---

## Notes

- No new files created (except experiment log)
- `_comet_predicted_pos` is **not** changed — its validity check (`future_idx + 5 >= len(path)`) is already correct
- The fix is backward-compatible: for comets that the 2-pass already handled correctly, the new loop converges in ≤2 iterations and produces the same result
