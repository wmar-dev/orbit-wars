# Tasks: Agent Improvement Experiments — Round 3

**Input**: Design documents from `specs/007-more-agent-experiments/`

**Prerequisites**: [plan.md](plan.md) | [spec.md](spec.md) | [research.md](research.md) | [data-model.md](data-model.md) | [quickstart.md](quickstart.md)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task serves (US1–US4)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the 4-player evaluation harness that diagnostics and combined-agent validation depend on.

- [x] T001 Create eval4.py 4-player evaluation harness at eval4.py — mirrors eval.py structure; runs `env.run([agent, opponent, opponent, opponent])`; reports per-game rank (1–4) and aggregate average rank, win rate, mean elimination turn; CLI: `python eval4.py --agent <file> --opponent <file|random> --games N`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish 4-player baselines and diagnose the v8→v15 leaderboard regression before any new agent work begins. Results inform Candidate M/N design and combined-agent tuning.

**⚠️ CRITICAL**: Experiment records for all candidates must be written before their agent files.

- [x] T002 Run 4-player baseline diagnostic for agent_v8.py: `python eval4.py --agent agent_v8.py --opponent random --games 20`; record average rank and win rate
- [x] T003 [P] Run 4-player baseline diagnostic for agent_v20.py: `python eval4.py --agent agent_v20.py --opponent random --games 20`; record average rank and win rate
- [x] T004 Record 4-player baseline results and regression analysis in experiments/2026-05-30-4p-baseline-diagnosis.md — note rank gap between v8 and v20; identify which hypothesis (A/B/C from research.md D-007) best explains the gap

**Checkpoint**: 4-player baseline established — all user story work can now begin.

---

## Phase 3: User Story 1 — Identify and Hypothesize (Priority: P1) 🎯

**Goal**: All six experiment records written with hypotheses before any agent file is created.

**Independent Test**: Confirm that experiment records for Candidates I, J, K, L, M, and N exist in `experiments/` with hypothesis, change description, and ≥55% pass threshold documented. No agent files exist yet.

- [x] T005 [P] [US1] Write experiment record for Candidate I (reactive defense dispatch) in experiments/2026-05-30-candidate-i-reactive-defense.md — hypothesis: targeted defense on certain-loss planets saves ships that broad Candidate C (10%) wasted; change: scan obs.fleets each turn, reinforce only when projected_garrison < incoming fleet; pass threshold ≥55% score vs agent_v20
- [x] T006 [P] [US1] Write experiment record for Candidate J (smooth adaptive range) in experiments/2026-05-30-candidate-j-smooth-adaptive-range.md — hypothesis: power-law formula `2.0 * ratio**0.25` avoids the catastrophic contraction of Candidate G (0%); change: replace `RANGE_FACTOR = 2.0` constant with dynamic formula clamped to [1.5, 3.5]; pass threshold ≥55% score vs agent_v20
- [x] T007 [P] [US1] Write experiment record for Candidate K (enemy-territory priority) in experiments/2026-05-30-candidate-k-enemy-priority.md — hypothesis: 1.5× ROI multiplier for enemy-owned targets when winning by ≥1.5× ratio ends games faster than neutral expansion; change: conditional multiplier in `_roi_k()` replacing `_roi()` when condition met; pass threshold ≥55% score vs agent_v20
- [x] T008 [P] [US1] Write experiment record for Candidate L (two-source coordinated attack) in experiments/2026-05-30-candidate-l-two-source-attack.md — hypothesis: large enemy strongholds permanently skipped by single-sender can be flipped by coordinating 2 nearby sources; change: fallback loop after single-sender that finds top-2 sources jointly covering `target.ships + 1`; pass threshold ≥55% score vs agent_v20
- [x] T009 [P] [US1] Write experiment record for Candidate M (4P neutral-first when losing) in experiments/2026-05-30-candidate-m-4p-neutral-expansion.md — hypothesis: when trailing in 4-player, attacking any opponent invites retaliation from 2 others; cheap neutral captures build production without triggering multi-opponent response; change: 2× ROI multiplier for neutral planets (owner == -1) when own_total < min(opponent totals); 4-player only
- [x] T010 [P] [US1] Write experiment record for Candidate N (4P focus-fire on leader) in experiments/2026-05-30-candidate-n-4p-focus-fire.md — hypothesis: letting the leading opponent snowball loses 4-player games; targeting their planets disrupts their growth while spending chips on a fair fight; change: 1.3× ROI multiplier for planets owned by the player with the highest ship total; 4-player only

**Checkpoint**: All 6 experiment records exist — US2 can now begin.

---

## Phase 4: User Story 2 — Run Isolated Mechanic Experiments (Priority: P1)

**Goal**: Each of the four 2-player candidates implemented and evaluated; results recorded.

**Independent Test**: Run `python eval.py --agent0 agent_v21.py --agent1 agent_v20.py --games 20` through all four candidates; each experiment record has a recorded win rate and PASS/FAIL conclusion.

### Implement candidates (can run in parallel)

