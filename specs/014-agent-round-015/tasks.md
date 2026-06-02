# Tasks: Agent Round 015 — Six Improvement Candidates

**Input**: Design documents from `specs/014-agent-round-015/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: No separate test files — each candidate is validated by running `eval.py` (50 games vs agent_v47).

**Organization**: One phase per candidate (user story), each independently implementable and executable. All candidate phases can run in parallel since they produce different files.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: Which user story / candidate this task belongs to

---

## Phase 1: Setup

**Purpose**: Scaffold experiment log stubs and confirm eval tooling is working.

- [X] T001 Verify eval tooling: run `uv run python eval.py --agent0 agent_v47.py --agent1 agent_v47.py --games 4 --jobs 2` and confirm ~50% score
- [X] T002 [P] Create experiment stub `experiments/015-candidate-1-roi-mismatch.md` with Hypothesis / Change / Self-play result / Conclusion sections
- [X] T003 [P] Create experiment stub `experiments/015-candidate-2-endgame-roi.md` with Hypothesis / Change / Self-play result / Conclusion sections
- [X] T004 [P] Create experiment stub `experiments/015-candidate-3-garrison-buffer.md` with Hypothesis / Change / Self-play result / Conclusion sections
- [X] T005 [P] Create experiment stub `experiments/015-candidate-4-sender-prescreen.md` with Hypothesis / Change / Self-play result / Conclusion sections
- [X] T006 [P] Create experiment stub `experiments/015-candidate-5-fleet-sufficiency.md` with Hypothesis / Change / Self-play result / Conclusion sections
- [X] T007 [P] Create experiment stub `experiments/015-candidate-6-campaign-target.md` with Hypothesis / Change / Self-play result / Conclusion sections

---

## Phase 2: Foundational

No blocking prerequisites — all candidate phases can begin immediately after Phase 1.

---

## Phase 3: User Story 1 — ROI Scoring Mismatch Fix (Priority: P1) 🎯

**Goal**: Enemy targets scored with the actual (larger, faster) fleet speed rather than the naive `ships + 1` speed, so ROI comparisons between enemy and neutral targets are accurate.

**Independent Test**: `uv run python eval.py --agent0 agent_v48.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T008 [US1] Copy `agent_v47.py` to `agent_v48.py` and replace the module docstring to describe Candidate 1 (ROI mismatch fix, base: agent_v47)
- [X] T009 [US1] In `agent_v48.py`: modify `_roi(t, bx, by, mine)` to accept an optional fourth parameter `actual_fleet_size=None`; inside, compute `n = actual_fleet_size if actual_fleet_size is not None else (t.ships + 1)` and use `fleet_speed(n)` for the travel calculation
- [X] T010 [US1] In `agent_v48.py`: before building `roi_scores` (the list comprehension at the `candidates` loop), add a pre-computation pass — for each `(t, bx, by)` in `candidates`, if `t.owner != -1` call `_enemy_fleet_size(t, bx, by, mine.x, mine.y, initial_planets_map, angular_velocity)` to get `(ships_needed, bx2, by2)`; re-validate path safety for corrected position; store as `(t, bx2, by2, ships_needed)`; for neutrals store `(t, bx, by, t.ships + 1)`
- [X] T011 [US1] In `agent_v48.py`: update the `roi_scores` list and `blended_key` to pass `actual_fleet_size=ships_needed` to every `_roi(...)` call; update the winner unpacking accordingly
- [X] T012 [US1] In `agent_v48.py`: remove the now-redundant second call to `_enemy_fleet_size` for the best target (it was already resolved in T010); use the already-stored `ships_needed`, `bx`, `by` directly
- [X] T013 [US1] Run eval: `uv run python eval.py --agent0 agent_v48.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T014 [US1] Fill in `experiments/015-candidate-1-roi-mismatch.md` with hypothesis, exact code change (quote changed lines), win/loss record, and conclusion (pass ≥56% or fail)

**Checkpoint**: agent_v48.py complete; result recorded; pass/fail noted.

---

## Phase 4: User Story 2 — Endgame ROI Normalization (Priority: P1)

**Goal**: ROI time-decay term uses actual remaining game turns (`500 - step`) instead of a hardcoded 100, so the agent stops over-investing in distant captures late-game.

**Independent Test**: `uv run python eval.py --agent0 agent_v49.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T015 [P] [US2] Copy `agent_v47.py` to `agent_v49.py` and replace the module docstring to describe Candidate 2 (endgame ROI normalization, base: agent_v47)
- [X] T016 [US2] In `agent_v49.py`: modify `_roi(t, bx, by, mine)` to accept an optional fifth parameter `remaining_turns=100.0`; replace the hardcoded `100.0` in `max(1.0, 100.0 - travel)` with `max(1.0, remaining_turns - travel)`
- [X] T017 [US2] In `agent_v49.py`: in the `agent()` function, after `step` is extracted (line ~223), compute `remaining_turns = max(1.0, 500.0 - step)` and pass it to every `_roi(...)` call site
- [X] T018 [US2] Run eval: `uv run python eval.py --agent0 agent_v49.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T019 [US2] Fill in `experiments/015-candidate-2-endgame-roi.md` with hypothesis, exact code change, win/loss record, and conclusion

**Checkpoint**: agent_v49.py complete; result recorded; pass/fail noted.

---

## Phase 5: User Story 3 — Garrison Defense Buffer (Priority: P2)

**Goal**: When an enemy fleet threatens a planet, the garrison floor includes a buffer above the raw threat count so the planet survives at non-zero garrison after the attack lands.

**Independent Test**: `uv run python eval.py --agent0 agent_v50.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T020 [P] [US3] Copy `agent_v47.py` to `agent_v50.py` and replace the module docstring to describe Candidate 3 (garrison defense buffer, base: agent_v47)
- [X] T021 [US3] In `agent_v50.py`: locate the garrison floor line (currently `floor = max(src.production * GARRISON_FLOOR_FACTOR, threat.get(src.id, 0))`); replace with: `incoming = threat.get(src.id, 0); buffer = src.production * 2 if incoming > 0 else 0; floor = max(src.production * GARRISON_FLOOR_FACTOR, incoming + buffer)`
- [X] T022 [US3] Run eval: `uv run python eval.py --agent0 agent_v50.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T023 [US3] Fill in `experiments/015-candidate-3-garrison-buffer.md` with hypothesis, exact code change, win/loss record, and conclusion

**Checkpoint**: agent_v50.py complete; result recorded; pass/fail noted.

---

## Phase 6: User Story 4 — Sender Pre-Screening for Enemy Targets (Priority: P2)

**Goal**: The sender assignment loop excludes source planets that cannot cover the production-adjusted garrison of enemy targets, so attack opportunities aren't silently dropped when the best-scored sender is unaffordable.

**Independent Test**: `uv run python eval.py --agent0 agent_v51.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T024 [P] [US4] Copy `agent_v47.py` to `agent_v51.py` and replace the module docstring to describe Candidate 4 (sender pre-screening, base: agent_v47)
- [X] T025 [US4] In `agent_v51.py`: inside the `best_sender` inner loop (iterating over `src` in `my_planets`), after the `surplus <= 0` guard and before computing `score`, add the pre-screen block for enemy targets: `if t.owner != -1: naive_dist = math.hypot(src.x - t.x, src.y - t.y); naive_travel = naive_dist / fleet_speed(t.ships + 1); rough_needed = int(t.ships + t.production * naive_travel) + 1; if src.ships < rough_needed: continue`
- [X] T026 [US4] Run eval: `uv run python eval.py --agent0 agent_v51.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T027 [US4] Fill in `experiments/015-candidate-4-sender-prescreen.md` with hypothesis, exact code change, win/loss record, and conclusion

**Checkpoint**: agent_v51.py complete; result recorded; pass/fail noted.

---

## Phase 7: User Story 5 — Friendly Fleet Sufficiency Check (Priority: P3)

**Goal**: Skip re-targeting a planet that already has a sufficient friendly fleet in transit, preventing wasted double-dispatches to already-covered targets.

**Independent Test**: `uv run python eval.py --agent0 agent_v52.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T028 [P] [US5] Copy `agent_v47.py` to `agent_v52.py` and replace the module docstring to describe Candidate 5 (friendly fleet sufficiency check, base: agent_v47; NOTE: this is a reframe of the original committed-ships idea — do NOT subtract committed ships from garrison since the game engine already does this)
- [X] T029 [US5] In `agent_v52.py`: after the `threat` dict is built and before the `best_sender` loop, add `covered_targets = set()` and populate it: for each fleet in `raw_fleets` where `f_owner == player`, iterate over `targets`; compute predicted position using `_converged_orbit_lead` or current position; compute `expected_angle = math.atan2(y_pred - f_y, x_pred - f_x)`; if `_angle_diff(f_angle, expected_angle) < ANGLE_EPSILON`, compute `rough_needed = t.ships + 1 if t.owner == -1 else int(t.ships + t.production * (math.hypot(f_x - x_pred, f_y - y_pred) / fleet_speed(t.ships + 1))) + 1`; if `f_ships >= rough_needed`, add `t.id` to `covered_targets`
- [X] T030 [US5] In `agent_v52.py`: in the `best_sender` outer loop, skip targets whose `t.id` is in `covered_targets` (add `if t.id in covered_targets: continue` before the inner `src` loop)
- [X] T031 [US5] Run eval: `uv run python eval.py --agent0 agent_v52.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T032 [US5] Fill in `experiments/015-candidate-5-fleet-sufficiency.md` with hypothesis, exact code change, win/loss record, and conclusion

**Checkpoint**: agent_v52.py complete; result recorded; pass/fail noted.

---

## Phase 8: User Story 6 — Persistent Campaign Target (Priority: P3)

**Goal**: Each owned planet maintains a persistent attack target across turns, preventing flip-flopping and wasted partial-fleet commitments.

**Independent Test**: `uv run python eval.py --agent0 agent_v53.py --agent1 agent_v47.py --games 50 --jobs 4` achieves ≥56% win rate.

- [X] T033 [P] [US6] Copy `agent_v47.py` to `agent_v53.py` and replace the module docstring to describe Candidate 6 (persistent campaign target, base: agent_v47)
- [X] T034 [US6] In `agent_v53.py`: add module-level `_campaign: dict = {}` above the `agent()` function definition (maps `planet_id: int → (target_id: int, roi_at_assignment: float)`)
- [X] T035 [US6] In `agent_v53.py`: at the start of `agent()`, declare `global _campaign`; build a set `current_target_ids = {t.id for t in targets}` for existence checks
- [X] T036 [US6] In `agent_v53.py`: replace the `best_sender` dict entirely with a campaign-aware approach — for each `mine` in `my_planets`, check if `mine.id` has an active campaign: if yes, look up `(campaign_target_id, stored_roi)`; validate the campaign (target still exists and unowned by player; not in `covered_targets`; if the top available ROI is >30% higher than `stored_roi`, clear campaign); if campaign still valid, set `best_sender[campaign_target_id] = mine.id` and skip re-scoring for that planet; if campaign invalid or absent, fall through to normal sender scoring
- [X] T037 [US6] In `agent_v53.py`: after a dispatch move is appended for a mine planet, record or update `_campaign[mine.id] = (best_target.id, best_roi)` so the campaign persists to next turn
- [X] T038 [US6] In `agent_v53.py`: at the start of each turn, prune stale campaign entries: for each `pid` in list(`_campaign.keys()`), if `pid` not in `{p.id for p in my_planets}`, delete it (planet lost)
- [X] T039 [US6] Run eval: `uv run python eval.py --agent0 agent_v53.py --agent1 agent_v47.py --games 50 --jobs 4` and record win rate
- [X] T040 [US6] Fill in `experiments/015-candidate-6-campaign-target.md` with hypothesis, exact code change, win/loss record, and conclusion

**Checkpoint**: agent_v53.py complete; result recorded; pass/fail noted.

---

## Phase 9: Polish — Combine Passing Candidates & Promote Best Agent

**Purpose**: Merge all passing candidates (≥56% win rate vs agent_v47) into a combined agent, evaluate, and promote if it clears the combined threshold (≥60% vs agent_v47).

- [X] T041 Review results from T013, T018, T022, T026, T031, T039; list passing candidates and their win rates
- [X] T042 Copy `agent_v47.py` to `agent_v5X.py` (number is next sequential after v53, e.g. `agent_v54.py`) and apply all passing candidate changes in this order: C1 → C2 → C3 → C4 → C5 → C6 (apply only those that passed individually)
- [X] T043 If C1 and C2 both pass and are being combined: merge their `_roi` parameter changes carefully — the combined function signature is `_roi(t, bx, by, mine, actual_fleet_size=None, remaining_turns=100.0)` and the pre-computation of `ships_needed` from C1 also feeds the `remaining_turns` ROI call
- [X] T044 Run combined eval vs agent_v47: `uv run python eval.py --agent0 agent_v5X.py --agent1 agent_v47.py --games 50 --jobs 4` and record result
- [X] T045 Run combined eval vs agent_v38: `uv run python eval.py --agent0 agent_v5X.py --agent1 agent_v38.py --games 50 --jobs 4` and record result
- [X] T046 [P] Create `experiments/015-combined-agent.md` with: list of passing candidates, combined win rates vs v47 and v38, and conclusion
- [X] T047 If combined agent achieves ≥60% vs agent_v47: update `README.md` Agents table — bold the new best agent row, add win rates for each individual candidate and the combined agent
- [X] T048 If combined agent achieves ≥60% vs agent_v47: update `Makefile` `AGENT` and `RENDER_AGENT` variables to point to the new combined agent file
- [X] T049 If combined agent achieves ≥60% vs agent_v47: copy combined agent to `main.py` per submission workflow; verify import check passes (`grep -n "^from \|^import " main.py` shows no unresolved local imports)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002–T007 are all parallelizable
- **Foundational (Phase 2)**: Empty — no blocking prerequisites
- **Candidate Phases (3–8)**: All depend only on Phase 1; all **six phases can run in parallel** since each produces a different file
- **Polish (Phase 9)**: Depends on all six candidate phases completing

### User Story Dependencies

- **US1 (P1)**: Independent — starts after Phase 1
- **US2 (P1)**: Independent — starts after Phase 1; can run in parallel with US1
- **US3 (P2)**: Independent — starts after Phase 1
- **US4 (P2)**: Independent — starts after Phase 1
- **US5 (P3)**: Independent — starts after Phase 1
- **US6 (P3)**: Independent — starts after Phase 1; most complex, best done last if working sequentially

### Within Each User Story

- Copy → Implement → Eval → Document (strict sequence per candidate)
- Eval command must complete before filling experiment log

---

## Parallel Example: All Six Candidates

```bash
# After Phase 1 completes, all six can run in parallel:
Task: "Implement and evaluate agent_v48.py (C1: ROI mismatch fix)"
Task: "Implement and evaluate agent_v49.py (C2: Endgame normalization)"
Task: "Implement and evaluate agent_v50.py (C3: Garrison buffer)"
Task: "Implement and evaluate agent_v51.py (C4: Sender pre-screen)"
Task: "Implement and evaluate agent_v52.py (C5: Fleet sufficiency)"
Task: "Implement and evaluate agent_v53.py (C6: Campaign target)"
```

---

## Implementation Strategy

### MVP First (P1 Candidates)

1. Complete Phase 1: Setup (T001–T007)
2. Complete Phase 3: US1 ROI mismatch (T008–T014) — highest-confidence candidate
3. Complete Phase 4: US2 Endgame normalization (T015–T019) — complementary to US1
4. **STOP and VALIDATE**: If both pass, they can be combined into an early partial combined agent

### Full Run

1. Complete Phase 1
2. Complete Phases 3–8 (in parallel or sequentially)
3. Complete Phase 9: combine passing candidates and promote

### Passing Threshold Reminder

- Individual: ≥56% win rate vs agent_v47 over 50 games
- Combined: ≥60% win rate vs agent_v47, ≥72% vs agent_v38
- Self-play symmetry: ~50% score (all draws = acceptable)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- Eval commands use `--jobs 4` for parallelism; adjust for your machine
- Do NOT modify `agent_v47.py` — all candidates are copies
- Each candidate file must be self-contained (no imports from helper.py unless it was already in v47)
- Record raw win/loss counts (e.g. 31W/19L/0D), not just percentages
- If a candidate scores exactly 56% (28W/22L), consider running a second 50-game batch to confirm
