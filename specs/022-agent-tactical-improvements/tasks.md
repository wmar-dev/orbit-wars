# Tasks: Agent Tactical Improvements

**Input**: Design documents from `specs/022-agent-tactical-improvements/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: Not separately requested — eval is done via `make eval` (self-play harness, ≥50 games per direction).

**Organization**: Tasks grouped by user story. All three stories modify `agent_v61.py` via toggle constants and are tested sequentially (same file). Stories can be implemented and eval'd independently by toggling constants off/on.

---

## Phase 1: Setup

**Purpose**: Create the new agent file and experiment log; wire toggle constants.

- [X] T001 Copy `agent_v60.py` to `agent_v61.py` and update the module docstring to describe the three tactical improvements
- [X] T002 Add four toggle constants to the top of `agent_v61.py` below the existing v60 constants: `EARLY_DISPATCH_ENABLED = True`, `EARLY_DISPATCH_WINDOW = 15`, `DYNAMIC_GARRISON_ENABLED = True`, `WEIGHTED_EVAL_ENABLED = True`
- [X] T003 Create experiment log file `experiments/2026-06-06-tactical-improvements.md` with hypothesis, change description, and placeholder rows for self-play results for each of the three directions

**Checkpoint**: `agent_v61.py` exists, imports cleanly (`uv run python -c "import agent_v61"`), and produces identical output to v60 when all toggles are `False`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify the eval harness works against v60 as the baseline, establishing the control group score.

**⚠️ CRITICAL**: Baseline eval must be recorded before any story implementation begins.

- [X] T004 Run `AGENT=agent_v61.py uv run python eval.py h2h --agent0 agent_v61.py --agent1 agent_v60.py --games 50 --swap` with all toggles `False` and record the result (should be ~50% — confirms v61 is a faithful copy of v60)
- [X] T005 Record the control-group result in `experiments/2026-06-06-tactical-improvements.md` under "Control group (all toggles False)"

**Checkpoint**: Baseline win rate documented. All story phases can now proceed sequentially.

---

## Phase 3: User Story 1 — Early-Game Dispatch (Priority: P1) 🎯 MVP

**Goal**: Agent dispatches toward the nearest capturable neutral planet immediately in turns 0–15, without waiting to accumulate a large garrison.

**Independent Test**: `EARLY_DISPATCH_ENABLED=True`, all other toggles `False`. Run 50-game eval vs v60. Target: ≥52% win rate. Measure average planet count at turn 20 (target: ≥4.0 vs current ~3.4).

### Implementation for User Story 1

- [X] T006 [US1] In `agent_v61.py`, add an `early_claimed` set and `early_dispatched` set at the top of `_greedy_moves()`, initialized empty each call
- [X] T007 [US1] In `agent_v61.py`, implement the early-dispatch block in `_greedy_moves()`: insert after the threat/comet setup section and before the main dispatch loop; guard with `if EARLY_DISPATCH_ENABLED and step <= EARLY_DISPATCH_WINDOW:`
- [X] T008 [US1] In the early-dispatch block in `agent_v61.py`, iterate over `my_planets`; for each mine not in `departing_this_turn` or `evacuate_this_turn`, find the nearest neutral planet (`t.owner == -1`) not in `early_claimed` that passes `_path_safe`
- [X] T009 [US1] In the early-dispatch block in `agent_v61.py`, compute fleet size accounting for garrison growth during travel: `travel_turns = hypot(x_pred - mine.x, y_pred - mine.y) / fleet_speed(t.ships + 1)`, `needed = t.ships + int(t.production * travel_turns) + 1`; skip if `mine.ships < needed`
- [X] T010 [US1] In the early-dispatch block in `agent_v61.py`, add the move to `moves`, add mine to `early_dispatched` and target to `early_claimed`; skip mines in `early_dispatched` in the main dispatch loop below
- [X] T011 [US1] Set `EARLY_DISPATCH_ENABLED = True`, all others `False`; run `uv run python eval.py h2h --agent0 agent_v61.py --agent1 agent_v60.py --games 50 --swap` and record win rate and average planet count at turn 20 in the experiment log

**Checkpoint**: US1 eval result recorded. Win rate ≥52% = proceed. Win rate <50% = investigate before continuing.

---

## Phase 4: User Story 2 — Garrison Floor Reduction (Priority: P2)

**Goal**: Agent holds fewer ships in reserve across the mid-game by using a lower and slower-ramping garrison floor, enabling more dispatches per turn.

**Independent Test**: `DYNAMIC_GARRISON_ENABLED=True`, all other toggles `False`. Run 50-game eval vs v60. Target: ≥52% win rate. Measure average dispatch rate in turns 30–50 (target: ≥0.65/turn vs current ~0.43).

### Implementation for User Story 2

- [X] T012 [US2] In `agent_v61.py`, locate the `gff` computation in `_greedy_moves()`: `gff = 1.0 + 3.0 * min(step / 300.0, 1.0)`
- [X] T013 [US2] In `agent_v61.py`, wrap the existing `gff` formula in an `if not DYNAMIC_GARRISON_ENABLED:` branch and add the alternative: `gff = 1.0 + 1.5 * min(step / 400.0, 1.0)` under `else:` (caps at 2.5× over 400 turns instead of 4× over 300)
- [X] T014 [US2] Set `DYNAMIC_GARRISON_ENABLED = True`, all others `False`; run `uv run python eval.py h2h --agent0 agent_v61.py --agent1 agent_v60.py --games 50 --swap` and record win rate in the experiment log

**Checkpoint**: US2 eval result recorded. Win rate ≥52% = proceed. Win rate <50% = try alternate gff cap (e.g. 3.0× instead of 2.5×) before declaring failure.

---

## Phase 5: User Story 3 — Production-Weighted Lookahead Eval (Priority: P3)

**Goal**: Beam search accumulates production score each simulated turn rather than sampling only at the depth horizon, so fast captures score higher than slow ones of equal final value.

**Independent Test**: `WEIGHTED_EVAL_ENABLED=True`, all other toggles `False`. Run 50-game eval vs v60. Target: win rate >54% (current beam parity).

### Implementation for User Story 3

- [X] T015 [US3] In `agent_v61.py`, locate the `_beam_search()` function's candidate evaluation loop (the `for dispatches, moves in candidates:` block)
- [X] T016 [US3] In `agent_v61.py`, replace the current pattern (`simulate N steps, then call state.score() once`) with a cumulative accumulation pattern when `WEIGHTED_EVAL_ENABLED`: initialize `score = 0.0`, then inside the step loop add `score += state.score(player, TRANSIT_WEIGHT)` after each `state.step()` call; when `WEIGHTED_EVAL_ENABLED` is `False`, retain the original horizon-only `score = state.score(...)` call after the loop
- [X] T017 [US3] Set `WEIGHTED_EVAL_ENABLED = True`, all others `False`; run `uv run python eval.py h2h --agent0 agent_v61.py --agent1 agent_v60.py --games 50 --swap` and record win rate in the experiment log

**Checkpoint**: US3 eval result recorded. All three directions now independently evaluated.

---

## Phase 6: Polish & Combination

**Purpose**: Combine all passing directions, run final eval, update project files, and prepare for Kaggle submission if threshold is met.

- [X] T018 Set all three toggles that individually passed (≥52% win rate) to `True` in `agent_v61.py`; set any that failed to `False` and add an explanatory comment
- [X] T019 Run `uv run python eval.py h2h --agent0 agent_v61.py --agent1 agent_v60.py --games 50 --swap` with the combined configuration and record the combined win rate in the experiment log
- [X] T020 Record conclusion for each direction in `experiments/2026-06-06-tactical-improvements.md`: direction result (keep/discard), combined win rate, and whether the 60% combined target was met
- [X] T021 [P] Update `README.md` Agents table to add `agent_v61.py` row with win rate vs v60 and strategy description; bold it if it becomes the new best
- [X] T022 [P] Update `Makefile` `AGENT` and `RENDER_AGENT` variables to point to `agent_v61.py` if it beats v60
- [X] T023 Run `make opponents` to sweep agent_v61 against all known opponent agents and record results
- [X] T024 If combined win rate ≥60%: run `make submit MESSAGE="agent_v61: early dispatch + garrison floor + weighted eval, XX% vs v60"` and record submission ID and Kaggle score in `SUBMISSIONS.md`

**Checkpoint**: Experiment log complete, README updated, submission made (if threshold met).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001–T003 complete)
- **US1 (Phase 3)**: Depends on Phase 2 baseline recorded
- **US2 (Phase 4)**: Depends on Phase 2; independent of US1 result (toggle-isolated)
- **US3 (Phase 5)**: Depends on Phase 2; independent of US1 and US2 results
- **Polish (Phase 6)**: Depends on all three story evals recorded

### User Story Dependencies

All three stories share the same file (`agent_v61.py`) but are isolated by toggle constants. They can be implemented in any order after Phase 2. The recommended order is P1 → P2 → P3 since P1 has the strongest expected signal and most evidence.

### Within Each User Story

- Implementation tasks must run sequentially (each task builds on the previous)
- Eval task (last task per story) must run after all implementation tasks in that story

### Parallel Opportunities

- T021 (README update) and T022 (Makefile update) in Phase 6 can run in parallel
- US2 and US3 implementation can be done in parallel if working across two sessions, since they modify different functions (`_greedy_moves` vs `_beam_search`)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational baseline (T004–T005)
3. Complete Phase 3: US1 early-dispatch (T006–T011)
4. **STOP and VALIDATE**: 50-game eval result vs v60
5. If ≥52%: proceed to US2. If <50%: investigate `EARLY_DISPATCH_WINDOW` and fleet-sizing before continuing.

### Incremental Delivery

1. Setup + Foundational → baseline documented
2. US1 → early dispatch eval'd → strongest signal confirmed
3. US2 → garrison eval'd → dispatch frequency signal confirmed
4. US3 → weighted eval → lookahead quality confirmed
5. Combination → 50-game combined eval → Kaggle submit if ≥60%

---

## Notes

- [P] tasks = different files or no shared state, can run in parallel
- Toggle constants allow each direction to be isolated without creating separate agent files
- All eval runs use `--swap` flag (each agent plays both sides) for fairness
- Record all results in the experiment log before proceeding to the next story
- If a direction fails (win rate <50%), do not include it in the combination
