# Tasks: Early Expansion Experiments from Replay 78539022

**Input**: Design documents from `/specs/018-replay-neutral-fleet-experiments/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and evaluation of each experiment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1–US4 per spec.md)
- Exact file paths included in each task description

---

## Phase 1: Setup

**Purpose**: Create experiment documentation skeleton before any code changes.

- [x] T001 Create experiment doc at `experiments/2026-06-02-replay-78539022-early-expansion.md` with sections: Hypothesis, Change, Self-play result, Conclusion (one section per experiment variant A/B/C)

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Confirm the dispatch-skip bug exists before writing fixes. Establishes baseline understanding required for all experiment phases.

**⚠️ CRITICAL**: No experiment variant can be written until this phase confirms the bug's location and reproduction path.

- [x] T002 Verify the affordability-skip bug in `agent_v57.py`: add a temporary `print` at line 408 (`if mine.ships < ships_needed: continue`) and run `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v57.py --games 1` with seed 1054721759 (replay seed) to confirm step 6 skips Planet 16 dispatch; document observed step of first dispatch and target chosen

**Checkpoint**: Bug confirmed — Planet 16 selected as best ROI at step 6, skip triggered, first dispatch delayed to step 12.

---

## Phase 3: User Story 2 — Earlier First Fleet Dispatch (Priority: P2) 🎯 MVP

**Goal**: Fix the affordability-skip bug so the agent falls back to the cheapest affordable target rather than sitting idle.

**Independent Test**: Run 50-game eval of `agent_v58_fallback.py` vs `agent_v57.py`; expect average first-dispatch step ≥5 steps earlier and win rate ≥50%.

### Implementation for User Story 2

- [x] T003 [US2] Create `agent_v58_fallback.py` by copying `agent_v57.py` and replacing the single-target pick + bail pattern (lines 380–413) with a sorted-candidates loop: sort `roi_scores` descending by `blended_key`, then iterate until finding a candidate where `mine.ships >= ships_needed`, dispatch to it and break; preserve all comet, path-safety, and enemy-fleet-size logic unchanged
- [x] T004 [US2] Run 50-game evaluation: `uv run python eval.py --agent0 agent_v58_fallback.py --agent1 agent_v57.py --games 50 --jobs 4`; capture win rate and print output
- [x] T005 [US2] Record Experiment A results in `experiments/2026-06-02-replay-78539022-early-expansion.md`: fill in Hypothesis, Change (reference lines modified), Self-play result (win rate, 50 games), Conclusion (improved / no change / regressed)

**Checkpoint**: User Story 2 complete when Experiment A win rate is measured and documented.

---

## Phase 4: User Story 1 — Growth-Efficiency First Target (Priority: P1)

**Goal**: Test whether replacing the ROI formula with a simpler `production/ships` growth-efficiency score for neutral planet selection further improves win rate beyond Experiment A.

**Independent Test**: Run 50-game eval of `agent_v58_efficiency.py` vs `agent_v57.py`; expect win rate ≥50% and ≥Experiment A win rate.

### Implementation for User Story 1

- [x] T006 [US1] Create `agent_v58_efficiency.py` by taking `agent_v58_fallback.py` as the base and modifying the `blended_key` function: for neutral targets (`t.owner == -1`), replace the ROI-based score with `t.production / max(t.ships, 1)`; for enemy targets keep existing ROI; update the sort order to use this combined key before iterating the affordability fallback loop
- [x] T007 [US1] Run 50-game evaluation: `uv run python eval.py --agent0 agent_v58_efficiency.py --agent1 agent_v57.py --games 50 --jobs 4`; capture win rate and print output
- [x] T008 [US1] Record Experiment B results in `experiments/2026-06-02-replay-78539022-early-expansion.md`: fill in Hypothesis, Change (describe scoring formula replacement), Self-play result (win rate, 50 games), Conclusion and comparison to Experiment A

**Checkpoint**: User Story 1 complete when Experiment B win rate is measured and compared to A.

---

## Phase 5: User Story 3 — Minimum-Viable Fleet Sizing (Priority: P2)

**Goal**: Verify whether neutral planets grow during transit (which would make current `ships_needed = t.ships + 1` insufficient) and fix fleet sizing if needed.

**Independent Test**: Run a replay trace confirming fleet arrival: send exactly `t.ships + 1` ships to a neutral and confirm capture. If capture fails, create `agent_v58_sizing.py` with corrected sizing.

### Implementation for User Story 3

- [x] T009 [US3] Verify neutral planet static-garrison behavior: check `kaggle_environments` orbit_wars source for neutral growth logic, or run a controlled eval where the agent sends exactly `t.ships + 1` ships to a neutral and observe whether capture succeeds; document result in experiment doc
- [x] T010 [P] [US3] SKIPPED — neutrals confirmed static; no sizing fix needed

**Checkpoint**: User Story 3 complete when fleet sizing is either confirmed correct (no change needed) or corrected with experimental evidence.

---

## Phase 6: User Story 4 — Winner Selection and Parallel Expansion Measurement (Priority: P3)

**Goal**: Select the best-performing single variant, promote it to `agent_v58.py`, and verify the cascade effect (more planets owned early) is present.

**Independent Test**: `agent_v58.py` wins ≥55% of 50 games vs `agent_v57.py`; average planets owned at step 25 is ≥2.5 for winner.

### Implementation for User Story 4

- [x] T011 [US4] Compare Experiment A and B win rates: if within 3 percentage points, run head-to-head `uv run python eval.py --agent0 agent_v58_fallback.py --agent1 agent_v58_efficiency.py --games 100 --jobs 4` to break the tie; document decision in experiment doc
- [x] T012 [US4] Promote winning variant: copy its file to `agent_v58.py`; update docstring at top of `agent_v58.py` with summary of change, base agent, and win rate vs v57
- [x] T013 [US4] Measure parallel expansion cascade: modify a temporary copy of `agent_v58.py` to print planet counts at step 25, run 10 games vs `agent_v57.py`, compute average planet count at step 25 and record in experiment doc

**Checkpoint**: User Story 4 complete when `agent_v58.py` exists with documented win rate and cascade measurement.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Update project metadata to reflect the new best agent.

- [x] T014 [P] Update `README.md` agents table: add row for `agent_v58.py` with win rate vs `agent_v57`; bold the best agent row per CLAUDE.md instructions
- [x] T015 Update `Makefile`: set `AGENT := agent_v58.py` and `RENDER_AGENT ?= agent_v58.py` if `agent_v58` beats `agent_v57` (only if win rate > 50% in at least 50 games)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 only
- **Phase 3 (US2)**: Depends on Phase 2 confirmation
- **Phase 4 (US1)**: Depends on Phase 3 (Experiment B uses Experiment A as base)
- **Phase 5 (US3)**: Depends on Phase 4 (sizing fix builds on winning fallback logic)
- **Phase 6 (US4)**: Depends on Phases 3, 4, 5 all complete
- **Polish (Phase 7)**: Depends on Phase 6 completion

### User Story Dependencies

- **US2 (Phase 3)**: Can start immediately after foundational — no dep on other stories
- **US1 (Phase 4)**: Depends on US2 complete (Experiment B uses Experiment A code as base)
- **US3 (Phase 5)**: Can run in parallel with US1 (independent code path) except T010 uses winner from A/B
- **US4 (Phase 6)**: Depends on US1, US2, US3 all complete

### Within Each Phase

- T003 before T004 before T005 (sequential: write → eval → record)
- T006 before T007 before T008 (same pattern)
- T009 before T010 (verify before fixing)
- T011 before T012 before T013 (compare → promote → measure)

### Parallel Opportunities

- T001 (Setup) can run alongside T002 (Foundational)
- T010 (sizing) is marked [P] — can run concurrently with T006–T008 if using separate terminals
- T014 (README) is marked [P] — can run concurrently with T015

---

## Parallel Example: Phase 5 (US3)

```bash
# T009 and early T006-T007 can overlap since they touch different files:
# Terminal 1:
uv run python eval.py --agent0 agent_v58_efficiency.py --agent1 agent_v57.py --games 50 --jobs 4

# Terminal 2 (simultaneously):
grep -n "production\|growth\|neutral" /path/to/kaggle_environments/envs/orbit_wars/orbit_wars.py
```

---

## Implementation Strategy

### MVP First (User Story 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (confirm bug)
3. Complete Phase 3: Experiment A (affordability fallback)
4. **STOP and VALIDATE**: Run 50-game eval; if win rate ≥55%, this alone may be submission-worthy
5. Continue to Phase 4+ if improvement is marginal

### Incremental Delivery

1. T001–T002: Foundation confirmed
2. T003–T005: Experiment A complete → first validated improvement
3. T006–T008: Experiment B complete → compare with A
4. T009–T010: Fleet sizing confirmed/fixed
5. T011–T013: Best variant promoted to agent_v58.py
6. T014–T015: Project metadata updated

---

## Notes

- [P] tasks touch different files with no blocking dependencies
- [Story] label maps each task to the spec.md user story for traceability
- Eval commands require the virtual environment: `uv run python eval.py ...`
- Replay seed for bug reproduction: `seed=1054721759` (from `replay/78539022.json`)
- Remove temporary debug `print` statements from T002 before writing any experiment variant
- Record all eval results (win rate, game count) in the experiment doc before marking tasks complete
