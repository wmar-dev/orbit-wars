# Implementation Plan: Advanced Agent Techniques (Round 8)

**Branch**: `031-advanced-agent-techniques` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-advanced-agent-techniques/spec.md`

## Summary

Round 8 pivots the lineage from incremental constant-tweaking — which washed out near 50% across Rounds 5–7 — to **qualitatively more advanced decision techniques**, motivated by the single hardest signal in the project: `agent_v68` wins **0%** against the strongest loadable benchmark, `slawekbiel_agent` ("the-producer-agent"). Reading that opponent reveals it is not a neural net but a **torch-vectorized global planner**: it scores every (source→target) launch candidate across all planets simultaneously, repositions ships up a "regroup gradient" toward stressed planets, and applies reinforcement-timing factors. Those are precisely the structural capabilities `agent_v68` lacks — it claims targets per-planet greedily, then beam-searches only a few candidate move-sets. The key planning insight: slawekbiel's *strategy* is reproducible in **pure Python**; only its compute substrate (torch) is excluded by the stdlib-only submission constraint.

The round forks `agent_v68 → agent_v69.py` (frozen baseline unchanged) and implements three advanced-technique candidates, each behind an independent toggle in an isolated code region:

- **Candidate A — Global coordinated allocation**: replace per-planet greedy target claiming with a joint assignment that scores all (source, target) pairs and resolves source/target conflicts globally, so multiple planets coordinate fronts instead of piling on or stalling.
- **Candidate B — Deeper time-bounded search**: widen and deepen the lookahead (iterative-deepening beam, or time-bounded MCTS) under a strict wall-clock budget with graceful degradation to the current best's move when the budget is hit.
- **Candidate C — Regroup/reinforcement repositioning**: add a "regroup gradient" that moves surplus ships from safe rear planets toward stressed/threatened owned planets ahead of an attack — a *coordinated* repositioning distinct from Round 4's already-failed reactive `DEFENSE_INTERCEPT`.

Each candidate is evaluated over ≥50 `--swap` self-play games vs frozen `agent_v68` (pass ≥52%) **and** ≥30 `--swap` games vs `slawekbiel_agent` (must not regress below the current best's 0%; ideally strictly >0% per SC-001). Passers are combined, the combination re-evaluated over ≥50 self-play + ≥30 benchmark games, and the best config adopted only if it beats `agent_v68` at the round threshold. If nothing passes, `agent_v68` is retained and the negative result documented (mirroring Rounds 5–7).

## Technical Context

**Language/Version**: Python 3.14.0 (local via `uv` with `pyproject.toml`); Kaggle sandbox runs Python 3 with stdlib + `kaggle_environments` only.

**Primary Dependencies**: Agent runtime — `math`, `time`, `random`, `copy` (stdlib) + `kaggle_environments.envs.orbit_wars.orbit_wars.Planet` only. Tooling (local, not submitted) — `eval.py` (h2h/4p/opponents harness), `record_replays.py` (replay capture), `analyze-replay` skill, and `torch` 2.12.0 (now installs on Python 3.14, so `slawekbiel_agent` loads — the Round 7 blocker is resolved).

**Storage**: None at play time (single-file agent, no disk I/O during a turn). Replays written as JSON to `replays/replay_<slug>_<ts>_<idx>.json`.

**Testing**: `eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 50 --swap --jobs 4` for self-play; `eval.py h2h --agent0 agent_v69.py --agent1 opponent_agents/slawekbiel_agent.py --games 30 --swap` (or `eval.py opponents`) for the benchmark check; `record_replays.py` + `analyze-replay` for design input.

**Target Platform**: Kaggle sandbox (Python 3, stdlib + `kaggle_environments`); local macOS + `.venv` managed by `uv`.

**Project Type**: Single-file competition agent (Constitution Option A — all helpers inlined, no local runtime imports).

**Performance Goals**: ≤0.8s per turn (0.2s margin under the 1s `actTimeout`); p99 per-turn < 100ms historically. Candidate B explicitly trades compute for strength and therefore MUST be wall-clock-bounded with a safe fallback.

**Constraints**: Stdlib + `kaggle_environments` only in the submitted agent — **no `numpy`/`torch`/third-party at play time** (FR-009). This rules out a neural value net or vectorized tensor planner in the agent itself; advanced techniques must be pure-Python algorithms (global assignment, search, gradient repositioning). `agent_v68.py` is a frozen, read-only fork point. New candidates must preserve safety filters (sun-path avoidance, in-bounds dispatch) and the per-turn time budget (FR-008, FR-010).

**Scale/Scope**: Typical game: 20–30 planets, 0–50 in-transit fleets, 500-turn horizon. Phase A: design input from ≥5 fresh `agent_v68`-vs-`slawekbiel` replays. Phase B/C: 3 candidates × (50 self-play + 30 benchmark) + 1 combination × (50 + 30) ≈ 320 games.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | **Accepted deviation** | RL training (specs 026–028) failed to converge (0% vs `agent_v64`) across three rounds; the project reverted to the heuristic lineage. This round advances the heuristic *technique class* (global allocation, deeper search, regroup repositioning), not constants. Same documented deviation as Rounds 6–7. A learned value function is explicitly out of scope here because FR-009 forbids torch/numpy in the submitted agent; the RL path remains open for a dedicated future round. |
| II. Fair Play | **Pass** | No engine exploits; `actTimeout` respected — Candidate B is wall-clock-bounded with a guaranteed safe fallback (FR-010), and safety filters are preserved (FR-008). |
| III. Manual Submissions | **Pass** | Any Kaggle submission is manual, only after local evals confirm an improvement over `agent_v68`. |
| IV. Experiment Documentation | **Pass** | Replay analysis, per-candidate evals, the combination, and the benchmark re-verification are each documented in `experiments/` before any submission (FR-011). |
| V. Local Self-Play | **Pass** | Every candidate, the combination, and the re-check exceed the 20-game minimum (50 self-play / 30 benchmark). |
| VI. Submission Package | **Pass** | `agent_v69.py` remains a single self-contained file (Option A), matching `agent_v68.py`; pre-submission import check required if submitted. |
| VII. 95% Confidence | **Pass** | Two independent confirmations (≥50-game self-play AND ≥30-game benchmark non-regression) raise decision confidence above the single self-play signal; the benchmark re-check guards against self-play overfit. |

**Result**: PASS (one accepted, documented deviation on Principle I, identical in kind to Rounds 6–7). No new violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/031-advanced-agent-techniques/
├── plan.md              # This file
├── research.md          # Phase 0 output: technique selection, search-budget, eval protocols
├── data-model.md        # Phase 1 output: artifact "entities" for the round
├── quickstart.md        # Phase 1 output: exact commands for replay, per-candidate eval, combination
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

No `contracts/` directory: the round exposes no external interface — it produces agent files and experiment logs consumed only within the repo.

### Source Code (repository root)

```text
agent_v68.py                                  # Existing, frozen — fork point and self-play baseline (current best)
agent_v69.py                                  # New: fork of agent_v68; hosts Candidate A/B/C behind
                                               # independent toggles + the combined config
