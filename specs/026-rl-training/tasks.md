---
description: "Task list for RL training pipeline"
---

# Tasks: RL Training Pipeline

**Input**: Design documents from `/specs/026-rl-training/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Verify Pipeline (Shared Infrastructure)

**Purpose**: Ensure the existing RL infrastructure (ppo.py, env.py, obs.py, export.py) works end-to-end with no crashes, produces checkpoints, and supports resume.

- [ ] T001 Run 10-episode PPO training vs random, confirm checkpoint + resume
- [ ] T002 Export checkpoint to single-file agent via export.py with --verify
- [ ] T003 Fix decode_action docstring in rl/obs.py:199 (stale no-op reference)
- [ ] T004 Save .pt checkpoints during training (not just at end) in rl/ppo.py
- [ ] T005 Add `--log-file` and `--log-frequency` arguments for configurable logging

---

## Phase 2: Foundational (Strong Opponent Training)

**Purpose**: Switch opponent progression to target agent_v64 and train a policy that demonstrably improves. Measure reward trend over training.

- [ ] T006 [P] Update `get_opponent` in rl/ppo.py to use agent_v64 as strong opponent (replace agent_v38)
- [ ] T007 Train 1000 episodes vs agent_v64 to confirm reward trend is upward
- [ ] T008 Verify exported policy plays valid legal moves (no crashes, no 0-command turns unless forced)

---

## Phase 3: User Story 1 — Evaluate Trained Policy (Priority: P1)

**Goal**: Rigorous evaluation harness: load checkpoint → run h2h vs v64 → report win rate + timing.

**Independent Test**: `make eval AGENT1=/tmp/rl_agent.py AGENT2=agent_v64.py GAMES=20` reports win rate and avg reward.

- [ ] T009 [US1] Create evaluation script or Makefile target `eval-rl` that exports checkpoint to agent file then runs eval.py h2h against v64
- [ ] T010 [US1] Verify timing: p99 per-turn < 100ms for exported numpy forward pass

---

## Phase 4: User Story 2 — Train vs agent_v64 with Self-Play (Priority: P2)

**Goal**: Train until policy ≥20% vs v64 at 5000 episodes, then ≥40% at 20000 episodes with self-play escalation.

**Independent Test**: After 5000 episodes, `make eval-rl` shows ≥20% win rate vs v64.

- [ ] T011 [US2] Train 5000 episodes vs agent_v64 + self-play; evaluate every 500 episodes
- [ ] T012 [US2] Continue training to 20000 episodes; verify ≥40% win rate vs v64
- [ ] T013 [US2] Apply constitution experiment documentation (log training + eval results)

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T014 Build best checkpoint as Makefile default AGENT (update AGENTS.md, Makefile)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Verify Pipeline)**: No dependencies — can start immediately. Must complete before US1 (evaluation).
- **Phase 2 (Foundational)**: Needs Phase 1 completion (pipeline must be stable).
- **Phase 3 (US1 — Eval)**: Needs Phase 1 completion (export pipeline).
- **Phase 4 (US2 — Train vs v64)**: Needs Phase 2 (agent_v64 opponent) and Phase 3 (eval harness).
- **Phase 5 (Polish)**: Only after meaningful trained policy exists.

### User Story Dependencies

- **US1 (Eval)**: Independent after Phase 1
- **US2 (Training)**: Needs eval harness to measure progress

### Within Each Phase

- T006–T007 are sequential (update opponent first, then train)
- T009–T010 are sequential (create eval target first, then measure timing)

### Parallel Opportunities

- T001–T003 can run in parallel within Phase 1
- T006 is independent from US1 (T009–T010) — can run in parallel

---

## Implementation Strategy

### MVP First (Phase 1 + US1)

1. Run 10 episodes to verify pipeline (T001)
2. Fix bugs found (T003, T004)
3. Build eval harness (T009)
4. Measure timing (T010)

### Incremental Delivery

1. Phase 1 → pipeline verified, bugs fixed
2. Phase 2 + US1 → strong opponent training + eval capability (train 1000 episodes)
3. Phase 2 + US2 → long training runs to 5000+ episodes, self-play escalation (train 5000→20000)
4. Phase 5 → promote best RL policy to default agent
