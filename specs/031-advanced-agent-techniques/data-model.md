# Phase 1 Data Model: Advanced Agent Techniques (Round 8)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-06-13

This round has no runtime data schema (the agent is stateless across turns apart from existing module-level caches). The "entities" below are the **artifacts** the round produces and the relationships used to decide adoption. They map the spec's Key Entities to concrete files and fields.

## FrozenBaselineAgent

The current best at round start; fork point and self-play opponent.

| Field | Value / Source |
|-------|----------------|
| `file` | `agent_v68.py` |
| `role` | Frozen — never modified this round (FR-001) |
| `benchmark_winrate` | 0% vs `slawekbiel_agent` (30 games, Round 7) — the number to beat |
| `selfplay_role` | `--agent1` in every per-candidate self-play eval |

**Invariant**: `git diff` on `agent_v68.py` must be empty for the entire round.

## CandidateTechnique

One qualitatively-advanced technique, toggled and isolated.

| Field | Description |
|-------|-------------|
| `id` | `A` (global allocation) / `B` (deep search) / `C` (regroup) |
| `toggle` | `GLOBAL_ALLOC_ENABLED` / `DEEP_SEARCH_ENABLED` / `REGROUP_ENABLED` |
| `technique_class` | coordinated-strategy / deeper-search / richer-eval+repositioning |
| `code_region` | target-claiming step / `_beam_search` wrapper / repositioning pass |
| `closes_gap` | slawekbiel global scoring / shallow beam / no repositioning |
| `distinct_from` | `MULTI_DISPATCH` (R6) / none (new axis) / `DEFENSE_INTERCEPT` (R4) |
| `default_state` | `False` (committed) |

**Validation rules**:
- Each candidate compiles and runs with *only* its own toggle `True` (isolation).
- All toggles `False` ⟹ `agent_v69 ≡ agent_v68` (regression-free default).
- No candidate adds a non-stdlib runtime import (FR-009).
- Candidate B carries `DEEP_SEARCH_BUDGET_MS` and a guaranteed fallback move (FR-010).

## BenchmarkOpponent

| Field | Value |
|-------|-------|
| `slug` | `slawekbiel` |
| `file` | `opponent_agents/slawekbiel_agent.py` (+ `orbit_lite` package) |
| `loadable` | Yes — `torch` 2.12.0 installs on Python 3.14 (R7 blocker resolved) |
| `current_best_winrate` | 0% (the wall this round attacks) |
| `eval_games` | ≥30 `--swap` |

## EvaluationResult

One row per candidate, the combination, and the re-check.

| Field | Type | Pass condition |
|-------|------|----------------|
| `subject` | agent config (toggle set) | — |
| `selfplay_winrate` | % over ≥50 `--swap` games | ≥52% (FR-004, FR-006) |
| `benchmark_winrate` | % over ≥30 `--swap` games | ≥0% (no regression); >0% targets SC-001 |
| `p99_turn_ms` | ms | < budget, zero forfeits (FR-008, SC-005) |
| `sun_losses` | count | 0 (FR-008, SC-004) |
| `oob_losses` | count | 0 (FR-008, SC-004) |
| `verdict` | PASS / FAIL | both axes + safety must hold |

## CombinedConfig

| Field | Description |
|-------|-------------|
| `toggles_on` | every PASS candidate's toggle set `True` |
| `selfplay_winrate` | re-eval ≥50 `--swap` vs `agent_v68` |
| `benchmark_winrate` | re-eval ≥30 `--swap` vs `slawekbiel` |
| `adopt` | True iff selfplay ≥52% AND no benchmark regression (FR-007, FR-012) |

**State transition** (round outcome):
```
no candidate PASS ─────────────► retain agent_v68 (document negative result)        [FR-012]
≥1 PASS, combo ≥52% selfplay ──► agent_v69 = new best; update README + Makefile +    [FR-013]
   and no benchmark regression       auto-memory lineage note
≥1 PASS, combo fails ──────────► retain agent_v68; document; optionally ship best
                                     single passing candidate if it alone clears bar
```

## ExperimentLog

| Field | File |
|-------|------|
| replay analysis | `experiments/2026-06-1X-round8-replay-analysis.md` (Phase A) |
| per-candidate + combination + re-check | `experiments/2026-06-1X-experiments-round8.md` (Phase B/C) |

**Invariant** (Principle IV): both logs exist and record hypothesis / change / result / conclusion before any Kaggle submission.
