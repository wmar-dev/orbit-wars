# Implementation Plan: Curriculum Training with Terminal Reward

## Technical Context

- **Branch**: (`028-curriculum-training`)
- **Existing codebase**: RL pipeline from `027-rl-full-obs` — obs.py (560-dim, 40 planets, 8+42 fleet), env.py (multi-fleet action), ppo.py (PPO training), export.py (numpy export)
- **Problem**: PPO doesn't converge because policy never experiences winning states (0% vs v64) and reward is a noisy blended signal
- **Available opponents**: random, agent_v38.py, agent_v64.py

## Design Decisions (from research)

1. **Terminal reward**: Replace blended per-turn reward with sparse terminal signal (+1 win, -1 loss, 0 draw). Removes noisy gradient.
2. **Curriculum stages**: Start vs random (threshold 80%, min 500 ep), graduate to v38 (threshold 60%, min 1000 ep), then v64 (no threshold, 5000 ep max).
3. **Greedy fallback**: When all 5 fleet slots produce invalid actions, fall back to nearest-enemy-sniper. Eliminates 46% idle turns.
4. **Win-rate evaluation**: Automatic 50-game eval every 200 episodes; advancement decision based on rolling win rate.
5. **PPO hyperparameters**: Keep LR=3e-4, hidden=256, entropy=0.01 from round 7 (unchanged).

## Constitution Check

Relevant principles:
- **Principle I (RL First)**: ✓ RL is primary path
- **Principle VI (Kaggle-compatible export)**: ✓ Export unchanged; changes are training-only

Gates: PASS

## Phases

### Phase 0: Research (complete — see design decisions above)

### Phase 1: Design

- **reward.py**: New reward module with terminal-only function
- **ppo.py**: Add curriculum logic, eval harness, greedy fallback integration
- **env.py**: Update step() to use terminal-only reward; add fallback integration
- **obs.py**: No changes (reuse round 7 encoder)

### Phase 2: Implementation Tasks

1. **reward.py**: Write terminal-only reward function
2. **env.py**: Wire terminal reward; add fallback to decode_action
3. **ppo.py**: Add curriculum stage tracking, eval harness, automated advancement
4. **Smoke test**: 200 episodes vs random with terminal reward
5. **Curriculum training**: Full curriculum run (random → v38 → v64)
6. **Export**: Export best checkpoint
7. **Evaluate**: 100-game eval vs v64
8. **Document**: Results to experiments/

## Generated Artifacts

- `specs/028-curriculum-training/plan.md` — this file
- `rl/reward.py` — terminal reward module
- Updates to `rl/env.py`, `rl/ppo.py`
