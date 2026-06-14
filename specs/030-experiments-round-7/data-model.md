# Data Model: Experiments Round 7

This round produces decision records and experiment logs rather than runtime data structures. The "entities" below are the artifacts each phase reads or writes.

## BenchmarkOpponent

The loadable opponent against which `agent_v64` has the lowest win rate; the source of Phase B gap analysis.

| Field | Type | Description |
|---|---|---|
| `opponent_file` | string | Path under `opponent_agents/`, or `agent_v58.py`/`agent_v60.py` if external opponents are saturated |
| `agent_v64_win_rate` | float | `agent_v64`'s win rate vs this opponent (≥20 `--swap` games) — the lowest in the sweep |
| `is_saturated` | bool | `True` if the lowest win rate across all loadable opponents is still ≥65% |
| `rationale` | string | One-paragraph justification, written to `experiments/2026-06-1X-round7-opponent-matrix.md` |

**Validation**: `opponent_file` MUST be loadable in the local env (FR-001). The `slawekbiel` load attempt MUST be recorded regardless of outcome (FR-002).

## OpponentWinRateEntry

One row of the Phase A sweep.

| Field | Type | Description |
|---|---|---|
| `opponent_name` | string | Opponent slug or sparring agent name |
| `loadable` | bool | `False` for opponents that fail to import (e.g., `slawekbiel` missing `torch`) |
| `games` | int | ≥20 for loadable opponents |
| `agent_v64_win_rate` | float \| null | `null` if not loadable |
| `notes` | string | Import errors, timeouts, sun/OOB losses, etc. |

**Validation**: every `KNOWN_OPPONENTS` entry plus `agent_v58`/`agent_v60` appears; unloadable entries have `loadable=false` and a recorded reason.

## ReplayAnalysisReport

The Phase B output, in the format produced by the `analyze-replay` skill.

| Field | Type | Description |
|---|---|---|
| `games_analyzed` | int | ≥5 (FR-003) |
| `win_rate` | float | `agent_v64` vs `BenchmarkOpponent` |
| `median_divergence_turn` | int | From the skill's divergence-turn distribution |
| `divergence_window` | string | The decisive turn range driving losses (the "real" divergence, not a noisy trigger) |
| `behavioral_differences` | list[string] | ≥3 observed differences |
| `candidates` | list[CandidateDirection] | 2–3 (feeds Phase C) |

## CandidateDirection

A hypothesis-driven, independently-toggled tactical change identified in Phase B.

| Field | Type | Description |
|---|---|---|
| `id` | string | `candidate_1`, `candidate_2`, (`candidate_3`) |
| `toggle_constant` | string | Constant added to `agent_v68.py` (e.g., `CANDIDATE_1_ENABLED`) |
| `hypothesis` | string | From the Phase B report |
| `predicted_effect` | string | From the Phase B report |
| `risk` | string | From the Phase B report |
| `distinct_from_prior` | bool | Confirmed not a duplicate of mechanics in `agent_v57`–`agent_v67` (FR-004) |
| `avoids_prior_failure` | string \| null | Required (non-null) if adjacent to a Round 6 discard: how it avoids the documented failure mode (FR-005) |
| `win_rate_vs_baseline` | float | Result of the 50-game `--swap` eval vs `agent_v64` (FR-007) |
| `passed` | bool | `win_rate_vs_baseline >= 0.52` |

**Validation**: 2–3 records (FR-004); `distinct_from_prior` MUST be `true` for all before evaluation; any candidate adjacent to affordable-fallback or global-garrison-scaling MUST have non-null `avoids_prior_failure` (FR-005).

## CombinedConfig

The Phase C output if ≥1 candidate passes.

| Field | Type | Description |
|---|---|---|
| `agent_file` | string | `agent_v68.py`, with all passing candidates' toggles `True` |
| `enabled_candidates` | list[string] | IDs where `passed == true` |
| `win_rate_vs_baseline` | float | Confirmation 50-game `--swap` eval vs `agent_v64` (FR-008) |
| `passed` | bool | `win_rate_vs_baseline >= 0.52` |
| `win_rate_vs_benchmark` | float | ≥30-game `--swap` eval vs `BenchmarkOpponent` (FR-009) |
| `no_benchmark_regression` | bool | `win_rate_vs_benchmark >= BenchmarkOpponent.agent_v64_win_rate` (SC-005) |
| `timing_p99_ms` | float | Must be `< 100` (SC-006) |
| `sun_oob_losses` | int | Must be `0` across all Phase C eval games (SC-006) |

**State transition**: if `CombinedConfig.passed` AND `no_benchmark_regression` AND `timing_p99_ms < 100` AND `sun_oob_losses == 0`, `agent_v68.py` becomes the new current best → README Agents table bolded entry + Makefile `AGENT`/`RENDER_AGENT` updated (FR-012). Otherwise, all candidate toggles stay `False` (`agent_v68 ≡ agent_v64`), `agent_v64` stays bolded as current best, and the discarded candidates are documented with measured win rates (FR-013) — same precedent as `agent_v65`/`agent_v67`.

**Edge case (benchmark regression)**: if a candidate passes self-play (≥52%) but `no_benchmark_regression` is `False`, prefer the configuration that does not regress against the tougher opponent and flag the divergence (Edge Cases / SC-005).
