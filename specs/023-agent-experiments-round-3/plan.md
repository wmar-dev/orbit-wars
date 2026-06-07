# Implementation Plan: Agent Experiments Round 3

**Branch**: `023-agent-experiments-round-3` | **Date**: 2026-06-06 | **Spec**: `specs/023-agent-experiments-round-3/spec.md`

**Input**: Feature specification from `specs/023-agent-experiments-round-3/spec.md`

## Summary

Three focused experiments on `agent_v62.py` (current best, 70% vs v61, 72% vs v60):
1. **P1** — Evaluate the already-implemented defense interceptor (`DEFENSE_INTERCEPT_ENABLED`) for win rate impact
2. **P2** — Increase beam search depth (15/20) and/or beam width (5) to close the 0% slawekbiel gap
3. **P3** — Re-implement production-weighted beam eval with correct transit-weight handling (fixes v61 US3 regression)

All experiments are additive toggles in `agent_v63.py` (copy of v62 + new toggles). Baseline control is frozen `agent_v62.py`.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `kaggle-environments>=1.28.0`; stdlib only (`math`, `time`, `random`, `copy`)

**Storage**: N/A (agent is stateless per turn; results logged in `experiments/`)

**Testing**: `eval.py h2h` harness (50 games, `--swap`)

**Target Platform**: Kaggle Linux sandbox (2 vCPU, 800ms per-turn `actTimeout`)

**Project Type**: Single-file game competition agent

**Performance Goals**: p95 per-turn < 780ms, p99 < 800ms on local hardware (Kaggle-comparable)

**Constraints**: 800ms/turn, 100x100 board, 4 players, Python 3.11+ stdlib only in sandbox

**Scale/Scope**: 1 agent file, 3 toggleable experiments, 50-game evals per direction

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. RL First** | ⚠️ Partial divergence | This round is purely heuristic (rule-based), not RL. This follows the established pattern from all prior rounds (v2–v62). RL is deferred to a future dedicated round. Acceptable given current infra maturity. |
| **II. Fair Play** | ✅ Pass | All changes operate within game rules. No engine exploits. |
| **III. Manual Submissions** | ✅ Pass | Plan requires manual `make submit`. No auto-submit. |
| **IV. Experiment Documentation** | ✅ Pass | Experiment log (`experiments/2026-06-06-experiments-round3.md`) required. |
| **V. Local Self-Play** | ✅ Pass | All evals are 50-game self-play with `--swap`. Exceeds 20-game minimum. |
| **VI. Submission Package** | ✅ Pass | Single-file agent (`agent_v63.py`). All helpers inlined. |
| **VII. 95% Confidence** | ✅ Pass | 50-game evals × 3 directions + combined test provide statistical confidence. |

**Gate decision**: ✅ PASS — proceed to Phase 0. Divergence from Principle I is documented and consistent with project precedent.

## Project Structure

### Documentation (this feature)

```text
specs/023-agent-experiments-round-3/
├── plan.md              # This file
├── research.md          # Phase 0 — technical feasibility
├── data-model.md        # Phase 1 — toggle constants and entities
├── quickstart.md        # Phase 1 — how to run experiments
├── contracts/           # Phase 1 — experiment toggle interface
└── tasks.md             # Phase 2 (created by /speckit-tasks)
```

### Source Code (repository root)

```text
agent_v62.py             # Frozen baseline (current best)
agent_v63.py             # Copy of v62 + new experiment toggles
main.py                  # Updated to agent_v63.py after passing experiments
experiments/
└── 2026-06-06-experiments-round3.md   # Experiment log
specs/023-agent-experiments-round-3/   # This feature (documentation)
```

**Structure Decision**: Single-file agent. Experiments are toggle constants at file top. Each experiment independently evaluable by toggling flags. `agent_v63.py` is the experimental platform; `agent_v62.py` is the frozen baseline.

## Complexity Tracking

No constitution violations requiring justification.
