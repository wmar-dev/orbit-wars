# Experiment: 011 — RL A2C Baseline (Ablation)

**Date**: 2026-05-31
**Feature**: `011-rl-optimize-agent`
**Algorithm**: A2C (Advantage Actor-Critic — PPO without clipping)

## Hypothesis

A2C is PPO with the clipping loss removed. By comparing A2C and PPO performance,
we can measure the contribution of PPO's clipping to training stability and final
win rate. If A2C scores similarly to PPO, clipping is not essential for this game
and we can simplify future implementations.

## Change

New file: `rl/a2c.py` — same architecture as PPO (`rl/ppo.py`) but:

- Loss = plain policy gradient: `−(log_prob * advantage).mean()` (no clip, no importance sampling)
- Same GAE, value loss, entropy bonus
- Same staged opponent schedule

Exported via `rl/export.py` → `agent_v41.py`.

## Hyperparameters

Same as PPO except no clip ε parameter.

| Parameter | Value |
|-----------|-------|
| Hidden units | 256 × 2 layers |
| Learning rate | 3e-4 |
| γ (discount) | 0.99 |
| λ (GAE) | 0.95 |
| Entropy coef | 0.01 |
| Value coef | 0.5 |
| Rollout steps | 512 |
| Episodes | 1,000 (initial) |

## Self-Play Result

> _To be filled after evaluation_

- **Score vs agent_v38 (50 games, seed 0)**: TBD
- **Sun/OOB losses (`diagnose_v9.py`)**: TBD
- **Score vs PPO**: TBD (ablation comparison)

## Training Curve

> _To be filled after training_

| Episode | Avg reward (last 50 eps) |
|---------|-------------------------|
| 200 | TBD |
| 500 | TBD |
| 1000 | TBD |

## Conclusion

> _To be filled after evaluation_

Pass (≥55%) / Fail. Whether PPO clipping provides measurable improvement.
Recommendation for future algorithm choices.
