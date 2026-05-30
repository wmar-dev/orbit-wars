---
description: "Task list for Agent Improvement Experiments — Round 2 (agent_v16–v20)"
---

# Tasks: Agent Improvement Experiments — Round 2

**Input**: Design documents from `/specs/006-agent-experiments-round-2/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story. US1 = hypothesis documentation, US2 = isolated mechanic experiments (E–H), US3 = combined agent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the evaluation harness is working against the new agent_v15 baseline.

- [X] T001 Verify `eval.py --agent0 agent_v15.py --agent1 agent_v15.py --games 1` runs without error (sanity check; expect win or draw)
- [X] T002 Confirm `experiments/` directory exists at repo root (it should from round 005; create if absent)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the baseline fingerprint for agent_v15 and identify the exact code locations all four candidates will modify.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Run `eval.py --agent0 agent_v15.py --agent1 agent_v15.py --games 20 --seed 0` to confirm self-play parity (expected ~50%); record result as the round 2 baseline reference
- [X] T004 Read `agent_v15.py` in full and note the exact locations of: (a) `speed = fleet_speed(mine.ships + 1)` on line 241 (Candidate E insertion point), (b) `ships_needed = best_target.ships + 1` on line 289 (Candidate F insertion point), (c) `max_range = nearest_dist * RANGE_FACTOR` (Candidate G insertion point), (d) the `max(candidates, key=lambda ...)` best-target selection (Candidate H insertion point)

**Checkpoint**: Baseline confirmed — candidate implementation can now begin

---

## Phase 3: User Story 1 — Hypothesis Documentation (Priority: P1) 🎯 MVP

**Goal**: Write an experiment record for each candidate mechanic before any agent code is written (FR-001, SC-001).

**Independent Test**: Confirm that all four experiment record files exist in `experiments/` and each contains Hypothesis, Change, Self-play result (TBD), and Conclusion (TBD) sections before T009 (agent_v16) is started.

### Implementation for User Story 1

- [X] T005 [P] [US1] Create `experiments/2026-05-30-candidate-e-orbit-lead-fix.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: computing `fleet_speed(target.ships + 1)` per target corrects the travel-time overestimate that causes fleets to aim past orbiting targets
- [X] T006 [P] [US1] Create `experiments/2026-05-30-candidate-f-transit-sizing.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: sending `target.ships + target.production × travel_turns + 1` prevents failed captures caused by garrison growth during transit
- [X] T007 [P] [US1] Create `experiments/2026-05-30-candidate-g-adaptive-range.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: expanding range when own_ships/enemy_ships ≥ 1.5 and contracting when ≤ 0.7 makes the agent press when winning and focus when losing
- [X] T008 [P] [US1] Create `experiments/2026-05-30-candidate-h-roi-scoring.md` with Hypothesis, Change, Self-play result (TBD), Conclusion (TBD) sections — hypothesis: scoring targets by `production × (100 − travel_turns) / capture_cost` rewards fast, cheap captures and penalizes expensive late ones

**Checkpoint**: All four experiment records exist with hypotheses written — implementation may now begin

---

## Phase 4: User Story 2 — Isolated Mechanic Experiments (Priority: P1)

**Goal**: Implement agent_v16–v19, evaluate each over 20 games vs agent_v15 (seeds 0–19), record win rates, and determine which mechanics advance (≥55% threshold).

**Independent Test**: Each agent can be run with `eval.py --agent0 agent_vN.py --agent1 agent_v15.py --games 20 --seed 0` and produces a win rate. Each experiment record is updated with Self-play result and Conclusion.

### Candidate E — Speed-Corrected Orbit Lead (agent_v16)

- [X] T009 [US2] Write `agent_v16.py` at repo root, building on agent_v15 verbatim; add docstring listing mechanic (speed-corrected orbit lead) and base agent (v15); change: remove the single `speed = fleet_speed(mine.ships + 1)` line (currently outside the per-target loop); in the candidates loop, add `speed_for_lead = fleet_speed(t.ships + 1)` before each `_refined_orbit_lead` call; apply the same change in the fallback (range-ignoring) loop; the best-sender precomputation uses raw distance only, so no change is needed there
- [X] T010 [US2] Run `eval.py --agent0 agent_v16.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); record win/loss counts
- [X] T011 [US2] Update `experiments/2026-05-30-candidate-e-orbit-lead-fix.md` with Self-play result and Conclusion; note pass/fail vs 55% threshold
- [X] T012 [US2] Update README.md Agents table with agent_v16 and its win rate vs agent_v15 (FR-006)

### Candidate F — Transit-Adjusted Fleet Sizing (agent_v17)

- [X] T013 [US2] Write `agent_v17.py` at repo root, building on agent_v15 verbatim; add docstring listing mechanic (transit-adjusted fleet sizing) and base agent (v15); change: after selecting `best_target` and computing orbit-lead position `(bx, by)`, add `travel_turns = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(best_target.ships + 1)`; replace `ships_needed = best_target.ships + 1` with `ships_needed = int(best_target.ships + best_target.production * travel_turns + 1)`; the skip condition `if mine.ships < ships_needed` already exists — it now naturally skips targets where the source can't afford the adjusted amount
- [X] T014 [US2] Run `eval.py --agent0 agent_v17.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); record win/loss counts
- [X] T015 [US2] Update `experiments/2026-05-30-candidate-f-transit-sizing.md` with Self-play result and Conclusion; if win rate is very low (< 20%), note whether the agent is skipping all targets (diagnose by checking if ships_needed is always > mine.ships)
- [X] T016 [US2] Update README.md Agents table with agent_v17 and its win rate vs agent_v15

