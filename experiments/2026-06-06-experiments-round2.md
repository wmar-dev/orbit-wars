# Experiment: Five Tactical Improvements (agent_v62)

**Date**: 2026-06-06 | **Agent**: `agent_v62.py`

---

## Overview

Five targeted experiments built on agent_v60 (beam search, Kaggle 916.9), tested
independently vs v60 (20 games each, --swap), then best combos in 50-game evals.

---

## Individual Results (20 games, --swap, vs agent_v60)

| # | Experiment | Win Rate | Score | Verdict |
|---|-----------|----------|-------|---------|
| 1 | MULTI_DISPATCH — shared-target dispatch | 50.0% (10W/10L) | 50.0% | EVEN — no benefit |
| 2 | THREAT_BUFFER — reduced defense buffer | 40.0% (8W/12L) | 40.0% | FAIL — leaves planets exposed |
| 3 | SPLINTER_DISPATCH — send surplus to nearest neutral | 60.0% (12W/7L/1D) | 62.5% | PASS |
| 4 | EVAL_ENHANCED — planet count + ship count in eval | 65.0% (13W/7L) | 65.0% | PASS |
| 5 | OPPONENT_MODEL_V2 — position-based opponent | 40.0% (8W/12L) | 40.0% | FAIL (double-dispatch bug) |
| 5 (fixed) | OPPONENT_MODEL_V2 — no double-dispatch | 80.0% (16W/4L) | 80.0% | PASS (major) |
| 6 | DYNAMIC_GARRISON — v61 clone | 65.0% (13W/6L/1D) | 67.5% | PASS (confirmed v61 result) |

## Combined Results

| Config | Games | Win Rate | Score | vs |
|--------|-------|----------|-------|----|
| best3 (garrison + splinter + eval) | 50 | 66.0% (33W/17L) | 66.0% | v60 |
| best4 (best3 + opponent v2 fixed) | 50 | 72.0% (36W/14L) | 72.0% | v60 |
| best4 vs v61 (current best) | 50 | **70.0% (35W/15L)** | **70.0%** | **v61** |

## Opponent Sweep (best4, 20 games each, --swap)

| Opponent | W | D | L | Win% |
|----------|---|---|---|------|
| sigmaborov | 20 | 0 | 0 | 100% |
| dylanxue04 | 20 | 0 | 0 | 100% |
| yusufmurtaza | 20 | 0 | 0 | 100% |
| slawekbiel | 0 | 0 | 20 | 0% |

## Conclusions

**Keep (best4 config)**:
1. `DYNAMIC_GARRISON_ENABLED=True` — 67.5% vs v60, cap 2.5x/400t
2. `SPLINTER_DISPATCH_ENABLED=True` — 62.5% vs v60, send surplus to nearest neutral in turns 0-30
3. `EVAL_ENHANCED_ENABLED=True` — 65% vs v60, planet count + ship count in beam eval
4. `OPPONENT_MODEL_V2_ENABLED=True` — 80% vs v60 (fixed), position-based opponent in forward sim

**Discard**:
1. `MULTI_DISPATCH_ENABLED` — 50%, no improvement
2. `THREAT_BUFFER_ENABLED` — 40%, negative

**Next target**: slawekbiel (0% win rate). Likely needs deeper search or better opponent modeling.
