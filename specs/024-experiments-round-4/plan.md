# Implementation Plan: Experiments Round 4

**Branch**: `024-experiments-round-4` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-experiments-round-4/spec.md`

## Summary

Three experiments on agent_v63 to close the 0% slawekbiel win rate gap:

| Priority | Experiment | Hypothesis | Toggle |
|----------|------------|------------|--------|
| P1 | Improved opponent model v3 | Realistic simulated opponent → more accurate beam eval → better vs strong opponents | `OPPONENT_MODEL_V3_ENABLED` |
| P2 | Multi-turn plan generation | "Skip" candidates let beam search evaluate waiting-to-build vs immediate dispatch | `MULTI_TURN_PLAN_ENABLED` |
| P3 | Phase-detection dispatch | Adjust garrison/targeting params based on game state to improve late-game conversion | `PHASE_DETECTION_ENABLED` |

All evaluated against v63 baseline, 50 games with --swap. ≥52% win rate = KEEP, <50% = DISCARD.

## Technical Context

**Language/Version**: Python 3.11+ (CPython, same as existing agents)

**Primary Dependencies**: `kaggle-environments>=1.28.0` (game engine), Python stdlib only (`math`, `time`, `random`, `copy`)

**Storage**: N/A — stateless single-file agent, no persistence

**Testing**: `eval.py` (50-game head-to-head with --swap, optional --timing for p50/p95/p99), `make selfplay`, Makefile targets

**Target Platform**: Kaggle Linux sandbox (dev on macOS, ARM/Intel compatible)

**Project Type**: Single-file Python agent (Option A: self-contained, imports only stdlib + kaggle-environments)

**Performance Goals**: < 800ms per-turn (Kaggle budget). Current agents run at p99 < 15ms, >50x headroom.

**Constraints**:
- Single self-contained `.py` file per agent version (Option A)
- No imports outside stdlib + `kaggle_environments`
- Agent receives observation dict, returns list of `[from_planet_id, angle, num_ships]` moves
- Thread-safety not required (sequential per-turn execution)

**Scale/Scope**: Single ~1000-line Python file with tunable constants at top. Each experiment adds one toggle constant + associated logic.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I (RL First)**: ❌ This round uses heuristic experiments exclusively.
**Exception rationale**: All prior development rounds have been heuristic-based. RL training infrastructure has not been established and is out of scope for this round. This is consistent with project convention since the agent-v60 era (beam search, splinter dispatch, etc.). A future round should establish RL training.

**Principle II (Fair Play)**: ✅ No rule violations. Agent operates within Kaggle rules, respects actTimeout.

**Principle III (Manual Submissions)**: ✅ Submission will be manual via `make submit` if any experiment passes.

**Principle IV (Documentation)**: ✅ Each experiment documented with hypothesis, change, self-play result, conclusion in experiment log file.

**Principle V (Local Self-Play)**: ✅ ≥50 games with --swap per experiment (exceeds 20-game minimum).

**Principle VI (Submission Package)**: ✅ Single-file Option A. All imports from stdlib + kaggle-environments.

**Principle VII (95% Confidence)**: ✅ 50-game evals with --swap provide sufficient statistical power. ≥52% / <50% thresholds are clear go/no-go criteria.

## Project Structure

### Documentation (this feature)

```text
specs/024-experiments-round-4/
├── plan.md              # This file
├── research.md          # Phase 0 — technical decisions
├── data-model.md        # Phase 1 — entity definitions
├── quickstart.md        # Phase 1 — test scenarios
├── contracts/           # Phase 1 — interface contracts
└── tasks.md             # Phase 2 — task breakdown
```

### Source Code (repository root)

```text
agent_v63.py              # Frozen baseline (v63, 52% vs v62)
agent_v64.py              # Experimental platform (copy of v63 + round 4 toggles)
eval.py                   # Evaluation harness (with --timing from round 3)
experiments/              # Experiment logs
Makefile                  # Test/eval targets (AGENT updated to v64 if experiments pass)
```

## Complexity Tracking

No constitution violations to justify beyond the documented RL exception above.
