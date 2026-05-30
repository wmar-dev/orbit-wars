---
description: "Task list for Agent Improvement Experiments (agent_v11–v15)"
---

# Tasks: Agent Improvement Experiments

**Input**: Design documents from `/specs/005-agent-improvement-experiments/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks are grouped by user story. US1 = hypothesis documentation, US2 = isolated mechanic experiments (A–D), US3 = combined agent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the evaluation harness works against agent_v10 and create the experiment records directory baseline.

- [ ] T001 Verify `eval.py --agent0 agent_v10.py --agent1 agent_v10.py --games 1` runs without error (sanity check before any new agent work)
- [ ] T002 Confirm `experiments/` directory exists at repo root (create if absent)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the baseline diagnostic fingerprint for agent_v10 that all candidates are judged against. Must complete before any experiment records are written.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Run `eval.py --agent0 agent_v10.py --agent1 agent_v10.py --games 20` (seeds 0–19) to confirm self-play parity (expected ~50%); record result as the baseline reference
- [ ] T004 Read `agent_v10.py` in full and note the exact locations of: (a) fleet send logic, (b) `_path_safe()`, (c) target scoring loop — these are the insertion points for all four mechanics

**Checkpoint**: Baseline confirmed — candidate implementation can now begin

---

## Phase 3: User Story 1 — Hypothesis Documentation (Priority: P1) 🎯 MVP

**Goal**: Document a written hypothesis, expected outcome, and success threshold for each candidate mechanic before any agent code is written (FR-001, SC-001).

**Independent Test**: Confirm that all four experiment record files exist in `experiments/` and each contains a Hypothesis, Change, Self-play result (placeholder), and Conclusion (placeholder) section before T009 (agent_v11) is started.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Create `experiments/2026-05-30-candidate-a-redundant-fleet.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: skipping already-covered targets reduces wasted launches
- [ ] T006 [P] [US1] Create `experiments/2026-05-30-candidate-b-garrison-sizing.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: right-sizing fleet sends and enforcing a garrison floor improves net ship economy
- [ ] T007 [P] [US1] Create `experiments/2026-05-30-candidate-c-threat-defense.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: narrow `incoming > garrison + production×5` threshold avoids agent_v6's over-defense trap
- [ ] T008 [P] [US1] Create `experiments/2026-05-30-candidate-d-single-sender.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: restricting each target to one sender frees other planets to attack different targets

**Checkpoint**: All four experiment records exist with hypotheses written — implementation may now begin

---

## Phase 4: User Story 2 — Isolated Mechanic Experiments (Priority: P1)

**Goal**: Implement agent_v11–v14, evaluate each over 20 games vs agent_v10 (seeds 0–19), record win rates, and determine which mechanics advance (≥55% threshold).

**Independent Test**: Each agent can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v10.py --games 20` and produces a win rate. Each experiment record is updated with Self-play result and Conclusion.

### Candidate A — Redundant Fleet Avoidance (agent_v11)

- [ ] T009 [US2] Write `agent_v11.py` at repo root, building on agent_v10; add docstring listing mechanic (redundant fleet avoidance) and base agent (v10); implement: before each target evaluation, compute `sum(f.ships for f in obs.fleets if f.owner == my_id and f.destination == target) >= target.ships + 1`; if covered, skip target
- [ ] T010 [US2] Run `eval.py --agent0 agent_v11.py --agent1 agent_v10.py --games 20` (seeds 0–19); record win/loss counts
- [ ] T011 [US2] Update `experiments/2026-05-30-candidate-a-redundant-fleet.md` with Self-play result and Conclusion; note pass/fail vs 55% threshold
- [ ] T012 [US2] Update README.md Agents table with agent_v11 and its win rate vs agent_v10 (FR-006)

### Candidate B — Garrison Sizing (agent_v12)

- [ ] T013 [US2] Write three sub-experiment variants of agent_v12 logic (inline in one file with a `GARRISON_FLOOR_MODE` constant): Mode A = `max(planet.production * 5, 1)`, Mode B = `max(planet.production * 10, 1)`, Mode C = `10`; send logic: `send = min(target.ships + 1, source.ships - garrison_floor)`; skip if `send <= 0`; include docstring
- [ ] T014 [US2] Run eval for Mode A (`production × 5`): `eval.py --agent0 agent_v12.py --agent1 agent_v10.py --games 20` with `GARRISON_FLOOR_MODE='A'`; record win rate
- [ ] T015 [US2] Run eval for Mode B (`production × 10`) and Mode C (fixed 10); record win rates for all three variants
- [ ] T016 [US2] Select the best-performing sub-experiment variant; set it as the permanent `GARRISON_FLOOR_MODE` in `agent_v12.py`; add docstring note on winning variant
- [ ] T017 [US2] Update `experiments/2026-05-30-candidate-b-garrison-sizing.md` with sub-experiment results table, winning variant, and Conclusion
- [ ] T018 [US2] Update README.md Agents table with agent_v12 and its win rate vs agent_v10

