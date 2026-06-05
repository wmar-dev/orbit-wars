# Tasks: Game Replay Learning

**Input**: Design documents from `specs/020-game-replay-learning/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Organization**: Tasks grouped by user story — each story is an independently runnable increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directories and wire up shared utilities used by all scripts.

- [ ] T001 Create `replays/` directory and add it to `.gitignore` (large JSON files, dev-only)
- [ ] T002 [P] Create `record_replays.py` as an empty CLI stub with argparse skeleton (`--opponent`, `--games`, `--out-dir`, `--our-agent`) at repo root
- [ ] T003 [P] Create `analyze_replays.py` as an empty CLI stub with argparse skeleton (`--dir`, `--opponent`, `--buckets`) at repo root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The agent recording shim and replay serializer — both scripts depend on these before any game-state data can be captured or stored.

**⚠️ CRITICAL**: All user story work depends on this phase being complete.

- [ ] T004 Implement `_make_recording_shim(agent_fn, player_idx, move_log)` in `record_replays.py` — wraps an agent callable, appends `(turn, player_idx, moves)` to `move_log` each call, returns the same moves unchanged
- [ ] T005 Implement `_compute_planet_counts(planets_raw, n_players)` and `_compute_ship_totals(planets_raw, fleets_raw, n_players)` helper functions in `record_replays.py` — derive per-player planet count and total ship count from raw obs fields
- [ ] T006 Implement `_compute_divergence_turn(turns)` in `record_replays.py` — scans TurnRecord list and returns the first turn index where `max(counts[i]/counts[j]) >= 2.0` for planets or ships; returns `None` if never reached
- [ ] T007 Implement `_serialize_replay(agents, opponent_file, outcome, turn_records)` in `record_replays.py` — builds and returns the full Replay dict matching the v1.0 schema in `contracts/replay-schema.md`; includes `version`, `recorded_at`, `agents`, `opponent_file`, `outcome`, `turns`
- [ ] T008 Implement `_save_replay(replay_dict, out_dir, opponent_slug, game_idx)` in `record_replays.py` — writes JSON to `{out_dir}/replay_{opponent_slug}_{YYYYMMDD_HHMMSS}_{game_idx:03d}.json`; creates `out_dir` if absent

**Checkpoint**: Shim, serializer, and save helpers are ready — game recording can now be implemented in US1.

---

## Phase 3: User Story 1 — Run Games and Inspect Turn-by-Turn State (Priority: P1) 🎯 MVP

**Goal**: Run N games, record complete per-turn state, save replay JSON files to disk, browse turn-by-turn from the CLI.

**Independent Test**: `python record_replays.py --opponent opponent_agents/slawekbiel_agent.py --games 1` produces a valid JSON file in `replays/`; browsing with `python analyze_replays.py` prints per-game outcome without error.

### Implementation for User Story 1

- [ ] T009 [US1] Implement the main game-recording loop in `record_replays.py` — loads our agent and opponent via `importlib` (with `sys.modules` registration fix), wraps both in `_make_recording_shim`, calls `env.run([shim_a, shim_b])`, collects raw obs from each step's state
- [ ] T010 [US1] Extract `TurnRecord` from each env step in the recording loop — build `planets` list (id, x, y, radius, owner, ships, production), `fleets` list (id, owner, ships, source, destination, eta), `moves` from shim log, `planet_counts`, `ship_totals`
- [ ] T011 [US1] Compute `Outcome` after each game ends — winner (player with higher reward, or `null` for draw), `end_turn`, `final_planets`, `final_ships`, `divergence_turn` (via T006), `total_dispatches`
- [ ] T012 [US1] Wire the recording loop to `_serialize_replay` and `_save_replay` — each completed game is written to disk before the next game starts; print filename on save
- [ ] T013 [US1] Add side-alternation to the recording loop in `record_replays.py` — even games: our agent is player 0; odd games: opponent is player 0 (same pattern as `eval_opponents.py`)
- [ ] T014 [US1] Implement `_load_replays(directory, opponent_slug=None)` in `analyze_replays.py` — globs JSON files, filters by opponent slug in filename if provided, returns list of parsed replay dicts; prints count of files loaded
- [ ] T015 [US1] Implement turn-by-turn display in `analyze_replays.py` — given a single replay, print a compact table: turn | our_planets | opp_planets | our_ships | opp_ships | our_dispatches | opp_dispatches; add `--replay <file>` flag to trigger this mode

**Checkpoint**: `record_replays.py` records games; `analyze_replays.py --replay <file>` displays turn-by-turn state. User Story 1 is independently testable.

---

## Phase 4: User Story 2 — Compare Agent Behavior Across a Batch of Games (Priority: P2)

**Goal**: Aggregate statistics across 20 games — per-turn-bucket averages, win rate, divergence distribution — printed as a readable summary table.

**Independent Test**: `python record_replays.py --games 20` then `python analyze_replays.py` prints a summary with per-bucket averages for both agents and a divergence turn distribution without error.

### Implementation for User Story 2

- [ ] T016 [US2] Implement `_bucket_index(turn, buckets)` and `_aggregate_stats(replays, buckets)` in `analyze_replays.py` — computes per-bucket averages for planet counts, ship totals, and dispatches per turn for each player across all replays
- [ ] T017 [US2] Implement `_divergence_stats(replays)` in `analyze_replays.py` — collects divergence turns from losses, returns min/median/max and count; handles games with no divergence recorded
- [ ] T018 [US2] Implement `_print_summary(stats, divergence_stats, replays)` in `analyze_replays.py` — prints the full summary table: win rate, per-bucket table (our agent / opponent), divergence distribution, per-game outcome list (matching the format in `contracts/replay-schema.md`)
- [ ] T019 [US2] Wire `_aggregate_stats`, `_divergence_stats`, and `_print_summary` into the default `analyze_replays.py` main path (no `--replay` flag) with `--buckets` parsing (comma-separated integers → list of ints)
- [ ] T020 [US2] Add `--opponent` filter to `analyze_replays.py` main path — passes slug to `_load_replays`; prints "No replays found" and exits 0 if filter yields nothing

**Checkpoint**: `analyze_replays.py` prints a complete batch summary. User Story 2 is independently testable.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Completeness, error handling, and the Claude skill integration.

- [ ] T021 Add error handling to `record_replays.py` — catch agent exceptions mid-game, save partial replay up to the error turn with a note in `outcome` (`"error": "<message>"`), continue to next game
- [ ] T022 [P] Add `--our-agent` dynamic loading to `record_replays.py` — use same `importlib` + `sys.modules` pattern as `eval_opponents.py`; default to `agent_v56.py`; print agent names at start
- [ ] T023 [P] Create `experiments/` directory if it does not exist and add a `.gitkeep`; update `.gitignore` to keep the directory but not its contents if desired
- [ ] T024 Validate the `/analyze-replay` skill end-to-end — run `record_replays.py --games 5`, then invoke `/analyze-replay` inside a Claude Code session; confirm it loads files, prints the summary table, identifies ≥3 behavioral differences, and writes to `experiments/`
- [ ] T025 [P] Update `opponent_agents/README.md` — add note pointing to `record_replays.py` and `/analyze-replay` skill for replay-based analysis
- [ ] T026 [P] Run `quickstart.md` validation end-to-end — execute each command in the quickstart, confirm all produce expected output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately; T002 and T003 can run in parallel
- **Phase 2 (Foundational)**: Depends on Phase 1 — blocks all user story work; T004–T008 are sequential within the phase (each builds on the previous helper)
- **Phase 3 (US1)**: Depends on Phase 2 complete — T009 → T010 → T011 → T012 are sequential; T013–T015 follow T012
- **Phase 4 (US2)**: Depends on Phase 3 complete (needs `_load_replays` from T014) — T016 → T017 → T018 → T019 → T020 sequential
- **Phase 5 (Polish)**: Depends on both US1 and US2 complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 foundational helpers
- **US2 (P2)**: Depends on US1 for `_load_replays` (T014) — cannot start until T014 is complete

### Within Each User Story

- Recording loop tasks (T009–T012) must run sequentially — each adds a layer on top of the previous
- Analysis tasks (T016–T019) must run sequentially — each builds on the aggregation helpers
- Polish tasks (T021, T022, T023) are independent and can run in parallel

### Parallel Opportunities

- T002 and T003 (stubs) in Phase 1
- T004–T008 each target separate helper functions — could be split if multiple agents are working
- T022 and T023 in Phase 5 are independent of T021

---

## Parallel Example: Phase 2

```bash
# These foundational helpers are conceptually independent (separate functions):
Task T004: _make_recording_shim() in record_replays.py
Task T005: _compute_planet_counts() + _compute_ship_totals() in record_replays.py
Task T006: _compute_divergence_turn() in record_replays.py
# T007 and T008 depend on T004-T006 completing
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T008)
3. Complete Phase 3: User Story 1 (T009–T015)
4. **STOP and VALIDATE**: `python record_replays.py --games 1` → `python analyze_replays.py --replay replays/<file>.json`
5. US1 complete: replays recorded, turn-by-turn browsable

### Incremental Delivery

1. Setup + Foundational → helpers ready
2. US1 complete → replay recording works, turn-by-turn display works (MVP)
3. US2 complete → batch summary + divergence statistics work
4. Polish → error handling, skill validation, quickstart confirmed

---

## Notes

- `[P]` tasks target different functions or files — safe to parallelize
- All `record_replays.py` recording functions import only stdlib + `kaggle_environments` (no new dependencies)
- The `sys.modules` registration fix from `eval_opponents.py` (T009) is essential for PyTorch-backed opponents like slawekbiel
- The `/analyze-replay` Claude skill (T024) is the capstone — it uses the replay files produced by all prior tasks
- Replay files are intentionally gitignored; re-run `record_replays.py` to regenerate