opponent_agents/slawekbiel_agent.py           # Existing benchmark opponent (now loadable; torch 2.12.0)
replays/replay_slawekbiel_<ts>_<idx>.json     # New: agent_v68 vs benchmark (design input)
experiments/
├── 2026-06-1X-round8-replay-analysis.md       # Phase A: analyze-replay output vs slawekbiel
└── 2026-06-1X-experiments-round8.md           # Phase B/C: per-candidate + combination + benchmark re-check
README.md                                      # Updated only if a new best is adopted (FR-013)
Makefile                                       # AGENT/RENDER_AGENT updated only if a new best is adopted (FR-013)
```

**Structure Decision**: No new project structure — the round adds one new agent file (`agent_v69.py`, next after `agent_v68.py`) forked from `agent_v68.py`, plus replay captures and experiment logs. `agent_v68.py` is a read-only fork point and self-play baseline and is not modified.

---

## Phase 0: Research

See [research.md](research.md). Resolves: (R1) which advanced techniques to implement and why each is distinct from a prior failed candidate; (R2) how to bound Candidate B's search within the 0.8s budget with graceful degradation; (R3) the per-candidate / combination / benchmark evaluation and adoption protocol, including the SC-001 ">0% vs benchmark" target.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) — artifact entities: `FrozenBaselineAgent`, `CandidateTechnique`, `BenchmarkOpponent`, `EvaluationResult`, `CombinedConfig`, `ExperimentLog`.

### Quickstart

See [quickstart.md](quickstart.md) — exact commands for replay capture/analysis, per-candidate self-play + benchmark evals, the combination run, and the benchmark re-verification.

### Agent Architecture (Phase C)

`agent_v69.py` is created as a copy of `agent_v68.py`, then extended with one independent toggle per candidate, each touching an isolated code region so toggles compose cleanly for the combination run:

```
agent_v69.py  (= copy of agent_v68.py)
├── CONSTANTS
│   ├── (all agent_v68 constants/toggles preserved unchanged)
│   ├── GLOBAL_ALLOC_ENABLED   = False   # Candidate A: joint multi-source target assignment
│   ├── DEEP_SEARCH_ENABLED    = False   # Candidate B: time-bounded deeper/wider lookahead
│   ├── DEEP_SEARCH_BUDGET_MS  = 700     #   wall-clock bound for Candidate B (fallback below)
│   └── REGROUP_ENABLED        = False   # Candidate C: regroup gradient repositioning
├── _greedy_moves / _gen_beam_candidates / _beam_search
│   ├── Candidate A gates the target-claiming step (replaces per-planet claim with global assignment)
│   ├── Candidate B gates _beam_search's depth/width + adds a wall-clock guard returning the
│   │   greedy/current-best move on timeout (FR-010 graceful degradation)
│   └── Candidate C adds a repositioning pass over idle rear planets, behind its own toggle
```

Each candidate is evaluated with only its own toggle `True`; the combination run sets every passing candidate's toggle `True`. Default committed state of all toggles is `False`, so `agent_v69 ≡ agent_v68` if nothing passes (mirroring `agent_v65`/`agent_v67`).

### Agent Context Update

`CLAUDE.md`'s active-feature pointer is updated to this plan (`specs/031-advanced-agent-techniques/plan.md`).

### Post-Design Constitution Re-Check

PASS — design introduces no new third-party runtime dependency (all three candidates are pure-Python), preserves safety filters and the time budget (Candidate B explicitly bounded per FR-010), and keeps `agent_v69.py` a single self-contained file. No change to the Constitution Check verdict above.

---

## Phase 2: Task Planning Approach

*(Executed by `/speckit-tasks`, not this command — described here for traceability.)*

`tasks.md` will decompose into: (T-A) capture ≥5 `agent_v68`-vs-`slawekbiel` replays and run `analyze-replay` to confirm/refine the three candidate designs; (T-B) fork `agent_v68 → agent_v69.py` with the three toggles defaulting `False`; (T-C..E) implement Candidates A/B/C each in isolation; (T-eval) per-candidate 50-game self-play + 30-game benchmark evals with safety/timing checks; (T-combine) combine passers and re-run 50 + 30; (T-doc) write the two experiment logs; (T-adopt) on a confirmed new best, update README table, Makefile `AGENT`/`RENDER_AGENT`, and the auto-memory lineage note.