### Candidate G — Adaptive Range Expansion (agent_v18)

- [X] T017 [US2] Write `agent_v18.py` at repo root, building on agent_v15 verbatim; add docstring listing mechanic (adaptive range expansion) and base agent (v15); change: before the per-planet loop, add `own_ships = sum(p.ships for p in my_planets)`, `enemy_ships = sum(p.ships for p in planets if p.owner == 1 - player)`, `ratio = own_ships / max(enemy_ships, 1)`, and `range_factor = 3.5 if ratio >= 1.5 else 1.5 if ratio <= 0.7 else 2.0`; replace `nearest_dist * RANGE_FACTOR` with `nearest_dist * range_factor` (do not delete the `RANGE_FACTOR` constant — keep it as the default fallback value)
- [X] T018 [US2] Run `eval.py --agent0 agent_v18.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); record win/loss counts
- [X] T019 [US2] Update `experiments/2026-05-30-candidate-g-adaptive-range.md` with Self-play result and Conclusion
- [X] T020 [US2] Update README.md Agents table with agent_v18 and its win rate vs agent_v15

### Candidate H — Capture-ROI Scoring (agent_v19)

- [X] T021 [US2] Write `agent_v19.py` at repo root, building on agent_v15 verbatim; add docstring listing mechanic (capture-ROI scoring) and base agent (v15); change: replace the best-target selection key from `lambda item: item[0].production / (math.hypot(item[0].x - mine.x, item[0].y - mine.y) + EPSILON)` with a helper `def _roi(t, bx, by): travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1); return t.production * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)` and use `key=lambda item: _roi(item[0], item[1], item[2])`; define `_roi` as a module-level function above the `agent()` function
- [X] T022 [US2] Run `eval.py --agent0 agent_v19.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); record win/loss counts
- [X] T023 [US2] Update `experiments/2026-05-30-candidate-h-roi-scoring.md` with Self-play result and Conclusion
- [X] T024 [US2] Update README.md Agents table with agent_v19 and its win rate vs agent_v15

**Checkpoint**: All four candidates evaluated; pass/fail determined for each mechanic vs 55% threshold

---

## Phase 5: User Story 3 — Combined Agent (Priority: P2)

**Goal**: Stack all passing mechanics (≥55%) into agent_v20 and verify ≥65% win rate vs agent_v15 with 0 sun/OOB losses (SC-003, SC-004).

**Independent Test**: `eval.py --agent0 agent_v20.py --agent1 agent_v15.py --games 20 --seed 0` returns ≥65% win rate; `diagnose_v9.py --agent agent_v20.py --games 20` returns 0 sun losses and 0 OOB losses.

### Implementation for User Story 3

