# Implementation Plan: Experiments Round 7

**Branch**: `030-experiments-round-7` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/030-experiments-round-7/spec.md`

## Summary

A three-phase experiment round forked from the current best heuristic agent, `agent_v64`. **Phase A** fixes Round 6's core methodological flaw — the strongest known opponent (`slawekbiel_agent`) was unloadable (`torch` has no Python 3.14 wheel), so Round 6 analyzed games vs `agent_v60`, which `agent_v64` already beats 80%. Phase A makes one documented attempt to unlock `slawekbiel`, then runs `agent_v64` over ≥20 `--swap` games against every loadable opponent (`eval.py opponents`) plus `agent_v58`/`agent_v60`, and designates the lowest-win-rate opponent the "Round 7 benchmark." **Phase B** records ≥5 fresh replays of `agent_v64` vs that benchmark (`record_replays.py`) and runs the `analyze-replay` skill to surface 2–3 candidate directions distinct from `agent_v57`–`agent_v67`, explicitly respecting Round 6's two documented failure traps (global garrison scaling was a 48% wash; affordable fallback regressed to 6% by short-circuiting the beam-search "wait" choice). **Phase C** forks `agent_v64` into `agent_v68.py`, implements each candidate behind an independent toggle, evaluates each over 50 `--swap` games vs `agent_v64` (pass ≥52%), combines passers, and — new this round — re-verifies the resulting best config over ≥30 `--swap` games vs the benchmark opponent to confirm the self-play win does not regress against a tougher opponent.

## Technical Context

**Language/Version**: Python 3.14 (local via `uv` with `pyproject.toml`); Kaggle sandbox runs Python 3 with stdlib + `kaggle_environments` only

**Primary Dependencies**: `math`, `time`, `random`, `copy` (stdlib); `kaggle_environments.envs.orbit_wars.orbit_wars.Planet`; `eval.py` (h2h/4p/opponents harness); `record_replays.py` (replay capture in analyze-replay format); `analyze-replay` skill for behavioral analysis

**Storage**: N/A at play time — single-file agents, no disk I/O during a turn. Replay captures written as JSON to `replays/replay_<opponent-slug>_<ts>_<idx>.json` by `record_replays.py`.

**Testing**: `eval.py h2h --agentN ... --games 50 --swap --jobs 4` for candidate evals; `eval.py opponents --agent agent_v64.py --games 20` for the Phase A opponent sweep; `record_replays.py` + `analyze-replay` skill for Phase B

**Target Platform**: Kaggle sandbox (Python 3, stdlib + `kaggle_environments`); local: macOS + `.venv` managed by `uv` (Python 3.14.0)

**Project Type**: Single-file competition agent (Option A — all helpers inlined, no local imports)

**Performance Goals**: ≤0.8s per turn (0.2s margin from the 1-second Kaggle `actTimeout`); p99 per-turn timing < 100ms, consistent with prior rounds

**Constraints**: All helpers inlined; stdlib + `kaggle_environments` only; no `numpy`/`scipy`/third-party packages in the agent; new candidates must not modify `agent_v64.py` (frozen baseline/fork point). `torch` is NOT available in the local Python 3.14 env (blocks `slawekbiel_agent`), and adding it is out of scope for the agent itself — any install attempt is local-tooling-only, for replay generation.

**Scale/Scope**: Typical game: 20–30 planets, 0–50 in-transit fleets, 500-turn horizon. Phase A: ~7 loadable opponents × 20 games + 2 sparring agents × 20 ≈ 180 games. Phase B: ≥5 replay games. Phase C: up to 3 candidates × 50 + 1 combination × 50 + 1 benchmark re-check × 30 ≈ 230 games.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | **Accepted deviation** | RL training (specs 026–028) failed to converge (0% win rate vs `agent_v64`) across three rounds; the project reverted to the heuristic lineage. This round continues that heuristic lineage; the RL path remains open for a future round. Same accepted deviation as Round 6. |
| II. Fair Play | **Pass** | No engine exploits; `actTimeout` respected via existing dispatch logic carried over from `agent_v64`. |
| III. Manual Submissions | **Pass** | Any Kaggle submission happens manually, only after this round's local evals confirm an improvement over `agent_v64`. |
| IV. Experiment Documentation | **Pass** | Phase A (opponent matrix), Phase B (replay analysis), and Phase C (per-candidate + combination + benchmark re-check) are each documented in `experiments/` before any submission. |
| V. Local Self-Play | **Pass** | Phase A uses ≥20 games per opponent; each Phase C candidate, the combination, and the benchmark re-check exceed the 20-game minimum (50/50/30). |
| VI. Submission Package | **Pass** | `agent_v68.py` remains a single self-contained file (Option A), matching `agent_v64.py`; pre-submission import check required if submitted. |
| VII. 95% Confidence | **Pass** | The benchmark re-check (FR-009) adds a second, tougher-opponent confirmation on top of the 50-game self-play eval, raising decision confidence above Round 6's single self-play signal. |

**Result**: PASS (one accepted, documented deviation on Principle I, identical to Round 6). No new violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/030-experiments-round-7/
├── plan.md              # This file
├── research.md          # Phase 0 output: opponent-selection, replay, and candidate-eval protocols
├── data-model.md        # Phase 1 output: artifact "entities" for each phase
├── quickstart.md        # Phase 1 output: exact commands for Phases A/B/C
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

No `contracts/` directory: this round exposes no external interface — it produces agent files and experiment logs consumed only within the repo.

### Source Code (repository root)

```text
agent_v64.py                                  # Existing, frozen — fork point and self-play baseline
agent_v68.py                                  # New: fork of agent_v64; hosts Candidate 1..N behind
                                               # independent toggle constants + the combined config
