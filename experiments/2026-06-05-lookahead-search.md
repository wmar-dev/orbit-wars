# Experiment: Agent Lookahead Decision Search

**Date**: 2026-06-05 | **Branch**: `021-lookahead-search` | **Agent**: `agent_v60.py`

---

## Beam Search (depth=10, K=3)

- **Hypothesis**: Alternative-target beam search outperforms greedy by evaluating top-K targets per mine vs v58
- **Change**: `agent_v60.py` with `SEARCH_STRATEGY="beam"`, `SEARCH_DEPTH=10`, `BEAM_K=3`, `TRANSIT_WEIGHT=0.1`
- **Self-play result**: 54% vs v58 (27/50 games, 50-game eval with --swap)
- **Conclusion**: Statistical parity with v58. Key finding: only generates alternative targets for mines already dispatching in greedy; mines that greedy holds must not dispatch to cheaper targets (depletes ships for better future targets).

---

## MCTS Search (depth=10, K=3, C=1.41)

- **Hypothesis**: UCB1 MCTS with simplified greedy rollout finds better action sets than beam
- **Change**: `agent_v60.py` with `SEARCH_STRATEGY="mcts"`, `SEARCH_DEPTH=10`, `MCTS_C=1.41`
- **Self-play result**: 54% vs v58 (27/50 games, 50-game eval with --swap)
- **Conclusion**: Identical to beam search. With deterministic simulation, MCTS converges after one visit per candidate (UCB1 ordering irrelevant). No advantage over beam.

---

## N-ply Search (depth=10, beam_width=8)

- **Hypothesis**: Depth-limited exhaustive search with beam pruning finds globally optimal first-turn action
- **Change**: `agent_v60.py` with `SEARCH_STRATEGY="nply"`, `SEARCH_DEPTH=10`, `NPLY_BEAM_WIDTH=8`
- **Self-play result**: 38% vs v58 (19/50 games, 50-game eval with --swap)
- **Conclusion**: Significantly worse than beam. Multi-mine combinations (cross-product) amplify simulation optimism bias — two "looks good" alternatives stack, producing unrealistic scenarios. Single-mine redirections (beam) are more robust.

---

## Algorithm Comparison Summary

| Strategy | Win Rate vs v58 (50 games) | Conclusion |
|----------|---------------------------|------------|
| beam     | 54%                       | Best; statistical parity/slight edge vs v58 |
| mcts     | 54%                       | Equivalent to beam (deterministic sim) |
| nply     | 38%                       | Worse; multi-mine combinations over-exploit |

**Best strategy**: beam

---

## Depth Sensitivity Study (US2)

**Strategy**: beam | **Games per depth**: 20

| SEARCH_DEPTH | Win Rate vs v58 | Timeout? | Notes |
|-------------|-----------------|----------|-------|
| 5           | 40%             | No       | Too shallow; can't distinguish moves |
| 10          | 50%             | No       | Best balance of lookahead and accuracy |
| 15          | 35%             | No       | Deeper simulation accumulates optimism bias |
| 20          | 25%             | No       | Compounding optimism bias; clearly worse |

**Optimal depth**: 10 — monotonic degradation beyond depth=10 without opponent model

---

## Opponent Model Study (US3)

**Strategy + Depth**: beam, depth=10

| OPPONENT_MODEL | Win Rate vs v58 (20 games) | Notes |
|----------------|---------------------------|-------|
| False          | 50%                       | control group |
| True           | 50%                       | No benefit; approximate impl adds only noise |

**Best setting**: False — opponent model uses planet ID as distance proxy (wrong); adds noise without benefit.

---

## Final Configuration

```python
SEARCH_STRATEGY   = "beam"
SEARCH_DEPTH      = 10
TRANSIT_WEIGHT    = 0.1
OPPONENT_MODEL    = False
```

**Final 50-game eval vs v58**: 54% (27/50, beam, depth=10, TRANSIT_WEIGHT=0.1, OPPONENT_MODEL=False)

**Kaggle submission score**: TBD
