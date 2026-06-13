# Implementation Plan: Experiments Round 6

**Branch**: `029-experiments-round-6` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-experiments-round-6/spec.md`

## Summary

A three-phase experiment round. Phase A resolves the Round 5 non-transitivity finding (`agent_v65`≡`agent_v64` loses to `agent_v58` 43.3%, yet `agent_v60` claims a 54% win over `agent_v58` plus a higher Kaggle score) by running a 50-game `--swap` round-robin among `agent_v58`, `agent_v60`, and `agent_v64` to pick a single "Round 6 baseline." Phase B generates fresh local replays of that baseline vs `opponent_agents/slawekbiel_agent.py` (the toughest known local opponent, 0/7 in the last analysis) and runs the `analyze-replay` skill to surface 2 new candidate directions not already covered by mechanics in `agent_v57`–`agent_v66`. Phase C forks the baseline into `agent_v67.py`, implements each candidate behind an independent toggle constant, evaluates each over 50 `--swap` games vs the baseline, and combines any that pass (≥52%) into a final configuration re-verified the same way.

## Technical Context

**Language/Version**: Python 3 (Kaggle sandbox; locally via `uv` with `pyproject.toml`)

**Primary Dependencies**: `math`, `time`, `random`, `copy` (stdlib); `kaggle_environments.envs.orbit_wars.orbit_wars.Planet`; `eval.py` (local h2h/4p/opponents harness); `analyze-replay` skill for behavioral analysis

**Storage**: N/A — single-file agents, no disk I/O during play. Replay captures for analysis are written as JSON to `replays/`.

**Testing**: `eval.py h2h --agentN ... --games 50 --swap --jobs 4` for the baseline matrix and each candidate eval; `analyze-replay` skill on generated replay JSON for Phase B

**Target Platform**: Kaggle sandbox (Python 3, stdlib + `kaggle_environments` only); local: macOS + `.venv` managed by `uv`

**Project Type**: Single-file competition agent (Option A — all helpers inlined, no local imports)

**Performance Goals**: ≤0.8s per turn (0.2s margin from the 1-second Kaggle `actTimeout`); p99 per-turn timing < 100ms, consistent with prior rounds

**Constraints**: All helpers inlined; stdlib + `kaggle_environments` only; no `numpy`, `scipy`, or third-party packages; new candidates must not alter `agent_v58`/`agent_v60`/`agent_v64` (frozen baselines used for Phase A comparison)

**Scale/Scope**: Typical game: 20–30 planets, 0–50 in-transit fleets, 500-turn horizon; Phase A is 150 games (3 pairings × 50); Phase B is ≥5 replay games; Phase C is up to 150 games (2 candidates × 50 + 1 combination × 50)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | **Accepted deviation** | RL training (Rounds 6–8, specs 026–028) failed to converge (0% win rate vs `agent_v64`) across three rounds. The project explicitly reverted to the heuristic `agent_v58` lineage "for the next round of experiments" (commit 876a9a8). This round continues that heuristic lineage; RL path remains open for a future round. |
| II. Fair Play | **Pass** | No engine exploits; `actTimeout` respected via existing dispatch logic carried over from the chosen baseline |
| III. Manual Submissions | **Pass** | Any Kaggle submission only happens after this round's local evals confirm an improvement over the Round 6 baseline; submitted manually |
| IV. Experiment Documentation | **Pass** | Phase A (baseline matrix), Phase B (replay analysis), and Phase C (per-candidate + combination results) are each documented in `experiments/` before any submission |
| V. Local Self-Play | **Pass** | Phase A uses 150 games (3×50); each Phase C candidate and the combination use 50-game `--swap` evals, exceeding the 20-game minimum |
| VI. Submission Package | **Pass** | `agent_v67.py` remains a single self-contained file (Option A), matching `agent_v58`/`agent_v60`/`agent_v64`; pre-submission import check required if submitted |
| VII. 95% Confidence | **Pass** | Phase A's 150-game matrix directly addresses the confidence gap left by Round 5's single 30-game test; Phase C candidates use the established 50-game/52% pass bar |

## Project Structure

### Documentation (this feature)

```text
specs/029-experiments-round-6/
├── plan.md              # This file
├── research.md          # Phase 0 output: baseline-matrix protocol + replay-analysis protocol
├── data-model.md         # Phase 1 output
├── quickstart.md          # Phase 1 output: exact commands for Phases A/B/C
└── tasks.md              # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
agent_v58.py, agent_v60.py, agent_v64.py   # Existing, frozen — inputs to the Phase A round-robin
agent_v67.py                                # New: fork of the Round 6 baseline (winner of Phase A);
                                             # hosts Candidate 1, Candidate 2, and the combined config
                                             # behind independent toggle constants
replays/                                    # New replay JSON captures: baseline vs slawekbiel_agent (Phase B)
experiments/
├── 2026-06-13-round6-baseline-matrix.md     # Phase A: win-rate matrix + baseline decision
├── 2026-06-1X-replay-analysis.md            # Phase B: analyze-replay output (date-stamped by the skill)
└── 2026-06-1X-experiments-round6.md         # Phase C: per-candidate evals + combination result
```

**Structure Decision**: No new project structure — this round adds one new agent file (`agent_v67.py`, the next available version number after `agent_v66.py`) forked from whichever of `agent_v58`/`agent_v60`/`agent_v64` wins the Phase A matrix, plus replay captures and experiment logs. `agent_v58`, `agent_v60`, and `agent_v64` are read-only inputs to Phase A and are not modified.

---

## Phase 0: Research

See [research.md](research.md).

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Quickstart

See [quickstart.md](quickstart.md).

### Agent Architecture (Phase C)

`agent_v67.py` is created only after Phase A determines the baseline (`<BASELINE>` below stands in for whichever of `agent_v58.py`/`agent_v60.py`/`agent_v64.py` wins):

```
agent_v67.py  (= copy of <BASELINE>.py)
├── CONSTANTS
│   ├── (all <BASELINE> constants preserved)
│   ├── CANDIDATE_1_ENABLED = True   # toggle for the first Phase B finding
│   └── CANDIDATE_2_ENABLED = True   # toggle for the second Phase B finding
│
├── <modified dispatch/eval function(s)>   # exact functions depend on Phase B findings;
│   ├── Candidate 1 path (gated by CANDIDATE_1_ENABLED)
│   └── Candidate 2 path (gated by CANDIDATE_2_ENABLED)
│
└── Evaluation protocol (per FR-006/FR-007):
    1. CANDIDATE_1_ENABLED=True,  CANDIDATE_2_ENABLED=False → 50-game --swap vs <BASELINE>
    2. CANDIDATE_1_ENABLED=False, CANDIDATE_2_ENABLED=True  → 50-game --swap vs <BASELINE>
    3. If either passes (≥52%): enable all passing candidates together → 50-game --swap vs <BASELINE> (confirmation)
```

No source-level design beyond this skeleton is possible until Phase B (replay analysis) identifies the 2 candidate directions — this is intentional per FR-004, which requires the candidates to be grounded in fresh replay evidence rather than assumed in advance.
