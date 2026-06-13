# Phase 0 Research: Experiments Round 6

## R1: How should the Phase A (baseline) round-robin be run?

**Decision**: Run three pairings, each as a 50-game `--swap` h2h eval via `eval.py`:

```bash
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v60.py --games 50 --jobs 4 --swap
uv run python eval.py h2h --agent0 agent_v58.py --agent1 agent_v64.py --games 50 --jobs 4 --swap
uv run python eval.py h2h --agent0 agent_v60.py --agent1 agent_v64.py --games 50 --jobs 4 --swap
```

**Rationale**: This is the exact protocol used to produce the existing claims (`agent_v60`: "54% vs v58 (50 games)"; `agent_v65`≡`agent_v64`: "43.3% vs v58 (30 games)"). Re-running `v58` vs `v60` at the same 50-game sample size either confirms or contradicts the existing claim; adding `v58` vs `v64` directly (never previously run head-to-head — `v64` was only ever compared to `v63` and to `v58` via the `v65` proxy at 30 games) and `v60` vs `v64` (never previously run) completes the triangle needed to detect or rule out a non-transitive cycle.

**Alternatives considered**:
- Re-running the existing 30-game `v58` vs `v65` test at a larger sample — rejected because it doesn't address whether `v60` (which has the highest individual Kaggle score, 916.9) is actually the strongest agent; `v65`≡`v64` so this pairing is already covered by `v58` vs `v64`.
- Including `v61`–`v63`/`v65` in the matrix to fully bisect the chain — rejected as out of scope (FR-001 caps this at 3 agents / 3 pairings = 150 games); if Phase A reveals `v60` is actually strongest, a future round can bisect `v60`→`v64` separately.

**Tie-breaking rule** (per Edge Cases): if the matrix is non-transitive (e.g., A beats B, B beats C, C beats A), pick the agent with the highest `SUBMISSIONS.md` Kaggle score among the three as the Round 6 baseline, and record the cycle in `experiments/2026-06-13-round6-baseline-matrix.md` for future investigation.

---

## R2: How should Phase B (replay generation + analysis) be run?

**Decision**:
1. Generate ≥5 local games of `<BASELINE>` (winner of Phase A) vs `opponent_agents/slawekbiel_agent.py` using `kaggle_environments`, saving each game's full step history as JSON to `replays/replay_round6_<N>.json` (same shape as the existing `replays/<episode_id>.json` files, produced via `env.toJSON()` after `env.run([...])`).
2. Run the `analyze-replay` skill against `replays/replay_round6_*.json` to produce the behavioral-difference report and candidate directions, written to `experiments/YYYY-MM-DD-replay-analysis.md`.

**Rationale**: `opponent_agents/slawekbiel_agent.py` is present locally (confirmed), matching the opponent used in the most recent slawekbiel-focused analysis (`experiments/2026-06-04-replay-analysis.md`, 0/7 win rate, median divergence turn 8). The `analyze-replay` skill already implements the exact statistics (per-turn-bucket planets/ships/dispatches, divergence-turn distribution, ≥3 behavioral differences, 1–3 candidate hypotheses) required by FR-003/SC-002, so Phase B is "generate replays, then invoke the skill" rather than writing new analysis tooling.

**Alternatives considered**:
- Downloading fresh Kaggle episode replays via `make replay EPISODE_ID=<id>` — rejected because Kaggle episodes are 4-player FFA against unknown opponents, not controlled 1v1 vs `slawekbiel_agent`, making behavioral-divergence analysis noisier and non-reproducible.
- Re-using the existing `replays/*.json` files (Kaggle episode downloads, e.g. `78841780.json`) — rejected because none are confirmed to be `<BASELINE>` vs `slawekbiel_agent` specifically; FR-003 requires fresh replays of the Round 6 baseline.

**Fallback** (per Edge Cases): if `opponent_agents/slawekbiel_agent.py` is missing or broken at execution time, re-run `make opponents` to refresh `opponent_agents/`, or fall back to the Phase A runner-up as the opponent for replay generation.

---

## R3: How should Phase C (candidate implementation + eval) be run?

**Decision**: Copy `<BASELINE>.py` to `agent_v67.py` (next available version number after `agent_v66.py`, confirmed unused). For each of the 2 candidates from Phase B, add an independent toggle constant (e.g., `CANDIDATE_1_ENABLED`, `CANDIDATE_2_ENABLED`, both defaulting to the value needed for that candidate's isolated test) and gate the candidate's logic behind it. Evaluate with:

```bash
uv run python eval.py h2h --agent0 agent_v67.py --agent1 <BASELINE>.py --games 50 --jobs 4 --swap
```

run once per candidate (the other candidate's toggle off), then once more with all passing candidates enabled together (combination confirmation).

**Rationale**: Matches the toggle-constant pattern established in `agent_v61`/`agent_v62`/`agent_v65` (`EARLY_DISPATCH_ENABLED`, `DYNAMIC_GARRISON_ENABLED`, `WEIGHTED_EVAL_ENABLED`, `MULTI_SOURCE_ENABLED`, etc.) and the FR-005/FR-006/FR-007 independent-then-combined evaluation sequence used in Rounds 2–5.

**Alternatives considered**:
- Creating two separate agent files (`agent_v67.py`, `agent_v68.py`) for the two candidates instead of toggles in one file — rejected; the toggle pattern is the established convention (simplifies the combination step to "enable both toggles" rather than merging two diverged files).

---

## Resolved Unknowns

No `[NEEDS CLARIFICATION]` markers remain. The only open question — *what are the 2 candidate directions?* — is intentionally deferred to Phase B execution (it is the output of that phase, not an input to planning), as documented in plan.md's "Agent Architecture (Phase C)" section.
