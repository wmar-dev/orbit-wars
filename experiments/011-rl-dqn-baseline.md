# Experiment: 011 — RL DQN Baseline

**Date**: 2026-05-31
**Feature**: `011-rl-optimize-agent`
**Algorithm**: DQN with Prioritized Experience Replay

## Hypothesis

DQN with prioritized replay may converge faster than PPO in wall-clock time because
experience replay lets each episode be reused multiple times — important given that
kaggle-environments simulation is the dominant time cost (~1–2 seconds/episode).
We expect ≥55% vs agent_v38 at potentially fewer wall-clock hours than PPO.

## Change

New file: `rl/dqn.py` — DQN with:

- Same 2-layer 256-unit MLP backbone as PPO, three factored Q-heads
- Prioritized experience replay (buffer=10k, α=0.6, β annealed 0.4→1.0)
- Target network (sync every 200 steps)
- ε-greedy exploration: ε=1.0→0.05 over 500 episodes
- Action masking: −1e9 on invalid Q-values before argmax

Exported via `rl/export.py` → `agent_v40.py`.

## Hyperparameters

| Parameter | Value |
|-----------|-------|
| Hidden units | 256 × 2 layers |
| Learning rate | 1e-4 |
| γ (discount) | 0.99 |
| Buffer size | 10,000 |
| Batch size | 64 |
| Target update | every 200 steps |
| ε start/end | 1.0 → 0.05 |
| ε decay | 500 episodes |
| PER α | 0.6 |
| PER β | 0.4 → 1.0 |
| Episodes | 1,000 (initial) |

## Self-Play Result

> _To be filled after evaluation_

- **Score vs agent_v38 (50 games, seed 0)**: TBD
- **Sun/OOB losses (`diagnose_v9.py`)**: TBD
- **Wall-clock time vs PPO**: TBD

## Training Curve

> _To be filled after training_

| Episode | Avg reward (last 50 eps) |
|---------|-------------------------|
| 200 | TBD |
| 500 | TBD |
| 1000 | TBD |

## Conclusion

> _To be filled after evaluation_

Pass (≥55%) / Fail (<55%). Comparison to PPO wall-clock time. Whether to submit.
