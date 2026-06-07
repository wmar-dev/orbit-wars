# Implementation Plan: Experiments Round 5

**Branch**: `025-experiments-round-5` | **Date**: 2026-06-06 | **Spec**: specs/025-experiments-round-5/spec.md

**Input**: Feature specification from `/specs/025-experiments-round-5/spec.md`

## Summary

Run three independent experiments on the agent_v64 baseline to close the slawekbiel gap and improve 4-player FFA performance:

1. **P1 — Multi-source coordinated attack**: Generate beam search candidates where 2+ sources target the same enemy planet simultaneously, enabling tactical coordination that the current single-source swap cannot produce.
2. **P2 — Fleet-size-optimized dispatch**: Oversend for distant targets where fleet speed scaling (1→6× based on log fleet size) reduces travel time enough that the extra ships pay for themselves in reduced garrison production during transit.
3. **P3 — 4-player state adaptation**: Adjust garrison floor factor, splinter window, and dispatch aggressiveness based on number of surviving opponents (higher floors for 3 opponents, lower for 1).

All three are independently togglable, evaluated against v64 via 50-game self-play with --swap. Passing experiments are combined into a single config and re-evaluated.

## Technical Context

**Language/Version**: Python 3.10+ (Kaggle sandbox runs 3.8+)

**Primary Dependencies**: math (stdlib), kaggle_environments, time, copy, random

**Storage**: N/A — stateless agent, no persistence between turns

**Testing**: `make selfplay` (runs head-to-head eval with --swap flag); manual 50-game evals via `python -c "..."` using kaggle_environments

**Target Platform**: Kaggle sandbox (Linux, x86_64, Python 3.8+, 800ms/turn budget)

**Project Type**: Competitive game agent (single-file heuristic + beam search)

**Performance Goals**: p99 per-turn < 100ms (currently p99 < 15ms for all variants; 800ms budget leaves enormous headroom)

**Constraints**: Single-file submission option (all code inlined), <800ms/turn, no external dependencies beyond Python stdlib + kaggle_environments

**Scale/Scope**: Single agent file (~1138 LOC currently), 3 new feature toggles, 50-game evals per experiment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (RL First)**: PASS — Heuristic logic is explicitly "acceptable as a baseline". No RL agent exists yet; these experiments optimize the baseline that will later seed RL training.
- **Principle IV (Experiment Documentation)**: PASS — All experiments will be logged in `experiments/2026-06-06-experiments-round5.md` with hypothesis, change, self-play result, and conclusion.
- **Principle V (Local Self-Play)**: PASS — Mandatory 50-game eval (≥20 minimum) with --swap for each experiment.
- **Principle VI (Submission Completeness)**: N/A — No Kaggle submission this round. Agent_v65 remains a local experimental platform.
- **Principle VII (95% Confidence)**: PASS — No critical decisions (submissions, architecture changes) made during research. Decision to keep/discard each experiment is based on ≥50 game evals, meeting the confidence bar.

**Result: All gates pass. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/025-experiments-round-5/
├── plan.md              # This file
├── research.md          # Phase 0: fleet speed, beam search internals, opponent model analysis
├── data-model.md        # Phase 1: entity definitions for multi-source, fleet-size opt, FFA adapt
├── quickstart.md        # Phase 1: implementation guide for all 3 experiments
├── contracts/           # Phase 1: interface docs (toggles, dispatch internals)
└── tasks.md             # Phase 2: task breakdown (created by /speckit-tasks)
```

### Source Code (repository root)

```text
agent_v64.py             # Frozen baseline (54% vs v63)
agent_v65.py             # Experimental platform (copy of v64, all 3 experiments added)
experiments/
└── 2026-06-06-experiments-round5.md   # Experiment log
Makefile                 # Updated AGENT to v65
```

### Structure Decision

Single-file agent — no multi-file structure needed. Agent_v65.py inherits all v64 logic and adds three independently togglable feature flags.

## Complexity Tracking

> All gates pass — no violations to justify.