opponent_agents/*.py                          # Existing downloaded opponents (Phase A sweep inputs)
replays/replay_<slug>_<ts>_<idx>.json         # New: agent_v64 vs benchmark opponent (Phase B)
experiments/
├── 2026-06-1X-round7-opponent-matrix.md       # Phase A: agent_v64 win-rate table + benchmark choice
├── 2026-06-1X-replay-analysis.md              # Phase B: analyze-replay output (date-stamped by skill)
└── 2026-06-1X-experiments-round7.md           # Phase C: per-candidate evals + combination + benchmark re-check
```

**Structure Decision**: No new project structure — this round adds one new agent file (`agent_v68.py`, next available after `agent_v67.py`) forked from `agent_v64.py`, plus replay captures and experiment logs. `agent_v64.py` is a read-only fork point and self-play baseline and is not modified.

---

## Phase 0: Research

See [research.md](research.md). Resolves: (R1) how to select the Round 7 benchmark opponent and handle the `slawekbiel`/`torch` blocker; (R2) how to generate and analyze fresh replays; (R3) how to implement, evaluate, combine candidates, and run the benchmark re-check.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md) — artifact entities: `BenchmarkOpponent`, `OpponentWinRateEntry`, `CandidateDirection`, `ReplayAnalysisReport`, `CombinedConfig`.

### Quickstart

See [quickstart.md](quickstart.md) — exact commands for Phases A, B, and C.

### Agent Architecture (Phase C)

`agent_v68.py` is created as a copy of `agent_v64.py`, then extended with one independent toggle per candidate identified in Phase B:

```
agent_v68.py  (= copy of agent_v64.py)
├── CONSTANTS
│   ├── (all agent_v64 constants preserved unchanged)
│   ├── CANDIDATE_1_ENABLED = False   # toggle for the first Phase B finding
│   ├── CANDIDATE_2_ENABLED = False   # toggle for the second Phase B finding
│   └── CANDIDATE_3_ENABLED = False   # (only if Phase B yields a third candidate)
└── _greedy_moves / helpers
    └── each candidate's logic gated behind its toggle, touching an
        independent code region so toggles compose cleanly for the combination run
```

Each candidate is evaluated with only its own toggle `True`; the combination run sets every passing candidate's toggle `True`. Default committed state of all toggles is `False` (so `agent_v68 ≡ agent_v64` if nothing passes, mirroring `agent_v65`/`agent_v67`).

### Agent Context Update

`CLAUDE.md`'s active-feature pointer is updated to this plan (see step in execution).

### Post-Design Constitution Re-Check

Re-checked after Phase 1: no new violations introduced. The design adds one file, reuses existing harnesses (`eval.py`, `record_replays.py`, `analyze-replay`), and respects the inlined-single-file constraint (Principle VI). PASS.

---

## Complexity Tracking

No constitution violations requiring justification. (The Principle I deviation is the standing, documented heuristic-lineage choice, not a new complexity introduced by this plan.)
