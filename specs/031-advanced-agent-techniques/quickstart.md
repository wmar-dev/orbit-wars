# Quickstart: Advanced Agent Techniques (Round 8)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-06-13

Exact commands for each phase. All runs from repo root via `uv`. `agent_v68.py` is frozen — never edit it.

## Phase A — Replay capture + analysis (design input)

```bash
# 1. Capture >=5 fresh agent_v68 vs slawekbiel replays
uv run python record_replays.py --agent0 agent_v68.py \
  --agent1 opponent_agents/slawekbiel_agent.py --games 5 --slug slawekbiel

# 2. Run the analyze-replay skill on the captured replays to confirm/refine
#    Candidates A/B/C (see research.md R1 confirmation step).
#    -> writes experiments/2026-06-1X-round8-replay-analysis.md
```

## Phase B — Fork and implement candidates

```bash
# 3. Fork the frozen baseline (next file after agent_v68)
cp agent_v68.py agent_v69.py

# 4. Add the three toggles (committed default False) + DEEP_SEARCH_BUDGET_MS,
#    each in an isolated code region (see plan.md "Agent Architecture"):
#      GLOBAL_ALLOC_ENABLED = False   # Candidate A
#      DEEP_SEARCH_ENABLED  = False   # Candidate B
#      DEEP_SEARCH_BUDGET_MS = 700
#      REGROUP_ENABLED      = False   # Candidate C

# Sanity: all toggles False => agent_v69 must tie agent_v68 ~50/50
uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 20 --swap --jobs 4
```

## Phase C — Per-candidate evaluation (both axes)

For each candidate, set ONLY its toggle `True`, then run both axes:

```bash
# Self-play axis (pass >=52%)
uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py \
  --games 50 --swap --jobs 4

# Benchmark axis (must not regress below 0%; target >0% per SC-001)
uv run python eval.py h2h --agent0 agent_v69.py \
  --agent1 opponent_agents/slawekbiel_agent.py --games 30 --swap --jobs 4
```

Record for each: self-play %, benchmark %, p99 per-turn ms, sun losses, OOB losses.
A candidate PASSES only if self-play ≥52% AND benchmark ≥0% AND zero safety/timing violations.

### Candidate B timing check (FR-010 / SC-005)

```bash
# Verbose run to inspect per-turn timing under the wall-clock guard on a dense board
uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 3 --verbose
# Confirm every turn < DEEP_SEARCH_BUDGET_MS with fallback margin; zero forfeits.
```

## Phase C — Combination + benchmark re-verification

```bash
# 5. Enable every PASSING candidate's toggle, then re-run both axes:
uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py \
  --games 50 --swap --jobs 4        # combined self-play (adopt iff >=52%)

uv run python eval.py h2h --agent0 agent_v69.py \
  --agent1 opponent_agents/slawekbiel_agent.py --games 30 --swap --jobs 4   # combined benchmark re-check

# Optional: full opponent sweep to confirm no regression vs other downloaded agents
uv run python eval.py opponents --agent agent_v69.py --games 20
```

## Phase C — Document + adopt (only if combo beats agent_v68 ≥52%)

```bash
# 6. Write experiments/2026-06-1X-experiments-round8.md (per-candidate + combo + re-check).
# 7. On adoption (FR-013):
#    - README.md: add agent_v69 row, bold it as current best
#    - Makefile:  AGENT=agent_v69.py  RENDER_AGENT=agent_v69.py
#    - auto-memory: update the lineage note (re-verify vs v69 next round)

# Pre-submission import check (Constitution VI) if submitting:
grep -n "^from \|^import " agent_v69.py | grep -v "kaggle_environments\|math\|random\|copy\|time"
# (expect no output -> Option A self-contained)
```

If no candidate passes: keep `agent_v68` as current best, commit `agent_v69.py` with all toggles `False`
(≡ v68), and document the negative result — mirroring Rounds 5 and 7.
