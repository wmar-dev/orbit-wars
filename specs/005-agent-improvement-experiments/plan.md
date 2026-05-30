# Implementation Plan: Agent Improvement Experiments

**Branch**: `005-agent-improvement-experiments` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-agent-improvement-experiments/spec.md`

## Summary

Run four isolated mechanic experiments (agent_v11–v14) against agent_v10 as the baseline, then stack all passing mechanics (≥55% win rate) into agent_v15. Each experiment follows the constitution's documentation-first discipline: an experiment record in `experiments/` before the agent file is written.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: kaggle_environments (orbit_wars engine), eval.py, diagnose_v9.py (both at repo root, used as-is)

**Storage**: N/A — agent files at repo root, experiment records in `experiments/`

**Testing**: `eval.py --agent0 agentN.py --agent1 agent_v10.py --games 20 --seed 0` (seeds 0–19); `diagnose_v9.py --agent agent_v15.py --games 20` for safety regression check on combined agent only

**Target Platform**: Local Python execution (Kaggle submission is manual, out of scope for this feature)

**Project Type**: Game AI agent scripts

**Performance Goals**: Each candidate ≥55% win rate vs agent_v10 over 20 games; combined agent_v15 ≥65% win rate vs agent_v10

**Constraints**: actTimeout 1s/turn; no modification to eval.py or diagnose_v9.py; no removal or weakening of sun avoidance, OOB rejection, or planet obstruction checks from agent_v10

**Scale/Scope**: 5 agent files (agent_v11–v15) + 5–6 experiment records; up to 6 evaluation runs × 20 games

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| **I. Reinforcement Learning First** | WAIVED (justified) | All mechanics are rule-based heuristics. Per the spec and prior precedent (001–004), RL-first is the long-term path; heuristic iteration is explicitly scoped here as the approved short-term method. Mechanics-that-require-fundamentally-redesigning-the-loop (MCTS, RL) are out of scope. |
| **II. Fair Play & Rules Compliance** | PASS | No engine bug exploitation; actTimeout respected; all agents build on the compliant agent_v10 base. |
| **III. Manual Submissions Only** | PASS | This feature does not include a Kaggle submission; submission remains manual and deliberate. |
| **IV. Experiment & Documentation Discipline** | PASS | FR-001 mandates an experiment record per mechanic before the agent file is written. Each record will include hypothesis, change, self-play result, and conclusion as required. |
| **V. Local Self-Play as Primary Evaluation Loop** | PASS | All candidates are evaluated with 20 local self-play games (seeds 0–19) before any promotion decision. |

**Complexity Tracking**: No violations requiring justification. Principle I is waived by pre-existing project precedent, not a new deviation.

**Post-design re-check**: No new violations introduced in Phase 1. All agents inherit agent_v10's safety guards (FR-007).

## Project Structure

### Documentation (this feature)

```text
specs/005-agent-improvement-experiments/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v10.py             # Immutable baseline — never modified
agent_v11.py             # Candidate A: redundant fleet avoidance
agent_v12.py             # Candidate B: garrison sizing (best sub-experiment)
agent_v13.py             # Candidate C: threat-aware defense
agent_v14.py             # Candidate D: single-sender coordination
agent_v15.py             # Combined agent (all ≥55% mechanics)

experiments/
├── 2026-05-30-candidate-a-redundant-fleet.md
├── 2026-05-30-candidate-b-garrison-sizing.md
├── 2026-05-30-candidate-c-threat-defense.md
├── 2026-05-30-candidate-d-single-sender.md
└── 2026-05-30-combined-agent-v15.md