- [x] T011 [P] [US2] Implement agent_v21.py (Candidate I: reactive defense dispatch) — copy agent_v20.py; add defense scan loop before offensive loop using `obs.get("fleets", [])`; dispatch reinforcement when `projected_garrison < incoming.ships`; only reinforce if source surplus ≥ deficit; source skips offensive dispatch that turn; update docstring
- [x] T012 [P] [US2] Implement agent_v22.py (Candidate J: smooth adaptive range) — copy agent_v20.py; replace `RANGE_FACTOR = 2.0` with per-turn computation `max(1.5, min(3.5, 2.0 * (own_total / max(1, enemy_total)) ** 0.25))`; `enemy_total` = sum of ships on opponent-owned planets only; update docstring
- [x] T013 [P] [US2] Implement agent_v23.py (Candidate K: enemy-territory priority) — copy agent_v20.py; add `_roi_k()` that applies 1.5× multiplier to `_roi()` result for enemy-owned targets when `own_total / max(1, enemy_total) ≥ 1.5`; replace `_roi()` calls with `_roi_k()` in candidate scoring; update docstring
- [x] T014 [P] [US2] Implement agent_v24.py (Candidate L: two-source coordinated attack) — copy agent_v20.py; after single-sender loop, add fallback: find target with highest ROI that no single source can afford; if top-2 sources by surplus jointly cover `target.ships + 1` and both within `range_factor`, dispatch both (each sends `ceil(needed/2)` ships); update docstring

### Evaluate candidates and record results (each independent after its implementation)

- [x] T015 [US2] Evaluate agent_v21.py: run `python eval.py --agent0 agent_v21.py --agent1 agent_v20.py --games 20 --seed 0`; update experiments/2026-05-30-candidate-i-reactive-defense.md with win rate and PASS/FAIL; update README.md Agents table
- [x] T016 [P] [US2] Evaluate agent_v22.py: run `python eval.py --agent0 agent_v22.py --agent1 agent_v20.py --games 20 --seed 0`; update experiments/2026-05-30-candidate-j-smooth-adaptive-range.md with win rate and PASS/FAIL; update README.md Agents table
- [x] T017 [P] [US2] Evaluate agent_v23.py: run `python eval.py --agent0 agent_v23.py --agent1 agent_v20.py --games 20 --seed 0`; update experiments/2026-05-30-candidate-k-enemy-priority.md with win rate and PASS/FAIL; update README.md Agents table
- [x] T018 [P] [US2] Evaluate agent_v24.py: run `python eval.py --agent0 agent_v24.py --agent1 agent_v20.py --games 20 --seed 0`; update experiments/2026-05-30-candidate-l-two-source-attack.md with win rate and PASS/FAIL; update README.md Agents table

**Checkpoint**: All four candidates evaluated — passing mechanics (≥55%) identified for US3.

---

## Phase 5: User Story 3 — Build Combined Agent (Priority: P2)

**Goal**: agent_v25.py combining all passing 2-player mechanics plus 4P-specific candidates M and N; passes ≥65% vs agent_v20 in 2-player and avg rank ≤ 2.0 in 4-player.

**Independent Test**: `python eval.py --agent0 agent_v25.py --agent1 agent_v20.py --games 20` returns ≥65%; `python eval4.py --agent agent_v25.py --opponent random --games 20` returns avg rank ≤ 2.0; `python diagnose_v9.py --agent agent_v25.py --games 20` returns 0 sun/OOB losses.

- [x] T019 [US3] Review experiment records from T015–T018; list all candidates with ≥55% win rate; document the selection in experiments/2026-05-30-combined-agent-v25.md (hypothesis section)
- [x] T020 [US3] Implement agent_v25.py — copy agent_v20.py; integrate all passing mechanics in the order defined in research.md D-005: (1) smooth adaptive range (J, if passed), (2) detect player count for 4P gates, (3) reactive defense (I, if passed), (4) enemy-priority ROI (K, if passed) + Candidate M neutral bias (4P-gated), (5) Candidate N focus-fire multiplier (4P-gated), (6) two-source fallback (L, if passed); set `GARRISON_FLOOR_FACTOR = 7` inside 4P-gated block; update docstring listing all included mechanics
- [x] T021 [US3] Evaluate agent_v25.py 2-player: run `python eval.py --agent0 agent_v25.py --agent1 agent_v20.py --games 20 --seed 0`; record win rate in experiment file; if <65%, run mechanic subsets per research.md D-005 to isolate regressions before proceeding
- [x] T022 [P] [US3] Evaluate agent_v25.py 4-player vs random: run `python eval4.py --agent agent_v25.py --opponent random --games 20`; record avg rank in experiment file; compare to v8 and v20 baselines from T002/T003
- [x] T023 [P] [US3] Evaluate agent_v25.py 4-player vs agent_v20: run `python eval4.py --agent agent_v25.py --opponent agent_v20.py --games 20`; record avg rank in experiment file
- [x] T024 [US3] Safety audit: run `python diagnose_v9.py --agent agent_v25.py --games 20`; verify 0 sun losses and 0 OOB losses; record in experiment file
- [x] T025 [US3] Update experiments/2026-05-30-combined-agent-v25.md with all results (2P win rate, 4P rank, safety); write conclusion
- [x] T026 [US3] Update README.md Agents table with agent_v25 entry; bold if it passes all gates (≥65% vs v20, 0 safety violations)

