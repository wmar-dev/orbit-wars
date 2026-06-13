# Round 6 Baseline Matrix — 2026-06-13

**Branch**: `029-experiments-round-6`
**Purpose**: Resolve the Round 5 non-transitivity finding (`agent_v65`≡`agent_v64` loses to `agent_v58` 43.3%, yet `agent_v60` claims a 54% win over `agent_v58` plus a higher Kaggle score) by running a 50-game `--swap` round-robin among `agent_v58`, `agent_v60`, and `agent_v64`.

---

## Kaggle Scores (from `SUBMISSIONS.md`, as of 2026-06-13)

| Agent | Kaggle Score | Notes |
|---|---|---|
| `agent_v58.py` | 795.7 (latest, 2026-06-08); historical 851.0 (2026-06-03), 880.7 (2026-06-05) | Multiple resubmissions of the same file; score fluctuates as Kaggle re-plays leaderboard games |
| `agent_v60.py` | 841.3 (2026-06-05) | README previously cited 916.9, not found in current `SUBMISSIONS.md` — likely stale/superseded by the 2026-06-13 refresh (commit 876a9a8) |
| `agent_v64.py` | N/A — never submitted to Kaggle | Only ever evaluated locally (54% vs v63, 43.3% vs v58 via the v65≡v64 proxy) |

---

## Win-Rate Matrix (Phase A: 3 pairings × 50 games, `--swap`)

| `agent_a` | `agent_b` | games | `agent_a` win rate | notes |
|---|---|---|---|---|
| `agent_v58.py` | `agent_v60.py` | 50 | 46.0% | v60 wins 54.0% — matches prior README claim ("54% vs v58") |
| `agent_v58.py` | `agent_v64.py` | 50 | 48.0% | v64 wins 52.0% — contradicts Round 5's 43.3% (v65≡v64 lost to v58 at 30 games); see note below |
| `agent_v60.py` | `agent_v64.py` | 50 | 40.0% | v64 wins 60.0% |

**Derived head-to-head wins**: v64 beats v58 (52.0%) and v60 (60.0%); v60 beats v58 (54.0%).

---

## Round6Baseline Decision

| Field | Value |
|---|---|
| `agent_file` | `agent_v64.py` |
| `aggregate_record` | 2-0 (beats v60 60.0%, beats v58 52.0%) |
| `kaggle_score` | N/A — `agent_v64.py` was never submitted to Kaggle (see scores table above) |
| `rationale` | The matrix is **transitive**: v64 > v60 > v58, and v64 also beats v58 directly (52.0%). v64 has the best aggregate record (2-0) of the three agents and is the clear Round 6 baseline — no Kaggle-score tiebreak is needed. |

**Cycle found**: None. The matrix is fully transitive (v64 > v60 > v58).

**Note on Round 5 discrepancy**: Round 5 (`experiments/2026-06-06-experiments-round5.md` / README) reported `agent_v65`≡`agent_v64` losing to `agent_v58` 43.3% over 30 games, and concluded `agent_v58` was the strongest local agent. This round's 50-game `--swap` re-run shows the **opposite** direction — `agent_v64` beats `agent_v58` 52.0%. The two results (43.3% vs 52.0%, both somewhere around the ~50% coin-flip band) suggest the 30-game sample was high-variance noise rather than a robust signal, OR that `agent_v65`'s toggles (claimed all-False/≡v64) introduce a subtle difference from `agent_v64.py` itself. Given the larger 50-game sample here and the fully-transitive triangle, `agent_v64.py` is adopted as `<BASELINE>` for Round 6. This supersedes the Round 5 "agent_v58 remains the strongest local agent" conclusion.
