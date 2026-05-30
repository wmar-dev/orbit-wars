# Implementation Plan: Beat the Getting Started Agent

**Branch**: `001-beat-starter-agent` | **Date**: 2026-05-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-beat-starter-agent/spec.md`

## Summary

Build a new Orbit Wars agent using **production-weighted targeting** — scoring every non-owned
planet by `production / distance` and attacking the highest-value target rather than the
nearest one. Alongside the agent, add a local head-to-head evaluation harness that prints
per-game results and an aggregate win rate. The agent must win ≥70% of 10 seeded games
against the existing nearest-planet-sniper (`main.py`) while staying within the 1-second
turn budget. Speed-optimized where possible; all code kept human-readable.

## Technical Context

**Language/Version**: Python 3.14 (project constraint in pyproject.toml)

**Primary Dependencies**: `kaggle-environments ≥1.28.0` (already installed via Makefile)

**Storage**: N/A — no persistence; eval results printed to stdout only

**Testing**: Manual — `uv run python eval.py` for head-to-head; `make test` for smoke test

**Target Platform**: Local macOS/Linux dev machine (same env as existing Makefile workflows)

**Project Type**: CLI / script — single-file agent + single-file eval harness

**Performance Goals**: Each turn decision in <1 second; full 10-game eval run in <60 seconds

**Constraints**: Pure Python, no external models or network calls, no pre-computed tables;
agent file must be self-contained (single file, compatible with Kaggle submission format)

**Scale/Scope**: 2-player games only; 10 eval games; single strategy implementation

**User Directives**: Optimize for speed where possible; keep code human-readable

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
| --- | --- | --- |
| I. RL First | ✅ Pass | Rule-based baseline is explicitly permitted as an "opponent seed" — precursor to RL training |
| II. Fair Play | ✅ Pass | Respects `actTimeout` (1s); no engine bug exploitation |
| III. Manual Submissions Only | ✅ Pass | No automation; `make submit` is always manual |
| IV. Experiment Documentation | ✅ Pass (conditional) | Experiment log MUST be created at `experiments/2026-05-29-production-weighted-baseline.md` before any Kaggle submission |
| V. Local Self-Play Eval | ✅ Pass | Spec mandates local eval harness with 10 seeded games before submission |

**Gate result**: PASS. No violations. Experiment log creation is a required task.

## Project Structure

### Documentation (this feature)

```text
specs/001-beat-starter-agent/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   └── agent-interface.md
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
orbit-wars/
├── main.py              # existing getting-started agent (baseline — do not modify)
├── agent_v2.py          # new production-weighted agent (this feature)
├── eval.py              # head-to-head evaluation harness (this feature)
├── experiments/
│   └── 2026-05-29-production-weighted-baseline.md   # required experiment log
└── Makefile             # extend with `make eval` and `make selfplay` targets
```

**Structure Decision**: Flat root layout matching existing project convention. No `src/`
nesting — Kaggle submission requires `main.py` at root, so all agent files live at root.
`eval.py` is a standalone script, not a test suite.

## Complexity Tracking

No constitution violations requiring justification.
