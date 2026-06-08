# Tasks: Curriculum Training with Terminal Reward

## Phase 1: Reward & Pipeline Changes

### T001 — Create terminal-only reward module

- [ ] T001 Create `rl/reward.py` with terminal-only reward function

### T002 — Update env.py with terminal reward + greedy fallback

- [ ] T002 [US1] Update `rl/env.py` to use terminal-only reward from `rl/reward.py`
- [ ] T003 [P] [US3] Add greedy fallback to `decode_action` in `rl/env.py` (nearest-enemy-sniper when all 5 fleet slots are invalid)

### T003 — Update ppo.py with curriculum + eval harness

- [ ] T004 [US1] Add curriculum stage tracking in `rl/ppo.py` (opponent, threshold, min_episodes per stage)
- [ ] T005 [P] [US2] Add win-rate eval harness (50 games every N episodes)
- [ ] T006 [US1] Add automatic curriculum advancement (switch opponent when threshold met)
- [ ] T007 [US1] Wire terminal-only reward through training loop (remove per-turn blended reward accumulation)

## Phase 2: Smoke Test

- [ ] T008 Run smoke test: 200 episodes vs random with terminal reward
- [ ] T009 Verify: idle-turn rate <5%, win rate vs random >50% by ep 200

## Phase 3: Full Curriculum Training

- [ ] T010 [US1] Run full curriculum: random → v38 → v64 (500 + 1000 + 5000 episodes)
- [ ] T011 [US2] Verify eval logs show win rate at each checkpoint

## Phase 4: Export & Evaluate

- [ ] T012 Export best checkpoint via `rl/export.py`
- [ ] T013 Evaluate exported agent: 100 games vs random, 100 vs v64

## Phase 5: Document

- [ ] T014 Write experiment results to `experiments/2026-06-07-rl-round8-results.md`

## Dependencies

```
T001 ──> T002 ──> T004 ──> T005 ──> T006 ──> T007 ──> T008 ──> T010 ──> T012 ──> T013 ──> T014
               \──> T003 ──/                            /
```

## Parallel Execution

- T001 (reward.py) and T003 (fallback in decode_action) are independent — can run in parallel
- T005 (eval harness) is independent of T004 (curriculum tracking) — can run in parallel