eval.py                  # Evaluation harness — not modified
diagnose_v9.py           # Diagnostic harness — not modified
```

**Structure Decision**: Flat repo root for agent scripts (matches all prior agents). Experiment records in `experiments/` as per constitution. No new directories needed.

---

## Phase 0: Research

> Output: `specs/005-agent-improvement-experiments/research.md`

No NEEDS CLARIFICATION items remain — all were resolved in the spec's Clarifications section (2026-05-30 session). Research covers mechanics context and design decisions below.

### Candidate A — Redundant Fleet Avoidance

**Decision**: Skip launching at a target when a friendly fleet is already en route with `en_route_ships ≥ target.ships + 1`.

**Rationale**: Current agent_v10 re-evaluates all planets each turn without accounting for committed fleets, causing multiple ships to pile onto already-won engagements and depleting source planets unnecessarily.

**Alternatives considered**:

- Track all in-flight fleets globally and subtract from target effective strength — more precise but requires maintaining fleet state across turns; ruled out as over-engineering for a heuristic agent.
- Check only the nearest en route fleet — rejected because multiple small fleets summed may exceed target.ships+1 while no single one does. The simpler `sum(f.ships for f in en_route) >= target.ships + 1` check is chosen.

**Prior art**: agent_v6 had no redundancy avoidance; all subsequent agents inherited this gap.

---

### Candidate B — Garrison Sizing

**Decision**: Send only enough ships to capture (`target.ships + 1`), with source planet required to retain a garrison floor. Three garrison floor sub-experiments: `production × 5`, `production × 10`, fixed `10`. The best-performing variant advances to agent_v15.

**Rationale**: agent_v10 sends `available_ships // 2` regardless of what is needed, over-committing on weak targets and under-committing on strong ones.

**Alternatives considered**:

- Dynamic floor based on threat level — deferred to Candidate C; B focuses only on send-sizing.
- `production × 3` — considered too low; leaves planets vulnerable during high-tempo enemy pushes.

**Sub-experiment evaluation order**: production×5 → production×10 → fixed 10. Winner (highest win rate vs agent_v10) is the variant embedded in agent_v12.

---

### Candidate C — Threat-Aware Defense

**Decision**: Dispatch reinforcements to owned planets when `incoming_enemy_ships > current_garrison + production × 5`. One reinforcement dispatch per threatened planet per turn (cap prevents runaway defense).

**Rationale**: agent_v6 implemented a broad `incoming > garrison` defense that triggered too frequently, converting offensive ships to defensive duty every turn and degrading win rate. The narrower `production × 5` buffer provides a meaningful safety margin before triggering.

**Alternatives considered**:

- `production × 3` threshold — too easy to trigger; risks recreating agent_v6's over-defense.
- Proportional reinforcements (send exactly `incoming − garrison`) — requires more state tracking; dismissed for this heuristic scope.
- Threshold `production × 10` — may leave planets exposed when production is low; not chosen as default but noted for future experimentation.

**Prior failure reference**: `experiments/2026-05-29-defensive-reinforce.md` documents why broad defense hurt agent_v6. This design explicitly addresses that failure mode.

---

### Candidate D — Single-Sender Coordination

**Decision**: For each enemy target, only the planet with the minimum `distance ÷ available_ships_surplus` ratio launches an attack. `available_ships_surplus = current_ships − garrison_floor`.

**Rationale**: Multiple planets targeting the same enemy waste combined ship counts that could be redirected to different targets, spreading the agent's offensive reach.

**Alternatives considered**:

- Closest planet only (minimum distance) — ignores ship efficiency; a nearby planet with few surplus ships is less valuable than a more distant one with many.
- Highest surplus planet — ignores travel time; a surplus-rich planet far away is slow to help.
- `distance ÷ available_ships_surplus` balances both dimensions.

**Interaction with Candidate B**: If both pass, Candidate D uses the same garrison floor chosen by Candidate B's winning sub-experiment as its surplus denominator.

---

### Combined Agent (agent_v15)

**Decision**: Stack all mechanics with ≥55% individual win rate vs agent_v10. Apply in this order within the targeting loop:

1. Single-sender coordination (D) — determine who may fire at each target
2. Redundant fleet check (A) — skip targets already covered
3. Garrison floor enforcement (B) — size the fleet correctly
4. Threat-aware defense (C) — interleave with offense; defense dispatches happen before offensive moves

**Interaction risks**:

- A + D: If D restricts sender and A skips redundant targets, fewer planets fire per turn — this is the intended effect (quality over quantity).
- B + C: If garrison floor (B) is high, Candidate C's reinforcement may find no spare ships on source. Add a guard: only dispatch reinforcement if `source.ships − garrison_floor > 0`.
- C + D: Defense dispatch must bypass D's single-sender constraint (defense is not an offensive action and has a separate dispatch path).

---

## Phase 1: Design & Contracts

> Outputs: `data-model.md`, `quickstart.md`

No external interface contracts are needed — this is a standalone game AI with no public API, CLI, or library surface. The contracts/ directory is skipped.

---
