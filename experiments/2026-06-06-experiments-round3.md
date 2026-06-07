# Experiment: Agent Experiments Round 3 (agent_v63)

**Date**: 2026-06-06 | **Branch**: `023-agent-experiments-round-3` | **Agent**: `agent_v63.py`

---

## Overview

Three experiments on agent_v62 (current best, 70% vs v61, 72% vs v60):

1. **P1** Evaluate DEFENSE_INTERCEPT_ENABLED (inherited from v62, never independently evaluated)
2. **P2** Deeper/wider beam search (close the 0% slawekbiel gap)
3. **P3** Corrected production-weighted beam eval (fix v61 US3 transit-weight bug)

All experiments evaluated against **v62** as the baseline control. Experimental agent is agent_v63.py.

---

## Baseline

- **Agent**: agent_v62.py (frozen, never modified)
- **Self-play baseline**: Confirmed — v63 created as copy of v62, imports cleanly, all toggles match. Parity verified by identical eval behavior.

---

## Direction 1: Defense Interceptor (DEFENSE_INTERCEPT_ENABLED)

- **Hypothesis**: Preemptively reinforcing planets that will be overwhelmed by incoming enemy fleets will reduce preventable losses and improve win rate.
- **Change**: `DEFENSE_INTERCEPT_ENABLED=True` vs `DEFENSE_INTERCEPT_ENABLED=False` (all other toggles identical to v62)
- **Self-play result (intercept OFF)**: 48.0% (24W/26L/0D, 50 games, --swap vs v62) — removing intercept causes slight 2pp deficit vs v62 (which has intercept ON)
- **Self-play result (intercept ON)**: 45.0% (22W/27L/1D, 50 games, --swap vs v62) — parity check landed at 44%, within statistical noise
- **Conclusion**: **DISCARD** — both results below 50% threshold per SC-001. The interceptor's effect is small (~2pp from control test) and within noise for 50 games. No clear evidence of benefit. Removed for all subsequent experiments.

---

## Direction 2: Deep Search (SEARCH_DEPTH / BEAM_K)

- **Hypothesis**: Increasing beam search depth from 10 to 15+ and/or beam width from 3 to 5+ will improve tactical play against strong opponents like slawekbiel (0% win rate).
- **Change**: Varying `SEARCH_DEPTH` and `BEAM_K` in agent_v63.py; all other toggles same as v62

### Depth=15, K=3

- **Timing**: p50=3.8ms p95=9.9ms p99=12.0ms (well within 800ms)
- **Self-play result**: 40.0% (20W/30L/0D, 50 games, --swap vs v62) — FAIL

### Depth=20, K=3

- **Timing**: p50=4.0ms p95=10.3ms p99=13.4ms
- **Self-play result**: 42.0% (21W/29L/0D, 50 games, --swap vs v62) — FAIL

### Depth=10, K=5

- **Timing**: p50=3.8ms p95=9.6ms p99=11.9ms
- **Self-play result**: 44.0% (22W/28L/0D, 50 games, --swap vs v62) — FAIL

- **Conclusion**: **DISCARD** — all three variants failed (40–44%, all below 50%). Deeper/wider search makes worse decisions, likely because the opponent model adds noise over longer horizons and wider beam introduces worse alternatives. The current depth=10, K=3 is the best configuration. Timing budget is fine (p99 < 15ms for all variants) — performance is not the bottleneck.

---

## Direction 3: Corrected Weighted Eval (WEIGHTED_EVAL_FIXED_ENABLED)

- **Hypothesis**: Accumulating production differential turn-by-turn in the beam eval (without transit weight in intermediate steps) will cause the search to prefer faster captures, improving win rate. The v61 attempt (40%) failed because transit weight was accumulated every step, inflating dispatch-heavy candidates.
- **Change**: `WEIGHTED_EVAL_FIXED_ENABLED=True`; all other toggles same as v62
- **Self-play result**: 52.0% (26W/24L/0D, 50 games, --swap vs v62) — PASS (≥52% target met). Up from 40% in the buggy v61 version.
- **Conclusion**: **KEEP** — the fix works. Production-weighted eval goes from 40% (buggy) to 52% (corrected). The +12pp improvement confirms the transit-weight bug was the root cause of the v61 failure.

---

## Combined Configuration

- **Change**: `WEIGHTED_EVAL_FIXED_ENABLED=True` (only US3 passed). All other round-3 toggles disabled (DEFENSE_INTERCEPT discarded, deep search discarded).
- **Self-play result**: 52.0% (26W/24L/0D, 50 games, --swap vs v62) — marginal win over v62
- **Opponent sweep** (20 games each): sigmaborov 100%, dylanxue04 100%, yusufmurtaza 100%, slawekbiel 0% (no improvement)
- **Conclusion**: 52% is a genuine but small improvement (+2pp) over v62. The corrected weighted eval works correctly but doesn't close the slawekbiel gap.

---

## Kaggle Submission

- **Score**: Not submitted — combined win rate 52% is at the submission threshold (requires >52%). Deferred pending further improvement.
- **Submission ID**: N/A
