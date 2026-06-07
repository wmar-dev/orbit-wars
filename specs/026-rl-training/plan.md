# Implementation Plan: RL Training

**Branch**: `026-rl-training` | **Date**: 2026-06-06 | **Spec**: specs/026-rl-training/spec.md

**Input**: Feature specification from `/specs/026-rl-training/spec.md`

## Summary

Train a PPO policy network (MLX/Apple Silicon) to play Orbit Wars, progressing from random opponents → heuristic agent_v64 → self-play. Verify the pipeline end-to-end, fix any bugs in the existing rl/ infrastructure, then train iteratively until the policy beats v64 at ≥40% win rate.

## Technical Context

**Language/Version**: Python 3.10+ (Kaggle sandbox 3.8+)

**Primary Dependencies**: mlx (GPU), gymnasium (env interface), numpy, torch (checkpoint export), kaggle-environments (game engine)

**Storage**: Checkpoints on disk at `rl/checkpoints/` (npz/pt files, ~500KB each)

**Testing**: `uv run python rl/ppo.py --episodes N --opponent random|agent_v64` for training; `python -c "..."` or `eval.py` for evaluation vs heuristic agents

**Target Platform**: Apple Silicon (Mac, M-series) for training; Kaggle Linux sandbox for submission inference

**Project Type**: RL training pipeline with PPO + MLP policy + Gymnasium env

**Performance Goals**: Training: 1000 episodes in <10 minutes on M-series. Inference: p99 < 100ms per turn (800ms budget)

**Constraints**: Apple Silicon unified memory (16-32GB shared CPU/GPU); no CUDA. Kaggle sandbox has no GPU, so inference must be CPU-only (use numpy, not mlx, for submission agent).

**Scale/Scope**: Single MLP policy (319 inputs → 2×256 hidden → 3 action heads + value head). Training up to 20000 episodes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (RL First)**: PASS — Direct implementation of the RL-first principle. Heuristic agents (v64) serve as the opponent seed.
- **Principle II (Fair Play)**: PASS — Training within kaggle_environments, no rule violations.
- **Principle III (Manual Submissions)**: N/A — No Kaggle submission planned in this feature.
- **Principle IV (Experiment Documentation)**: PASS — Each training run documented in experiment log.
- **Principle V (Local Self-Play)**: PASS — Training and evaluation run entirely locally.
- **Principle VI (Submission Completeness)**: N/A — Not submitting during this feature.
- **Principle VII (95% Confidence)**: PASS — Research/experimentation phase; no critical decisions yet.

**Result: All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/026-rl-training/
├── plan.md              # This file
├── research.md          # Phase 0: RL pipeline audit, hyperparameter decisions
├── data-model.md        # Phase 1: PolicyNet, obs encoding, action decoding, reward
├── quickstart.md        # Phase 1: training workflow commands
├── contracts/           # Phase 1: training/eval/export interface docs
└── tasks.md             # Phase 2: task breakdown (created by /speckit-tasks)
```

### Source Code (repository root)

```text
rl/
├── __init__.py
├── obs.py               # Observation encoder — debugged/verified
├── env.py               # Gymnasium wrapper — debugged/verified
├── ppo.py               # PPO training — debugged/verified (incl. eval hook)
├── dqn.py               # DQN (secondary, may remain experimental)
├── a2c.py               # A2C (secondary, may remain experimental)
├── export.py            # Export to single-file agent — debugged/verified
└── checkpoints/         # Trained weights (created during training)
    ├── ppo_ep*.npz
    ├── ppo_ep*.pt
    └── ppo_best.npz
```

### Structure Decision

Single training pipeline under `rl/`. All training code stays in this directory. The export produces a standalone agent file at the repo root for competition submission.

## Complexity Tracking

> All gates pass — no violations to justify.
