# Data Model: Experiments Round 6

This round produces decision records and experiment logs rather than runtime data structures. The "entities" below are the artifacts each phase reads or writes.

## Round6Baseline

The agent designated strongest by Phase A; the fork point for Phase C.

| Field | Type | Description |
|---|---|---|
| `agent_file` | string | One of `agent_v58.py`, `agent_v60.py`, `agent_v64.py` |
| `aggregate_record` | string | Summary of the agent's record across the 3 pairings, e.g. "2-0" or "1-1-1 (cycle)" |
| `kaggle_score` | float | From `SUBMISSIONS.md`, used as the cycle tiebreaker per Edge Cases |
| `rationale` | string | One-paragraph justification, written to `experiments/2026-06-13-round6-baseline-matrix.md` |

**Validation**: `agent_file` MUST be one of the 3 inputs to Phase A (FR-001). If the matrix is non-transitive, `rationale` MUST document the cycle and the Kaggle-score tiebreak (Edge Cases).

## WinRateMatrixEntry

One row of the Phase A round-robin.

| Field | Type | Description |
|---|---|---|
| `agent_a` | string | First agent in the pairing |
| `agent_b` | string | Second agent in the pairing |
| `games` | int | Always 50 (FR-001) |
| `agent_a_win_rate` | float | Fraction of games won by `agent_a`, `--swap` enabled |
| `notes` | string | Anomalies (timeouts, sun/OOB losses, etc.) |

**Validation**: exactly 3 entries (`v58`×`v60`, `v58`×`v64`, `v60`×`v64`), each with `games == 50`.

## CandidateDirection

A hypothesis-driven, independently-toggled tactical change identified in Phase B.

| Field | Type | Description |
|---|---|---|
| `id` | string | `candidate_1` or `candidate_2` |
| `toggle_constant` | string | The constant name added to `agent_v67.py` (e.g., `CANDIDATE_1_ENABLED`) |
| `hypothesis` | string | From the Phase B replay-analysis report |
| `predicted_effect` | string | From the Phase B replay-analysis report |
| `distinct_from_prior` | bool | Confirmed not a duplicate of mechanics in `agent_v57`–`agent_v66` (FR-004 / acceptance scenario 2) |
| `win_rate_vs_baseline` | float | Result of the 50-game `--swap` eval (FR-006) |
| `passed` | bool | `win_rate_vs_baseline >= 0.52` |

**Validation**: exactly 2 `CandidateDirection` records (FR-004); `distinct_from_prior` MUST be `true` for both before evaluation proceeds.

## ReplayAnalysisReport

The Phase B output, in the format produced by the `analyze-replay` skill.

| Field | Type | Description |
|---|---|---|
| `games_analyzed` | int | ≥5 (FR-003) |
| `win_rate` | float | `Round6Baseline` vs `slawekbiel_agent` |
| `median_divergence_turn` | int | From the skill's divergence-turn distribution |
| `behavioral_differences` | list[string] | ≥3 observed differences |
| `candidates` | list[CandidateDirection] | Exactly 2 (feeds Phase C) |

## CombinedAgent

The Phase C output if ≥1 candidate passes.

| Field | Type | Description |
|---|---|---|
| `agent_file` | string | `agent_v67.py`, with all passing candidates' toggles set to their "on" value |
| `enabled_candidates` | list[string] | IDs of `CandidateDirection` records where `passed == true` |
| `win_rate_vs_baseline` | float | Result of the confirmation 50-game `--swap` eval (FR-007) |
| `passed` | bool | `win_rate_vs_baseline >= 0.52` |
| `timing_p99_ms` | float | Must be `< 100` (SC-005) |
| `sun_oob_losses` | int | Must be `0` across all Phase C eval games (SC-005) |

**State transition**: if `CombinedAgent.passed`, `agent_v67.py` becomes the new current-best agent → README Agents table bolded entry + Makefile `AGENT`/`RENDER_AGENT` updated (FR-010). If no `CandidateDirection` passes, no `CombinedAgent` record is created, and `Round6Baseline` remains current best, with the README updated only if `Round6Baseline.agent_file != "agent_v58.py"` (FR-011).