- [X] T025 [US3] Review pass/fail results from T010, T014, T018, T022; list which mechanics passed ≥55%; if no mechanic passed, document findings in `experiments/2026-05-30-combined-agent-v20.md` and skip T026–T031
- [X] T026 [US3] Write `agent_v20.py` at repo root building on agent_v15; include docstring listing all stacked mechanics and base agents; implement mechanics in integration order per research.md D-006: (1) compute `range_factor` dynamically before per-planet loop (G, if G passed), (2) in candidates loop compute `speed_for_lead = fleet_speed(t.ships + 1)` per target (E, if E passed), (3) define `_roi()` helper and use it for best-target selection (H, if H passed), (4) compute `travel_turns` from predicted position and set `ships_needed = int(best_target.ships + best_target.production * travel_turns + 1)` (F, if F passed); compute `travel_turns` only once per best_target and reuse it for both F and H if both are included
- [X] T027 [US3] Run `eval.py --agent0 agent_v20.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); record win rate
- [X] T028 [US3] If win rate < 65%, test mechanic subsets (remove one mechanic at a time from agent_v20) to isolate regression — document findings in `experiments/2026-05-30-combined-agent-v20.md`; exclude the lowest-margin mechanic that causes the regression
- [X] T029 [US3] Run `diagnose_v9.py --agent agent_v20.py --games 20`; verify 0 sun losses and 0 OOB losses (SC-004)
- [X] T030 [US3] Create `experiments/2026-05-30-combined-agent-v20.md` with: stacked mechanics list, per-candidate pass/fail table, Self-play result vs agent_v15, diagnostic results, and Conclusion
- [X] T031 [US3] Update README.md Agents table: mark agent_v20 as the new best agent (bold) with its win rate vs agent_v15; include win rates for v16–v19

**Checkpoint**: agent_v20 evaluated; SC-001 through SC-005 verified

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation completeness and spec closure

- [X] T032 [P] Verify all five experiment records (E, F, G, H, combined) have complete Self-play result and Conclusion sections (no TBD placeholders remaining)
- [X] T033 [P] Verify all five new agent files (v16–v20) have docstrings listing mechanics and base agents (FR-008)
- [X] T034 Confirm README.md Agents table lists all agents v2–v20 with accurate win rates; best agent bolded
- [X] T035 Review agent_v20.py for safety guard regressions vs agent_v15: confirm `_path_safe()` is unchanged, `SUN_EXCLUSION = 12.0`, OOB guard `[0, 100]` inclusive, comet path index clamped

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — blocks all user stories
- **US1 — Hypothesis docs (Phase 3)**: Depends on Phase 2 — blocks Phase 4 (FR-001)
- **US2 — Candidates (Phase 4)**: Depends on Phase 3 (all experiment records must exist before any agent file is written)
- **US3 — Combined (Phase 5)**: Depends on Phase 4 (needs pass/fail results from all four candidates)
- **Polish (Phase 6)**: Depends on Phase 5

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on other stories; all four records can be written in parallel (T005–T008 all marked [P])
- **US2 (P1)**: Depends on US1 completion; within US2, each candidate (E, F, G, H) is independent and can be worked in parallel — each writes its own agent file and experiment record
- **US3 (P2)**: Depends on US2 completion (needs win rates to determine which mechanics to stack)

### Within User Story 2

- Candidate E (T009–T012), F (T013–T016), G (T017–T020), H (T021–T024) are independent of each other
- Within each candidate: write agent → run eval → update experiment record → update README

### Parallel Opportunities

- T005, T006, T007, T008 (US1 experiment record stubs) — all parallelizable
- T009–T012 (Candidate E) can run in parallel with T013–T016 (F), T017–T020 (G), T021–T024 (H)
- T032, T033 (Phase 6 verification) are parallelizable

---

## Parallel Example: User Story 2 (all four candidates simultaneously)

```bash
# All four candidates can be developed and evaluated in parallel:
Task E: "Write agent_v16.py + run eval vs v15 + update experiment record" (T009–T011)
Task F: "Write agent_v17.py + run eval vs v15 + update experiment record" (T013–T015)
Task G: "Write agent_v18.py + run eval vs v15 + update experiment record" (T017–T019)
Task H: "Write agent_v19.py + run eval vs v15 + update experiment record" (T021–T023)

# README updates (T012, T016, T020, T024) should be batched after all evals complete
# to avoid repeated edit conflicts on the same table row area
```

---

## Implementation Strategy

### MVP First (highest-expected-impact candidate first)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: Write all four hypothesis records (US1) — can batch in minutes
4. Start with Candidate E (orbit lead fix — confirmed bug, highest expected impact): T009–T012
5. **STOP and VALIDATE**: Did it reach 55%? If yes, proven mechanic in hand. Continue to F.

### Incremental Delivery

1. Setup + Foundational → baseline confirmed
2. US1: All four hypothesis records written in parallel
3. US2: Candidates E, F, G, H evaluated (parallel or sequential)
4. US3: Combined agent_v20 built from passing mechanics
5. Polish: Docs and table finalized

### Single-Developer Sequence (priority order)

1. T001 → T002 → T003 → T004 (phases 1–2)
2. T005 → T006 → T007 → T008 (US1, can batch)
3. T009 → T010 → T011 → T012 (Candidate E — orbit lead)
4. T013 → T014 → T015 → T016 (Candidate F — transit sizing)
5. T017 → T018 → T019 → T020 (Candidate G — adaptive range)
6. T021 → T022 → T023 → T024 (Candidate H — ROI scoring)
7. T025 → T026 → T027 → T028 → T029 → T030 → T031 (Combined)
8. T032 → T033 → T034 → T035 (Polish)

---

## Notes

- **Do not modify** `eval.py` or `diagnose_v9.py` — evaluation harness is fixed
- **Do not modify** `agent_v15.py` — it is the immutable baseline for this round
- Each candidate agent builds on agent_v15 verbatim; only the targeted mechanic changes
- Win rate < 55% for a candidate → document and skip; do not include in agent_v20
- Win rate < 65% for agent_v20 → run subset tests (T028) before concluding failure
- README Agents table update is mandatory after each eval (FR-006)
- Candidate E is the only pure bug fix; Candidates F, G, H are heuristic improvements — if E alone provides a large win, it may dominate the combined agent result
