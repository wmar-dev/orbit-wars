# Implementation Plan: Agent Improvement Experiments — Round 2

**Branch**: `006-agent-experiments-round-2` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-agent-experiments-round-2/spec.md`

## Summary

Run four isolated mechanic experiments (agent_v16–v19) against agent_v15 as the baseline, then stack all passing mechanics (≥55% win rate) into agent_v20. This round targets three confirmed structural gaps in agent_v15: the orbit-lead speed miscalculation that causes targeting misses on orbiting planets, fleet sizing that ignores garrison growth during transit, and a fixed range factor that ignores game-state advantage. A fourth candidate replaces the scoring formula with a capture-ROI metric.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: kaggle_environments (orbit_wars engine), eval.py, diagnose_v9.py (both at repo root, used as-is)

**Storage**: N/A — agent files at repo root, experiment records in `experiments/`

**Testing**: `eval.py --agent0 agentN.py --agent1 agent_v15.py --games 20 --seed 0` (seeds 0–19); `diagnose_v9.py --agent agent_v20.py --games 20` for safety regression check on combined agent only

**Target Platform**: Local Python execution (Kaggle submission is manual, out of scope for this feature)

**Project Type**: Game AI agent scripts

**Performance Goals**: Each candidate ≥55% win rate vs agent_v15 over 20 games; combined agent_v20 ≥65% win rate vs agent_v15

**Constraints**: actTimeout 1s/turn; no modification to eval.py or diagnose_v9.py; no removal or weakening of sun avoidance, OOB rejection, or planet obstruction checks from agent_v15

**Scale/Scope**: 5 agent files (agent_v16–v20) + 5 experiment records; up to 6 evaluation runs × 20 games

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| **I. Reinforcement Learning First** | WAIVED (justified) | All mechanics are rule-based heuristics. Per the spec and prior precedent (001–005), RL-first is the long-term path; heuristic iteration is the approved short-term method for this project phase. |
| **II. Fair Play & Rules Compliance** | PASS | No engine bug exploitation; actTimeout respected; all agents build on the compliant agent_v15 base. |
| **III. Manual Submissions Only** | PASS | This feature does not include a Kaggle submission; submission remains manual and deliberate. |
| **IV. Experiment & Documentation Discipline** | PASS | FR-001 mandates an experiment record per mechanic before the agent file is written. Each record will include hypothesis, change, self-play result, and conclusion as required. |
| **V. Local Self-Play as Primary Evaluation Loop** | PASS | All candidates are evaluated with 20 local self-play games (seeds 0–19) before any promotion decision. |

**Complexity Tracking**: No violations requiring justification. Principle I is waived by pre-existing project precedent, not a new deviation.

**Post-design re-check**: No new violations introduced in Phase 1. All agents inherit agent_v15's safety guards (FR-007).

## Project Structure

### Documentation (this feature)

```text
specs/006-agent-experiments-round-2/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v15.py             # Immutable baseline — never modified
agent_v16.py             # Candidate E: speed-corrected orbit lead
agent_v17.py             # Candidate F: transit-adjusted fleet sizing
agent_v18.py             # Candidate G: adaptive range expansion
agent_v19.py             # Candidate H: capture-ROI scoring
agent_v20.py             # Combined agent (all ≥55% mechanics)

experiments/
├── 2026-05-30-candidate-e-orbit-lead-fix.md
├── 2026-05-30-candidate-f-transit-sizing.md
├── 2026-05-30-candidate-g-adaptive-range.md
├── 2026-05-30-candidate-h-roi-scoring.md
└── 2026-05-30-combined-agent-v20.md

eval.py                  # Evaluation harness — not modified
diagnose_v9.py           # Diagnostic harness — not modified
```

**Structure Decision**: Flat repo root for agent scripts (matches all prior agents v2–v15). Experiment records in `experiments/` as per constitution. No new directories needed.

---

## Phase 0: Research

> Output: `specs/006-agent-experiments-round-2/research.md`

All design decisions are documented in [research.md](research.md). Key decisions summarized:

- **D-001**: Speed-corrected orbit lead computes `fleet_speed(target.ships + 1)` per target inside the candidates loop, not once per source planet. Fixes the 70%-overestimate of travel speed when source is large and send is small.
- **D-002**: Transit-adjusted fleet sizing uses `travel_turns = hypot(mine→predicted_pos) / fleet_speed(target.ships + 1)`. Ships sent = `target.ships + target.production × travel_turns + 1`. Skip if source can't afford adjusted amount.
- **D-003**: Adaptive range uses `own_ships / enemy_ships` ratio where enemy = opponent-owned planets only (not neutral). Range factor: ≥1.5 → 3.5; ≤0.7 → 1.5; else 2.0.
- **D-004**: Capture-ROI score = `target.production × max(1, 100 − travel_turns) / (target.ships + target.production × travel_turns + 1)`. Travel turns clamped to prevent zero/negative numerator.
- **D-005**: Diagnostic scope: `diagnose_v9.py` on agent_v20 only (same policy as round 005).
- **D-006**: Integration order in agent_v20: (1) compute adaptive range_factor, (2) per-target orbit lead with correct speed, (3) ROI or production/distance scoring, (4) transit-adjusted ships_needed.

---

## Phase 1: Design

> Outputs: `specs/006-agent-experiments-round-2/data-model.md`, `specs/006-agent-experiments-round-2/quickstart.md`

Entities and per-agent behavioral contracts documented in [data-model.md](data-model.md).

Evaluation workflow documented in [quickstart.md](quickstart.md).

---

## Known Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| Transit-adjusted sizing (F) replicates Candidate B starvation | Medium — skip-if-insufficient can block all targets | Diagnose by checking avg targets-per-turn; if near zero, lower adjustment formula |
| Adaptive range (G) causes path-unsafe targets to sneak through | Low — `_path_safe()` already filters unconditionally | No special handling needed |
| ROI scoring (H) favors near-zero-production planets with 0 ships | Low — formula: 0 production → 0 score regardless | Edge case: neutral comets with 0 production are already excluded by comet logic |
| Speed-corrected orbit lead (E) overshoots on fast-orbiting planets | Low — `_refined_orbit_lead` does 2 iterations; rounding converges | Add third iteration if overshoot diagnosed |
| E+F+H all use travel_turns; combined agent computes it multiple times | Low — redundant computation only, no semantic conflict | Refactor to compute once per target in combined agent |