### Candidate C — Threat-Aware Defense (agent_v13)

- [ ] T019 [US2] Write `agent_v13.py` at repo root, building on agent_v10; add docstring; implement: at turn start, compute `threat[p] = sum(f.ships for f in obs.fleets if f.owner == enemy_id and f.destination == p)` for each owned planet; if `threat[p] > p.ships + p.production * 5`, dispatch reinforcement from the closest owned planet with surplus ships (`source.ships - garrison_floor > 0`); cap at one dispatch per threatened planet per turn; offensive logic unchanged
- [ ] T020 [US2] Run `eval.py --agent0 agent_v13.py --agent1 agent_v10.py --games 20` (seeds 0–19); record win/loss counts
- [ ] T021 [US2] Update `experiments/2026-05-30-candidate-c-threat-defense.md` with Self-play result and Conclusion; compare trigger frequency vs agent_v6 if data available
- [ ] T022 [US2] Update README.md Agents table with agent_v13 and its win rate vs agent_v10

### Candidate D — Single-Sender Coordination (agent_v14)

- [ ] T023 [US2] Write `agent_v14.py` at repo root, building on agent_v10; add docstring; implement: for each enemy/neutral target, compute `efficiency[source] = distance(source, target) / max(source.ships - garrison_floor, 1)` for all owned sources; only the source with minimum efficiency score may launch at that target this turn; use a fixed `garrison_floor = production * 5` as the baseline (or whichever value was proven by Candidate B if T016 is done first)
- [ ] T024 [US2] Run `eval.py --agent0 agent_v14.py --agent1 agent_v10.py --games 20` (seeds 0–19); record win/loss counts
- [ ] T025 [US2] Update `experiments/2026-05-30-candidate-d-single-sender.md` with Self-play result and Conclusion
- [ ] T026 [US2] Update README.md Agents table with agent_v14 and its win rate vs agent_v10

**Checkpoint**: All four candidates evaluated; pass/fail determined for each mechanic vs 55% threshold

---

## Phase 5: User Story 3 — Combined Agent (Priority: P2)

**Goal**: Stack all passing mechanics (≥55%) into agent_v15 and verify ≥65% win rate vs agent_v10 with 0 sun/OOB losses (SC-003, SC-004).

**Independent Test**: `eval.py --agent0 agent_v15.py --agent1 agent_v10.py --games 20` returns ≥65% win rate; `diagnose_v9.py --agent agent_v15.py --games 20` returns 0 sun losses and 0 OOB losses.

### Implementation for User Story 3

- [ ] T027 [US3] Review pass/fail results from T010–T025; list which mechanics passed ≥55%; if no mechanic passed, document in `experiments/` and skip T028–T033
- [ ] T028 [US3] Write `agent_v15.py` at repo root building on agent_v10; include docstring listing all stacked mechanics and base agents; implement mechanics in integration order: (1) defense pass (C logic, if C passed), (2) single-sender filter per target (D logic, if D passed), (3) redundancy skip (A logic, if A passed), (4) garrison-floor send-sizing (B logic with winning variant from T016, if B passed); guard: defense dispatch bypasses single-sender constraint; guard: skip launch if `send <= 0` after floor subtraction
- [ ] T029 [US3] Run `eval.py --agent0 agent_v15.py --agent1 agent_v10.py --games 20` (seeds 0–19); record win rate
- [ ] T030 [US3] If win rate < 65%, test mechanic subsets (remove one mechanic at a time) to isolate regression — document findings in `experiments/2026-05-30-combined-agent-v15.md`
- [ ] T031 [US3] Run `diagnose_v9.py --agent agent_v15.py --games 20`; verify 0 sun losses and 0 OOB losses (SC-004)
- [ ] T032 [US3] Create `experiments/2026-05-30-combined-agent-v15.md` with stacked mechanics list, Self-play result vs agent_v10, diagnostic results, and Conclusion
- [ ] T033 [US3] Update README.md Agents table: mark agent_v15 as the new best agent (bold) with its win rate vs agent_v10; include win rates for v11–v14

