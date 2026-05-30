# Implementation Plan: Mid-Game Reward Signals and Reward-Guided Agent Experimentation

**Branch**: `008-mid-game-rewards` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-mid-game-rewards/spec.md`

## Summary

Build a standalone `reward_signal.py` module that computes per-turn, per-player reward scalars (normalized to [-1, 1]) from the `orbit_wars` game state observation. Extend `eval.py` and `eval4.py` with a `--reward-log` flag to collect JSON Lines datasets. Use those datasets and a replay-analysis script (`reward_analysis.py`) to validate reward shaping, then create at least one reward-guided agent variant (`agent_v31.py`) that blends reward estimates into ROI-based target scoring, evaluated against `agent_v30` at the ≥55% threshold.

## Technical Context

**Language/Version**: Python 3.14 (project venv at `.venv/`)

**Primary Dependencies**: `kaggle_environments` (orbit_wars engine, Planet/Fleet namedtuples), `eval.py` / `eval4.py` (evaluation harnesses — extended, not replaced)

**Storage**: `.jsonl` files for reward logs (one object per game/turn/player), `experiments/` directory for experiment records (established pattern)

**Testing**: `eval.py` / `eval4.py` for win-rate evaluation; manual inspection of reward log output; `reward_analysis.py` summary script for reward signal validation

**Target Platform**: Local macOS/Linux (same as existing project)

**Project Type**: Research bot / game agent (flat repo root layout, no package structure)

**Performance Goals**: Reward computation overhead <10% of eval wall-clock time; `reward_analysis.py` completes in <5 seconds on a 50-game log

**Constraints**: No external ML libraries introduced; pure Python math; existing agent files untouched

**Scale/Scope**: 2-player primary (50-game evaluation batches), 4-player secondary; reward log ~1–5 MB per 50-game run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | ✅ Pass | This feature builds the reward-signal infrastructure required for RL. Reward-guided agent blending is reward shaping on a heuristic baseline — a valid RL-first step. Full learned policy is the next stage. |
| II. Fair Play | ✅ Pass | No engine exploits; reward module is read-only over observable state. |
| III. Manual Submissions | ✅ Pass | No automated submission logic introduced. Experiment records must be written before any submission. |
| IV. Experiment Documentation | ✅ Pass | FR-013 requires experiment records in `experiments/` per run. Reward-weight configurations and win rates must be logged per the constitution format. |
| V. Local Self-Play | ✅ Pass | SC-006 requires ≥55% win rate over 50 games (above the 20-game minimum). Evaluation runs against `agent_v30` before any submission consideration. |

## Project Structure

### Documentation (this feature)

```text
specs/008-mid-game-rewards/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli.md           # CLI contracts for new scripts
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
reward_signal.py         # Standalone reward module (FR-001–009)
reward_analysis.py       # Replay analysis CLI (FR-012)
agent_v31.py             # First reward-guided agent variant (FR-010–011)
experiments/
└── 2026-05-30-reward-signal-baseline.md   # Reward shaping validation record
```

**Structure Decision**: Flat root layout, matching the established project convention. All new files live at the repo root alongside `eval.py`, `agent_v30.py`, etc. No package restructuring.

## Complexity Tracking

No constitution violations — no complexity justification required.
