# Implementation Plan: Agent Round 015

**Branch**: `014-agent-round-015` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-agent-round-015/spec.md`

## Summary

Six isolated improvement candidates against agent_v47 (current best: 68% vs v42, 72% vs v38). Each candidate targets a specific correctness gap or strategic weakness identified in the post-v47 analysis. Candidates are implemented as standalone agent files (v48–v53), evaluated at 50 games vs agent_v47, and passing candidates (≥56% win rate) combined into a new best agent.

## Technical Context

**Language/Version**: Python 3.9+ (Kaggle sandbox); local dev uses Python 3.9.6

**Primary Dependencies**: `kaggle-environments` (orbit_wars env), `math` (stdlib only for agent logic)

**Storage**: Module-level globals for Candidate 6 (persistent campaign dict); all other candidates are stateless

**Testing**: `uv run python eval.py --agent0 agent_vNN.py --agent1 agent_v47.py --games 50 --jobs 4`

**Target Platform**: Kaggle Orbit Wars sandbox (Linux); local macOS for development

**Project Type**: AI competition agent — self-contained Python function submitted as single file or tar.gz

**Performance Goals**: Agent decision must complete in ≤1 second per turn (Kaggle `actTimeout`)

**Constraints**: Submission must be Option A (single self-contained file) or Option B (tar.gz with helper.py included). All local imports must be inlined or bundled.

**Scale/Scope**: 500 turns per game; 20–40 planets; 6 candidate files + 1 combined; 6 × 50 + 50 + 50 = 400 evaluation games total

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I — RL First | ⚠️ Known deviation | RL experiments (round 011) failed to beat heuristic baseline. Heuristic iteration is accepted standing practice documented since round 009. |
| II — Fair Play | ✅ Pass | All candidates operate within game rules; no engine exploitation. |
| III — Manual Submissions | ✅ Pass | No automated submission pipeline added. Submission remains manual. |
| IV — Documentation | ✅ Pass | Each candidate requires an `experiments/015-*.md` entry before submission. |
| V — Self-Play Evaluation | ✅ Pass | 50-game eval vs agent_v47 per candidate; combined evaluated vs v47 and v38. |
| VI — Submission Package | ✅ Pass | New agents follow Option A (self-contained) or Option B (with helper.py). Pre-submission import check required. |
| VII — 95% Confidence | ✅ Pass | 50-game sample gives ±7% at 95% confidence; 56% threshold is statistically distinguishable from 50%. |

**Post-design re-check**: Research confirmed no new principles are violated. Candidate 5 reframing (friendly fleet sufficiency vs. committed ships deduction) eliminates a double-counting error that would have introduced incorrect surplus calculations.

## Project Structure

### Documentation (this feature)

```text
specs/014-agent-round-015/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md             ← Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
agent_v47.py             ← base agent (unmodified)
agent_v48.py             ← C1: ROI mismatch fix
agent_v49.py             ← C2: Endgame ROI normalization
agent_v50.py             ← C3: Garrison defense buffer
agent_v51.py             ← C4: Sender pre-screening
agent_v52.py             ← C5: Friendly fleet sufficiency check
agent_v53.py             ← C6: Persistent campaign target
agent_v5X.py             ← Combined (passing candidates only; number TBD after evals)
helper.py                ← Shared mechanics library (unmodified unless needed)
experiments/
├── 015-candidate-1-roi-mismatch.md
├── 015-candidate-2-endgame-roi.md
├── 015-candidate-3-garrison-buffer.md
├── 015-candidate-4-sender-prescreen.md
├── 015-candidate-5-fleet-sufficiency.md
├── 015-candidate-6-campaign-target.md
└── 015-combined-agent.md
```

**Structure Decision**: Flat agent files at project root (existing convention). Each candidate is a complete standalone copy of v47 with exactly one change. No new modules introduced for candidates 1–5. Candidate 6 adds a module-level `_campaign` global.

## Complexity Tracking

No constitution violations requiring justification.
