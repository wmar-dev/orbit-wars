# Data Model: Agent Experiments Round 3

## Toggle Constants (agent_v63.py)

All experiments are controlled by boolean constants at the top of the agent file. Toggle isolation allows independent A/B testing.

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `DEFENSE_INTERCEPT_ENABLED` | bool | `True` | Inherited from v62. When enabled, runs interceptor pre-pass in `_greedy_moves()` |
| `WEIGHTED_EVAL_FIXED_ENABLED` | bool | `True` | New. Accumulates production differential turn-by-turn in beam eval; transit weight at horizon only |
| `SEARCH_DEPTH` | int | `10` | Existing. Tunable for deeper search experiment (test at 15, 20) |
| `BEAM_K` | int | `3` | Existing. Tunable for wider beam experiment (test at 5) |

## Sub-parameters

| Constant | Type | Default | Description |
|----------|------|---------|-------------|
| `INTERCEPT_MIN_THREAT_RATIO` | float | `1.2` | Only intercept if fleet.ships > garrison × this ratio |
| `INTERCEPT_MIN_PROD` | float | `3.0` | Only defend planets with production >= this |

## Experiment Results Schema

Results recorded in `experiments/2026-06-06-experiments-round3.md`:

```markdown
# Experiment: Agent Experiments Round 3

**Date**: 2026-06-06 | **Branch**: `023-agent-experiments-round-3` | **Agent**: `agent_v63.py`

---

## Baseline

- **Agent**: agent_v62.py (frozen)
- **Self-play baseline**: 50 games, --swap vs ... (verify parity)

---

## Direction 1: Defense Interceptor

- **Hypothesis**: [from spec]
- **Change**: DEFENSE_INTERCEPT_ENABLED=True vs False (rest same)
- **Self-play result**: [W/L/D, win rate]
- **Conclusion**: KEEP / DISCARD

---

## Direction 2: Deep Search

- **Hypothesis**: [from spec]
- **Change**: SEARCH_DEPTH=15, BEAM_K=3
- **Timing**: p50=Xms, p95=Xms, p99=Xms
- **Self-play result**: [W/L/D, win rate vs v62]
- **Conclusion**: KEEP / DISCARD

---

## Direction 3: Corrected Weighted Eval

- **Hypothesis**: [from spec]
- **Change**: WEIGHTED_EVAL_FIXED_ENABLED=True (others same as v62)
- **Self-play result**: [W/L/D, win rate vs v62]
- **Conclusion**: KEEP / DISCARD

---

## Combined Configuration

- **Change**: All passing experiments enabled
- **Self-play result**: [W/L/D, win rate vs v62]
- **Opponent sweep**: [table of results]
- **Kaggle submission**: [score, if submitted]
```

## Timing Metrics

Per-turn timing collected as p50/p95/p99 over all turns of all eval games:

| Metric | Target | Description |
|--------|--------|-------------|
| p50 | — | Median per-turn time |
| p95 | < 780ms | 95th percentile (budget headroom) |
| p99 | < 800ms | 99th percentile (must not exceed budget) |

## Key Entities

- **agent_v62.py**: Frozen baseline agent (current best, 70% vs v61). Never modified during this round.
- **agent_v63.py**: Experimental agent. Copy of v62 plus new experiment toggles. Generated at start of T001.
- **Experiment log**: Markdown file in `experiments/` recording hypothesis, change, result, and conclusion for each direction.
