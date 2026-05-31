---

description: "Task list for RL-Optimized Agent"
---

# Tasks: RL-Optimized Agent

**Input**: Design documents from `specs/011-rl-optimize-agent/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `rl/` training directory, install PyTorch and gymnasium, and verify the kaggle-environments integration before any training code is written.

- [X] T001 Create `rl/` directory structure: `rl/checkpoints/`, `rl/logs/`
- [X] T002 Add `torch` and `gymnasium` to `.venv` via `uv pip install torch gymnasium`
- [X] T003 [P] Verify kaggle orbit_wars env boots: `uv run python -c "from kaggle_environments import make; env = make('orbit_wars'); print('ok')"`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build `rl/obs.py` (observation encoder) and `rl/env.py` (gymnasium wrapper) — both must be complete and smoke-tested before any training loop can run.

**⚠️ CRITICAL**: No training work can begin until this phase is complete.

- [X] T004 Implement `rl/obs.py`: `encode_obs(obs, player_id) -> (np.ndarray[319], np.ndarray[52])` using the sorted padded layout from data-model.md (planets sorted by angle, fleets by distance, comets by path_index; owner one-hot encoding; boolean mask bits appended)
- [X] T005 Implement `rl/env.py`: `OrbitWarsEnv(gymnasium.Env)` with `reset(opponent)`, `step(action)`, `MultiDiscrete([12,12,5])` action space, `Box(319,)` observation space; uses `env.train([None, opponent])` kaggle trainer API; computes reward via inlined `reward_signal.py` constants
- [X] T006 Smoke test env: run 1 complete episode, assert obs shape is `(319,)`, reward is non-zero, `done` fires before step 250; fix any kaggle API shape mismatches

**Checkpoint**: Foundation ready — `OrbitWarsEnv` produces valid obs/reward/done; training loops can now be built.

---

## Phase 3: User Story 1 — Train RL Agent via Self-Play (Priority: P1) 🎯 MVP

**Goal**: A training loop runs, produces checkpoints, and logs reward progression over episodes. At least one algorithm (PPO) trains without crashing for 1,000 episodes.

**Independent Test**: Launch `uv run python rl/ppo.py --episodes 100 --opponent random`; confirm checkpoint file created in `rl/checkpoints/`, CSV log written to `rl/logs/`, reward curve shows non-trivial signal (not always 0 or −1).

### Implementation for User Story 1

- [X] T007 [US1] Implement `rl/ppo.py`: CleanRL-style PPO with action masking (−1e9 on invalid logits), GAE (γ=0.99, λ=0.95), mini-batch updates (batch=64, 4 epochs/update), separate actor and critic heads sharing a 2-layer 256-unit MLP backbone; CLI args `--episodes`, `--opponent`, `--checkpoint-dir`, `--device`; saves checkpoint every 200 episodes; logs episode reward to `rl/logs/ppo_train.csv`
- [X] T008 [US1] Implement `rl/a2c.py`: same architecture as PPO but replace clipped PPO loss with plain policy gradient loss (no clipping, no importance sampling); share as much code with `ppo.py` as possible; same CLI interface and checkpoint/log conventions
- [X] T009 [P] [US1] Implement `rl/dqn.py`: DQN with prioritized experience replay (buffer size 10000, α=0.6, β=0.4), action masking applied to Q-values (−1e9 on invalid actions before argmax), target network (update every 200 steps), ε-greedy exploration (ε=1.0→0.05 over 500 episodes); same CLI interface and checkpoint/log conventions
- [X] T010 [US1] Train PPO for 1,000 episodes using staged opponent schedule: episodes 0–200 vs `"random"`, 200–500 vs `agent_v38.py`, 500+ mixed 50/50; verify reward curve trends upward; save best checkpoint to `rl/checkpoints/ppo_best.pt`
- [ ] T011 [P] [US1] Train DQN for 1,000 episodes with same staged schedule; save best checkpoint to `rl/checkpoints/dqn_best.pt`
- [ ] T012 [P] [US1] Train A2C for 1,000 episodes with same staged schedule; save best checkpoint to `rl/checkpoints/a2c_best.pt`
- [X] T013 [US1] Write `experiments/011-rl-ppo-baseline.md` with hypothesis, hyperparameters, training curve summary, and placeholder result/conclusion fields (to be filled after evaluation)
- [X] T014 [P] [US1] Write `experiments/011-rl-dqn-baseline.md` with same structure
- [X] T015 [P] [US1] Write `experiments/011-rl-a2c-baseline.md` with same structure

**Checkpoint**: All three algorithms have trained for 1,000 episodes and saved best checkpoints. Reward curves show non-trivial learning. Experiment records exist.

---

## Phase 4: User Story 2 — Evaluate RL Agent vs agent_v38 (Priority: P1)

**Goal**: Each trained RL checkpoint is exported to a standalone agent file and evaluated 50 games vs agent_v38 using `eval.py`. Results are recorded in experiment files.

**Independent Test**: `uv run python eval.py --agent0 agent_v39.py --agent1 agent_v38.py --games 50 --seed 0` produces a score; `diagnose_v9.py` reports 0 sun/OOB losses.

### Implementation for User Story 2

- [X] T016 Implement `rl/export.py`: loads a checkpoint `.pt`, extracts `state_dict` as numpy arrays, base64-encodes via `pickle.dumps` + `base64.b64encode`, writes a self-contained `agent_vNN.py` from template with hardcoded `WEIGHTS_B64` and numpy forward pass; CLI args `--checkpoint`, `--output`, `--verify` (checks numpy≈torch to 1e-5 tolerance)
- [X] T017 [US2] Export PPO best checkpoint → `agent_v39.py`; verify self-containment (`grep -n "^from \|^import "` passes Principle VI allowlist: math, numpy, base64, pickle, collections only)
- [ ] T018 [P] [US2] Export DQN best checkpoint → `agent_v40.py`; same self-containment check
- [ ] T019 [P] [US2] Export A2C best checkpoint → `agent_v41.py`; same self-containment check
- [X] T020 [US2] Evaluate `agent_v39.py` (PPO) vs `agent_v38.py`: `eval.py --games 50 --seed 0`; run `diagnose_v9.py`; fill result + conclusion fields in `experiments/011-rl-ppo-baseline.md`
- [ ] T021 [P] [US2] Evaluate `agent_v40.py` (DQN) vs `agent_v38.py`; fill `experiments/011-rl-dqn-baseline.md`
- [ ] T022 [P] [US2] Evaluate `agent_v41.py` (A2C) vs `agent_v38.py`; fill `experiments/011-rl-a2c-baseline.md`
- [ ] T023 [US2] Select best RL agent: highest score vs agent_v38 among the three that also passes 0 sun/OOB gate; if none pass ≥55%, extend evaluation to 100 games for any scoring 45–55% before final determination

**Checkpoint**: Best RL agent identified. Experiment records complete. Go/no-go decision made for Kaggle submission.

---

## Phase 5: User Story 3 — Submit Best RL Agent to Kaggle (Priority: P2)

**Goal**: The best RL agent passes smoke test, is submitted to Kaggle, and the returned public score is recorded in SUBMISSIONS.md.

**Independent Test**: `make test AGENT=<best_rl_agent>.py` passes; `make submit` returns a submission ID; SUBMISSIONS.md updated with score within 24 hours of submission completing.

### Implementation for User Story 3

- [ ] T024 [US3] Run `make test AGENT=<best_rl_agent>.py` (smoke test vs random); confirm no crashes or illegal moves
- [ ] T025 [US3] Final self-containment check on best RL agent file: run `grep -n "^from \|^import " <agent>.py | grep -v "math\|numpy\|base64\|pickle\|collections\|random\|itertools\|functools\|heapq\|copy\|typing\|os\|sys"`; must return empty output
- [ ] T026 [US3] Submit: `make submit AGENT=<best_rl_agent>.py MESSAGE="RL <algorithm> agent, <score>% vs v38, 50 games"`
- [ ] T027 [US3] After score returns: update `SUBMISSIONS.md` with ref, file, date, description, score (bold if new best)
- [ ] T028 [US3] Update `README.md` Agents table with best RL agent row (algorithm, win rate vs v38, Kaggle score); bold the best overall agent
- [ ] T029 [US3] If RL agent beats agent_v38 locally: update `AGENT` and `RENDER_AGENT` in `Makefile` to point to best RL agent

**Checkpoint**: Kaggle score recorded. README and Makefile reflect best agent. Feature complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, extended training, and infrastructure improvements that benefit all algorithms.

- [X] T030 [P] Add `make train-ppo`, `make train-dqn`, `make train-a2c` targets to `Makefile` for convenient training invocation
- [X] T031 [P] Add `rl/checkpoints/` and `rl/logs/` to `.gitignore` (checkpoint files are large; logs are ephemeral)
- [ ] T032 If any algorithm scores 45–55% on 50 games: extend to 5,000 episodes and re-evaluate; update experiment record with extended results
- [ ] T033 [P] Add `--resume` flag to all training scripts to load from most recent checkpoint in `--checkpoint-dir` and continue training from that episode

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all training
- **US1 Training (Phase 3)**: Depends on Phase 2 — T007/T008/T009 can run in parallel once T004–T006 complete
- **US2 Evaluation (Phase 4)**: Depends on Phase 3 checkpoints — T016 (export) must precede T017–T022
- **US3 Submission (Phase 5)**: Depends on Phase 4 best-agent selection (T023)
- **Polish (Phase 6)**: Can run in parallel with Phase 5

### User Story Dependencies

- **US1 (Train)**: After Phase 2 — no dependency on other stories
- **US2 (Evaluate)**: After US1 checkpoints exist — T016 is the key unlock
- **US3 (Submit)**: After US2 best-agent selection (T023) — linear gate

### Within US1

- T007, T008, T009 (implement algorithms) can run in parallel
- T010, T011, T012 (train) can run in parallel (independent processes)
- T013, T014, T015 (experiment records) can be written in parallel with training

### Within US2

- T017, T018, T019 (export) can run in parallel after T016
- T020, T021, T022 (evaluate) can run in parallel after respective exports

---

## Parallel Example: User Story 1 (Training)

```bash
# After T004–T006 complete, launch all three training runs in parallel:
uv run python rl/ppo.py --episodes 1000 --opponent agent_v38.py &
uv run python rl/dqn.py --episodes 1000 --opponent agent_v38.py &
uv run python rl/a2c.py --episodes 1000 --opponent agent_v38.py &
wait
```

## Parallel Example: User Story 2 (Evaluation)

```bash
# After T016 (export.py), export and evaluate all three in parallel:
uv run python rl/export.py --checkpoint rl/checkpoints/ppo_best.pt --output agent_v39.py
uv run python rl/export.py --checkpoint rl/checkpoints/dqn_best.pt --output agent_v40.py
uv run python rl/export.py --checkpoint rl/checkpoints/a2c_best.pt --output agent_v41.py
uv run python eval.py --agent0 agent_v39.py --agent1 agent_v38.py --games 50 --seed 0 &
uv run python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0 &
uv run python eval.py --agent0 agent_v41.py --agent1 agent_v38.py --games 50 --seed 0 &
wait
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (obs encoder + env wrapper)
3. Complete Phase 3: Train PPO only (T007, T010, T013)
4. Complete Phase 4: Export + evaluate PPO (T016, T017, T020, T023)
5. **STOP and VALIDATE**: Does PPO beat agent_v38 at ≥55%?
6. If yes → proceed to Phase 5 (submit). If no → run DQN/A2C in parallel.

### Incremental Delivery

1. Setup + Foundational → env works
2. PPO training + evaluation → first RL candidate
3. DQN + A2C in parallel → best algorithm selected
4. Submit best agent → Kaggle score recorded

---

## Notes

- [P] tasks = different files or independent processes, no blocking dependencies
- Training runs (T010, T011, T012) are long-running processes — run in tmux/background
- If `make test` fails for an exported agent, check that `_forward()` numpy implementation matches the PyTorch architecture exactly (common issue: missing ReLU or wrong weight transpose)
- Principle VI check (T017–T019, T025) is a hard gate — do not skip before submission
- Commit experiment records to git before running `make submit` (Principle IV)