**Checkpoint**: agent_v15 evaluated; SC-001 through SC-005 verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation completeness and spec closure

- [ ] T034 [P] Verify all five experiment records have complete Self-play result and Conclusion sections (no TBD placeholders remaining)
- [ ] T035 [P] Verify all five new agent files (v11–v15) have docstrings listing mechanics and base agents (FR-008)
- [ ] T036 Confirm README.md Agents table lists all agents v2–v15 with accurate win rates; best agent bolded
- [ ] T037 Review agent_v15.py for any safety guard regressions vs agent_v10: confirm `_path_safe()` is unchanged, sun exclusion = 12.0, OOB guard = [0, 100] inclusive, comet path index clamped

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories
- **US1 — Hypothesis docs (Phase 3)**: Depends on Phase 2 — blocks Phase 4 (FR-001)
- **US2 — Candidates (Phase 4)**: Depends on Phase 3 (all experiment records must exist first)
- **US3 — Combined (Phase 5)**: Depends on Phase 4 (needs pass/fail results from all candidates)
- **Polish (Phase 6)**: Depends on Phase 5

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on other stories; all four records can be written in parallel (T005–T008 all marked [P])
- **US2 (P1)**: Depends on US1 completion; within US2, each candidate (A, B, C, D) is independent and can be worked in parallel if desired — each writes its own file
- **US3 (P2)**: Depends on US2 completion (needs win rates to determine which mechanics to stack)

### Within User Story 2

- Candidate A (T009–T012), B (T013–T018), C (T019–T022), D (T023–T026) are independent of each other
- Within each candidate: write agent → run eval → update experiment record → update README

### Parallel Opportunities

- T005, T006, T007, T008 (US1 experiment record stubs) — all parallelizable
- T009–T012 (Candidate A) can run in parallel with T013–T018 (B), T019–T022 (C), T023–T026 (D)
- T034, T035 (Phase 6 verification) are parallelizable

---

## Parallel Example: User Story 2 (if working all four candidates simultaneously)

```bash
# All four candidates can be developed in parallel:
Task A: "Write agent_v11.py + run eval + update experiment record" (T009–T011)
Task B: "Write agent_v12.py sub-experiments + run eval + update experiment record" (T013–T017)
Task C: "Write agent_v13.py + run eval + update experiment record" (T019–T021)
Task D: "Write agent_v14.py + run eval + update experiment record" (T023–T025)

# README updates (T012, T018, T022, T026) should be batched after all evals complete
# to avoid repeated merge conflicts on the same table
```

---

## Implementation Strategy

### MVP First (User Story 1 + strongest single candidate)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: Write all four hypothesis records (US1)
4. Pick the highest-expected-impact candidate (Candidate A — redundant fleet avoidance) and complete T009–T012
5. **STOP and VALIDATE**: Did it reach 55%? If yes, one proven mechanic in hand.

### Incremental Delivery

1. Setup + Foundational → baseline confirmed
2. US1: All four hypothesis records written in parallel
3. US2: Candidates A, B, C, D evaluated (sequentially or in parallel)
4. US3: Combined agent_v15 built from passing mechanics
5. Polish: Docs and table finalized

### Single-Developer Sequence

1. T001 → T002 → T003 → T004 (phases 1–2)
2. T005 → T006 → T007 → T008 (US1, can batch)
3. T009 → T010 → T011 → T012 (Candidate A)
4. T013 → T014 → T015 → T016 → T017 → T018 (Candidate B)
5. T019 → T020 → T021 → T022 (Candidate C)
6. T023 → T024 → T025 → T026 (Candidate D)
7. T027 → T028 → T029 → T030 → T031 → T032 → T033 (Combined)
8. T034 → T035 → T036 → T037 (Polish)

---

## Notes

- **Do not modify** `eval.py` or `diagnose_v9.py` — evaluation harness is fixed
- **Do not modify** `agent_v10.py` — it is the immutable baseline
- Each agent file must build on agent_v10 verbatim; only the targeted mechanic is added
- Win rate < 55% for a candidate → document and skip; do not include in agent_v15
- Win rate < 65% for agent_v15 → run subset tests (T030) before concluding
- README Agents table update is mandatory after each eval (FR-006)
