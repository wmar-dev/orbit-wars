# Implementation Plan: RL Full Observation

**Branch**: `027-rl-full-obs` | **Date**: 2026-06-07 | **Spec**: specs/027-rl-full-obs/spec.md

**Input**: Feature specification from `specs/027-rl-full-obs/spec.md`

## Summary

Overhaul the RL observation encoder to see all 40 planets and 50 fleets, expand the action space to dispatch up to 5 fleets per turn (matching heuristic capability), and train via PPO against agent_v64 to achieve ≥5% win rate at 5000 episodes.

## Technical Context

**Language/Version**: Python 3.10+ (Kaggle sandbox 3.8+)

**Primary Dependencies**: mlx (GPU), gymnasium (env interface), numpy, torch (checkpoint export), kaggle-environments (game engine)

**Storage**: Checkpoints on disk at `rl/checkpoints/` (npz/pt files, ~900KB each after obs size increase)

**Testing**: `uv run python rl/ppo.py --episodes N --opponent agent_v64` for training; `make eval-rl` for evaluation vs v64

**Target Platform**: Apple Silicon (M-series) for training; Kaggle Linux sandbox for submission inference

**Project Type**: RL training pipeline with PPO + MLP policy + Gymnasium env

**Performance Goals**: Training: 1000 episodes in <10 minutes on M-series. Inference: p99 < 100ms per turn

**Constraints**: Apple Silicon unified memory (16-32GB shared CPU/GPU); no CUDA. Kaggle sandbox has no GPU. OBS_SIZE increase from 319 to ~644 adds ~30% more params but inference stays well under budget.

**Scale/Scope**: Single MLP policy (644 inputs → 2×256 hidden → 5×(40+40+4) action heads + value head). Training up to 20000 episodes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (RL First)**: PASS — RL training is the primary path. Observations and actions fixed to match the real game state.
- **Principle II (Fair Play)**: PASS — Training within kaggle_environments, no rule violations.
- **Principle III (Manual Submissions)**: N/A — No Kaggle submission planned in this feature.
- **Principle IV (Experiment Documentation)**: PASS — Each training run documented in experiment log.
- **Principle V (Local Self-Play)**: PASS — Training and evaluation run entirely locally.
- **Principle VI (Submission Completeness)**: PASS — Export pipeline produces self-contained agent files. Numpy forward pass updated for new OBS_SIZE.
- **Principle VII (95% Confidence)**: PASS — Building on documented failure of previous round (026-rl-training). New approach directly addresses identified causes (blind observation, single-fleet action).

**Result: All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/027-rl-full-obs/
├── plan.md              # This file
├── research.md          # Phase 0: RL pipeline audit, obs/action decisions
├── data-model.md        # Phase 1: FullObservation, MultiFleetAction, PolicyNet
├── quickstart.md        # Phase 1: training workflow commands
├── contracts/           # Phase 1: training/eval/export interface docs
└── tasks.md             # Phase 2: task breakdown (created by /speckit-tasks)
```

### Source Code (repository root)

```text
rl/
├── __init__.py
├── obs.py               # Observation encoder — rewritten (40 planets, 50 fleets, planet_type flag, comet predictions)
├── env.py               # Gymnasium wrapper — updated for multi-fleet action
├── ppo.py               # PPO training — updated action heads, input size, multi-fleet decoding
├── export.py            # Export to single-file agent — updated numpy forward pass
└── checkpoints/         # Trained weights (created during training)
    ├── ppo_ep*.npz
    └── ppo_best.npz
```

### Structure Decision

Single training pipeline under `rl/`. All code changes are within existing files — no new source files needed. The export produces a standalone agent file at the repo root.

## Complexity Tracking

> No violations to justify. All gates pass.

