# Implementation Plan: Game Replay Learning

**Branch**: `main` | **Date**: 2026-06-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-game-replay-learning/spec.md`

## Summary

Record complete black-box game state (planet ownership, ship counts, fleet moves) for every turn of games played against opponent agents, save replays to disk, and provide a Claude skill (`/analyze-replay`) that loads one or more replays and uses the Claude API to identify behavioral patterns, surface the decisive divergence turn, and propose concrete candidate improvements to the agent.

The learning loop is purely observational: only what appears in the game output is captured. The Claude skill drives the "improvement" step by analyzing the recorded data and writing a hypothesis to the experiments log.

## Technical Context

**Language/Version**: Python 3.14 (project venv)

**Primary Dependencies**: `kaggle_environments` (already installed), `json` stdlib (replay storage), `claude-sonnet-4-6` via Anthropic SDK (skill analysis)

**Storage**: JSON files on disk — one file per replay in `replays/` directory at project root

**Testing**: Manual smoke-test via CLI (`python record_replays.py`) + assertion on file structure

**Target Platform**: Local developer machine (macOS, same environment as existing eval scripts)

**Project Type**: CLI scripts + Claude skill (markdown-based skill invoked via Claude Code)

**Performance Goals**: 20-game batch recorded and summary generated in under 30 seconds

**Constraints**: Black-box observation only — no opponent internals accessed; replay files must be human-readable (JSON)

**Scale/Scope**: 20–50 games per analysis session; replays/`~1–5 MB each

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --- | --- | --- |
| I. RL First | ✅ Pass | This feature is observational tooling that feeds improvement hypotheses back into the RL loop — it does not replace RL training |
| II. Fair Play | ✅ Pass | Only game output (observation dict) is read; opponent internals are never accessed |
| III. Manual Submissions | ✅ Pass | No submission pipeline; this is analysis tooling only |
| IV. Experiment Documentation | ✅ Pass | The skill writes a hypothesis entry to `experiments/` as its output |
| V. Local Self-Play | ✅ Pass | Replay recording uses the local `kaggle_environments` runner |
| VI. Submission Package | ✅ Pass | Replay tooling is dev-only; not submitted to Kaggle |
| VII. 95% Confidence Gate | ✅ Pass | Not a critical submission decision; analysis tooling is low-risk |

No violations. Proceeding.

## Project Structure

### Documentation (this feature)

```text
specs/020-game-replay-learning/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── contracts/
│   └── replay-schema.md ← replay JSON contract
└── tasks.md             ← Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
replays/                          ← saved game replays (JSON, gitignored)

record_replays.py                 ← CLI: run N games vs an opponent, save replays
analyze_replays.py                ← CLI: load replays, print summary statistics

.claude/skills/
└── analyze-replay/
    └── SKILL.md                  ← Claude skill: analyze replay(s) and propose improvement
```

**Structure Decision**: Flat scripts at repo root, consistent with existing `eval_opponents.py` and `record_replays.py` pattern. Skills live under `.claude/skills/` following the established speckit convention.

## Complexity Tracking

No constitution violations — section not required.