**Checkpoint**: agent_v25 fully evaluated — if all gates pass, feature is complete. If not, proceed to US4.

---

## Phase 6: User Story 4 — Iterate Until a Better Agent Exists (Priority: P2)

**Purpose**: If Round 3 does not yield a combined agent beating agent_v20 by ≥65%, additional rounds continue with revised hypotheses.

**Independent Test**: A new combined agent beats the previous best by ≥65% over 20 games.

- [x] T027 [US4] If agent_v25 fails the ≥65% 2-player gate: run mechanic subset evaluation to isolate the regressing mechanic (`eval.py` with each subset of passing mechanics); document findings
- [x] T028 [US4] Revise hypotheses for Round 4 (v26–v29): write new experiment records in experiments/ incorporating failure analysis from T027; at minimum one new hypothesis must differ from all prior attempts
- [x] T029 [P] [US4] Implement Round 4 candidates (agent_v26–v29): follow same protocol as Phase 4 (experiment record first, then agent file, then evaluation); baseline for Round 4 is agent_v20 (or agent_v25 if it partially passed)
- [x] T030 [US4] Build and evaluate combined agent_v30: follow same protocol as Phase 5; repeat until a combined agent passes ≥65% vs its round's baseline

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T031 Update quickstart.md with any eval4.py flag changes discovered during T001 implementation (correct command syntax)
- [x] T032 [P] Verify all experiment records are complete (all 6 records + combined + 4P baseline have hypothesis, change, result, conclusion fields)
- [x] T033 [P] Confirm README.md Agents table is current and the best-performing agent is bolded

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 can start immediately
- **Foundational (Phase 2)**: T002–T004 require T001; T003 can run parallel with T002
- **US1 (Phase 3)**: T005–T010 require no code — can run in parallel with Phase 2 after T001
- **US2 (Phase 4)**: T011–T014 require Phase 3 records complete (constitution gate); T015–T018 require their paired implementation
- **US3 (Phase 5)**: T019–T026 require Phase 4 complete
- **US4 (Phase 6)**: T027–T030 run only if T021 fails the ≥65% gate
- **Polish (Phase 7)**: Requires US3 complete

### User Story Dependencies

- **US1 (P1)**: Starts immediately after Phase 1 — parallel with Phase 2 diagnostics
- **US2 (P1)**: Depends on US1 (experiment records gate); implementations T011–T014 can run in parallel
- **US3 (P2)**: Depends on US2 (needs passing mechanic list)
- **US4 (P2)**: Conditional on US3 failing — not needed if agent_v25 passes all gates

### Within Each User Story

- Experiment record before agent file (FR-001, constitution IV)
- Implementation before evaluation
- Evaluation before combined agent decision

### Parallel Opportunities

- T002 and T003: run simultaneously (different agent files)
- T005–T010: all 6 records can be written simultaneously
- T011–T014: all 4 candidate implementations simultaneously
- T015–T018: each eval is independent after its paired implementation
- T022 and T023: both 4-player eval runs can run simultaneously

---

## Parallel Example: User Story 2

```bash
# Implement all 4 candidates simultaneously:
Task T011: "Implement agent_v21.py (Candidate I: reactive defense) in agent_v21.py"
Task T012: "Implement agent_v22.py (Candidate J: smooth adaptive range) in agent_v22.py"
Task T013: "Implement agent_v23.py (Candidate K: enemy priority) in agent_v23.py"
Task T014: "Implement agent_v24.py (Candidate L: two-source attack) in agent_v24.py"

# Then evaluate all 4 simultaneously:
Task T015: "Evaluate agent_v21.py vs agent_v20.py (20 games)"
Task T016: "Evaluate agent_v22.py vs agent_v20.py (20 games)"
Task T017: "Evaluate agent_v23.py vs agent_v20.py (20 games)"
Task T018: "Evaluate agent_v24.py vs agent_v20.py (20 games)"
```

---

## Implementation Strategy

### MVP (User Stories 1 + 2 only)

1. Complete Phase 1: Create eval4.py
2. Complete Phase 2: Baselines (can overlap with Phase 3)
3. Complete Phase 3: Write all experiment records
4. Complete Phase 4: Implement and evaluate v21–v24
5. **STOP and check**: ≥1 mechanic must pass ≥55% to proceed

### Full Delivery

1. Setup + Foundational → baselines established
2. US1 (records) → US2 (experiments) → US3 (combined v25) → validate all gates
3. If gates pass: update README, feature complete
4. If not: US4 iteration until goal is met

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- Constitution IV gate: **experiment record must exist before its agent file is created**
- 2-player pass threshold: ≥55% **score** vs agent_v20 over 20 games (score = wins + 0.5×draws / 20; draws count as 0.5, not 0)
- 4-player pass threshold: avg rank ≤ 2.0 vs 3× random over 20 games
- Combined agent 2P target: ≥65% vs agent_v20
- Safety requirement: 0 sun losses, 0 OOB losses via diagnose_v9.py
- Update README.md Agents table after every evaluation (FR-006)
