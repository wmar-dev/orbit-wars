# Tasks: Mid-Game Reward Signals and Reward-Guided Agent Experimentation

**Input**: Design documents from `/specs/008-mid-game-rewards/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: Maps to user story from spec.md (US1–US5)
- No automated test tasks — project uses manual eval runs as its test harness

---

## Phase 1: Setup

**Purpose**: Confirm shared infrastructure is in place before coding begins.

- [ ] T001 Verify `experiments/` directory exists at repo root; if not, create it
- [ ] T002 Confirm `.venv` Python environment is active and `kaggle_environments` imports cleanly: `uv run python -c "from kaggle_environments.envs.orbit_wars.orbit_wars import Planet, Fleet; print('OK')"`

**Checkpoint**: Environment confirmed — all phases can proceed.

---

## Phase 2: Foundational — reward_signal.py

**Purpose**: The core reward module required by ALL user stories. No user story work starts until this phase is complete.

**⚠️ CRITICAL**: US1, US2, US3, US4, and US5 all depend on `reward_signal.py` being correct.

- [ ] T003 Create `reward_signal.py` at repo root with module docstring, `RewardConfig` constants block (`W_CAPTURE=0.5`, `W_PRODUCTION=0.3`, `W_SHIP=0.2`, `CAPTURE_SCALE=10.0`, `PROD_SCALE=5.0`, `SHIP_SCALE=20.0`), and `zero_reward()` helper returning a zeroed TurnReward dict
- [ ] T004 Implement `_parse_obs()` private helper in `reward_signal.py` that extracts `planets` (list of Planet namedtuples) and `fleets` (list of Fleet namedtuples) from a raw obs dict/object, raising `ValueError` with a descriptive message if required fields are missing
- [ ] T005 Implement `_capture_bonus()` in `reward_signal.py`: compare `planets_prev` vs `planets_now` by planet id; sum `planet.production` for planets whose owner changed from non-player to player; normalize by `CAPTURE_SCALE`, clamp to [-1, 1]
- [ ] T006 Implement `_production_delta()` in `reward_signal.py`: diff total production on owned planets between prev and now; normalize by `PROD_SCALE`, clamp to [-1, 1]
- [ ] T007 Implement `_ship_delta()` in `reward_signal.py`: total owned ships = `sum(p.ships for p in planets if p.owner==player) + sum(f.ships for f in fleets if f.owner==player)`; diff between prev and now; normalize by `SHIP_SCALE`, clamp to [-1, 1]
- [ ] T008 Implement `_terminal_reward()` in `reward_signal.py`: given `final_rewards` list and `player` index, compute rank (1-based, rank 1 = highest reward), return `1 - 2*(rank-1)/(N-1)` where N = number of players; handle ties by awarding same rank
- [ ] T009 Implement `compute_reward()` public function in `reward_signal.py`: accepts `prev_obs`, `curr_obs`, `player`, optional `final_rewards` and `num_players`; returns TurnReward dict with keys `capture_bonus`, `production_delta`, `ship_delta`, `terminal` (null if non-terminal), `total`; on turn 0 (`prev_obs is None`) return `zero_reward()`; on terminal turn set `total = terminal` (not sum of per-turn components)

**Checkpoint**: `reward_signal.py` is complete and importable. All user story phases can now begin.

---

## Phase 3: User Story 1 — Inspect reward signals during replay (P1) 🎯 MVP

**Goal**: Verify the reward module emits one scalar per (turn, player) for a complete game.

**Independent Test**: `uv run python reward_signal.py` runs a live 2-player game via kaggle_environments, prints one TurnReward dict per turn per player, and exits cleanly. Confirm output has one line per (turn, player) across all turns and that the winning player's cumulative `total` is positive.

- [ ] T010 [US1] Add `__main__` block to `reward_signal.py` that: imports `kaggle_environments`, runs a 10-turn game between two no-op agents, calls `compute_reward()` at each step for both players, prints each TurnReward dict as JSON — manually verify output format and that all `total` values are in [-1, 1]
- [ ] T011 [US1] Run `uv run python reward_signal.py` and confirm: (a) exactly 2 rows per turn, (b) `total` is in [-1, 1] for all rows, (c) turn-0 row has all zeros, (d) final row has non-null `terminal`

**Checkpoint**: User Story 1 complete — reward module verified standalone. ✅

---

## Phase 4: User Story 3 — Plug reward module into eval harness (P3)

*(Implemented before US2 because US2's acceptance test requires the `--reward-log` flag.)*

**Goal**: `eval.py` and `eval4.py` accept `--reward-log <path>` and write a `.jsonl` file without changing existing win/loss output.

**Independent Test**: `uv run python eval.py --reward-log rewards_test.jsonl --games 5` produces `rewards_test.jsonl` with one JSON object per (game, turn, player); win/loss totals are unchanged vs. a run without the flag.

- [ ] T012 [US3] Add `--reward-log PATH` optional argument to `eval.py` argument parser (default: None); document in argparse help string
- [ ] T013 [US3] Refactor `_run_game()` in `eval.py` to accumulate per-turn observations (`prev_obs`, `curr_obs`) via a lightweight wrapper around the agent functions; pass accumulated obs list back in the return tuple when `reward_log_enabled=True`
- [ ] T014 [US3] After each game completes in `eval.py`, call `compute_reward()` for each (turn, player) pair and append TurnReward JSON objects to the `.jsonl` file (one file, append mode across all games); include `game_id` and `seed` fields in each record
- [ ] T015 [US3] Confirm `eval.py` without `--reward-log` produces identical win/loss output as before (no regression introduced by obs collection refactor)
- [ ] T016 [P] [US3] Apply the same `--reward-log` pattern to `eval4.py`: add argument, collect 4-player turn obs, write 4 rows per turn to `.jsonl`
- [ ] T017 [P] [US3] Confirm `eval4.py` without `--reward-log` produces identical output (no regression)

**Checkpoint**: User Story 3 complete — harness integration verified. US2 validation can now run. ✅

---

## Phase 5: User Story 2 — Validate reward shaping incentivizes good play (P2)

**Goal**: Confirm that `agent_v30`'s mid-game reward is consistently higher than `agent_v3`'s on seeds it wins.

**Independent Test**: Collect a 50-game log (`agent_v30` vs `agent_v3`); verify winning player has higher cumulative `total` reward in ≥80% of games (SC-002).

- [ ] T018 [US2] Run: `uv run python eval.py --agent0 agent_v30.py --agent1 agent_v3.py --games 50 --seed 0 --jobs 4 --reward-log rewards_v30_vs_v3.jsonl` — save output
- [ ] T019 [US2] Run inline analysis to verify SC-002: `uv run python -c "import json; games={}; [games.setdefault(r['game_id'],[]).append(r) for r in (json.loads(l) for l in open('rewards_v30_vs_v3.jsonl'))]; wins=sum(1 for g in games.values() if sum(r['total'] for r in g if r['player']==0)>sum(r['total'] for r in g if r['player']==1)); print(f'P0 cumulative reward > P1: {wins}/50 games ({wins*2}%)')"`
- [ ] T020 [US2] Confirm SC-002 passes (≥80% = ≥40/50 games); if it fails, inspect which reward weights are underweighted using per-component breakdown and adjust `RewardConfig` in `reward_signal.py` before retrying

**Checkpoint**: User Story 2 complete — reward shaping validated. ✅

---

## Phase 6: User Story 4 — Build a reward-guided agent variant (P4)

**Goal**: Create `agent_v31.py` that blends reward estimates into ROI scoring and achieves ≥55% win rate vs. `agent_v30`.

**Independent Test**: `uv run python eval.py --agent0 agent_v31.py --agent1 agent_v30.py --games 50 --seed 0 --jobs 4` → win rate ≥55% (≥28/50).

- [ ] T021 [US4] Create `agent_v31.py` as a copy of `agent_v30.py`; update module docstring to describe the reward-blending mechanic; add `REWARD_ALPHA = 0.3` constant to the config block
- [ ] T022 [US4] Add `import reward_signal` and a module-level `_prev_obs: dict | None = None` state variable to `agent_v31.py` for tracking the previous observation across turns
- [ ] T023 [US4] Implement `_reward_estimate(target, source, dispatch_ships)` helper in `agent_v31.py`: estimates expected `capture_bonus` (target.production / CAPTURE_SCALE if we win the attack) and expected `ship_delta` (-dispatch_ships / SHIP_SCALE); returns weighted sum using `W_CAPTURE` and `W_SHIP` imported from `reward_signal`
- [ ] T024 [US4] Modify the target-scoring loop in `agent_v31.py`: after computing `roi` per (source, target), compute `roi_max` across all candidates; blend score as `(1 - REWARD_ALPHA) * (roi / roi_max) + REWARD_ALPHA * _reward_estimate(target, source, dispatch_ships)` — use blended score for best-target selection
- [ ] T025 [US4] Update `_prev_obs` at the end of the `agent()` function in `agent_v31.py` so the reward state advances each turn
- [ ] T026 [US4] Verify SC-007 (zero-blend identical to baseline): temporarily set `REWARD_ALPHA = 0.0` in `agent_v31.py`, run `eval.py --agent0 agent_v31.py --agent1 agent_v30.py --games 20 --seed 0` — confirm win rate is ~50% (statistically indistinguishable from agent_v30 vs itself); restore `REWARD_ALPHA = 0.3`
- [ ] T027 [US4] Run primary evaluation: `uv run python eval.py --agent0 agent_v31.py --agent1 agent_v30.py --games 50 --seed 0 --jobs 4 --reward-log rewards_v31_vs_v30.jsonl`
- [ ] T028 [US4] If win rate <55%: try `REWARD_ALPHA` values of 0.1, 0.2, 0.4, 0.5 in separate 20-game runs; keep the first value that passes 55%, or document all as FAIL if none pass
- [ ] T029 [US4] Write experiment record to `experiments/2026-05-30-reward-signal-baseline.md` following the constitution format (Hypothesis, Change, Self-play result, Conclusion)

**Checkpoint**: User Story 4 complete — reward-guided agent experimented and documented. ✅

---

## Phase 7: User Story 5 — Replay analysis from reward logs (P5)

**Goal**: `reward_analysis.py` reads a `.jsonl` reward log and prints a Markdown summary by game phase in <5 seconds.

**Independent Test**: `uv run python reward_analysis.py --log rewards_v30_vs_v3.jsonl > analysis.md` completes in <5s and identifies at least one high-reward pattern (e.g., early expansion by winner).

- [ ] T030 [P] [US5] Create `reward_analysis.py` at repo root with argparse CLI (`--log PATH` required, `--games N` optional, `--player N` optional) and module docstring
- [ ] T031 [US5] Implement log loading in `reward_analysis.py`: stream-parse `.jsonl` file line by line into a `dict[game_id, list[TurnReward]]` structure; raise clear error if file not found or JSON parse fails
- [ ] T032 [US5] Implement winner/loser identification in `reward_analysis.py`: for each game, identify winner as the player with `terminal == 1.0` on the final turn (highest terminal reward); handle draws (equal terminal) by marking both as tied
- [ ] T033 [US5] Implement game-phase bucketing in `reward_analysis.py` (early: steps 1–20, mid: 21–60, late: 61+); compute per-phase averages for `total`, `capture_bonus`, `production_delta`, `ship_delta`, split by winner vs. loser
- [ ] T034 [US5] Implement Markdown summary output in `reward_analysis.py`: overall section (avg total reward winner vs. loser), per-phase table, and top-5 highest-reward events (game_id, step, player, component, value)
- [ ] T035 [US5] Run `uv run python reward_analysis.py --log rewards_v30_vs_v3.jsonl` and verify: (a) completes in <5s, (b) summary is readable, (c) winner has higher avg reward than loser in at least 2 of 3 phases

**Checkpoint**: User Story 5 complete — analysis tooling operational. ✅

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T036 Update `README.md` Agents table: if `agent_v31` passed ≥55% threshold, add it to the table with its win rate vs. `agent_v30`; bold it if it is the new best local agent
- [ ] T037 Verify SC-003 (reward logging adds <10% overhead): time `eval.py --games 20` with and without `--reward-log`; confirm overhead is within bound
- [ ] T038 Remove the `__main__` smoke-test block from `reward_signal.py` (added in T010) so the module is clean for import-only use; confirm `import reward_signal` still works after removal

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user story phases**
- **Phase 3 (US1)**: Depends on Phase 2 only
- **Phase 4 (US3)**: Depends on Phase 2 only; can run in parallel with Phase 3
- **Phase 5 (US2)**: Depends on Phase 4 (requires `--reward-log` flag to collect data)
- **Phase 6 (US4)**: Depends on Phase 2 and Phase 4 (uses `--reward-log` for experiment records)
- **Phase 7 (US5)**: Depends on Phase 4 (reads `.jsonl` files produced by Phase 5/6)
- **Phase 8 (Polish)**: Depends on all prior phases complete

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2
- **US3 (P3)**: Independent after Phase 2; implemented before US2 due to test dependency
- **US2 (P2)**: Requires US3 complete (its acceptance test uses `--reward-log`)
- **US4 (P4)**: Requires Phase 2 (reward module) and Phase 4 (reward-log for experiments)
- **US5 (P5)**: Requires Phase 4 (reads `.jsonl` log files)

### Within Each Phase

- Foundational tasks (T003–T009) must be completed in order — each builds on the previous
- US3 harness tasks (T012–T014) must be sequential; T015–T017 can run in parallel with each other
- US4 agent tasks (T021–T025) must be sequential; T026–T028 can be tried in parallel per REWARD_ALPHA value

### Parallel Opportunities

- Phase 3 (US1) and Phase 4 (US3) can run in parallel after Phase 2 completes
- T016 and T017 (eval4.py changes) can run in parallel with T015
- T030 (reward_analysis.py scaffold) can start in parallel with other US5 tasks
- T036, T037, T038 in Polish phase can all run in parallel

---

## Parallel Execution Example: Phase 4 (US3)

```bash
# After T012 (argparse) is done, these can run in parallel:
Task T013: "Refactor _run_game() in eval.py to accumulate turn obs"
Task T016: "Apply --reward-log pattern to eval4.py"
```

## Parallel Execution Example: Phase 6 (US4) — REWARD_ALPHA tuning

```bash
# If T027 (REWARD_ALPHA=0.3) fails, these can run in parallel:
Task: "Eval with REWARD_ALPHA=0.1 — 20 games"
Task: "Eval with REWARD_ALPHA=0.2 — 20 games"
Task: "Eval with REWARD_ALPHA=0.4 — 20 games"
Task: "Eval with REWARD_ALPHA=0.5 — 20 games"
```

---

## Implementation Strategy

### MVP First (User Story 1 + Foundational Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: `reward_signal.py` — foundational module
3. Complete Phase 3: US1 smoke test
4. **STOP and VALIDATE**: Reward module emits correct per-turn scalars ✅
5. Proceed to Phase 4 once baseline is confirmed

### Incremental Delivery

1. Phases 1–2 → reward_signal.py working
2. Phase 3 (US1) → standalone reward verification
3. Phase 4 (US3) → harness integration with `--reward-log`
4. Phase 5 (US2) → reward shaping validated
5. Phase 6 (US4) → reward-guided agent and experiment record
6. Phase 7 (US5) → analysis tooling
7. Phase 8 → README update, timing check, cleanup

---

## Notes

- [P] tasks operate on different files or independent eval runs — safe to parallelize
- [Story] label maps each task to a user story for traceability against spec.md
- No automated test suite — manual verification via `eval.py` runs and printed output
- Each checkpoint validates the story independently before proceeding
- Commit after each phase or logical group
- Constitution compliance: document every reward-weight experiment in `experiments/` before submitting
