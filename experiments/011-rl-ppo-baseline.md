# Experiment: 011 — RL PPO Baseline

**Date**: 2026-05-31
**Feature**: `011-rl-optimize-agent`
**Algorithm**: PPO (Proximal Policy Optimization)

## Hypothesis

A PPO agent trained via self-play against agent_v38 will learn to exploit structural weaknesses in the heuristic agent — specifically timing of fleet dispatches and garrison management — that hand-coded rules cannot easily encode. We expect ≥55% score vs agent_v38 after 1,000 episodes, with scores improving further toward 5,000 episodes.

## Change

New file: `rl/ppo.py` — CleanRL-style PPO with:

- Shared 2-layer 256-unit MLP backbone
- Three independent actor heads: source planet (12), target planet (12), ship fraction (5)
- Action masking: −1e9 on invalid source/target logits
- GAE (γ=0.99, λ=0.95), clip ε=0.2, 4 epochs per rollout, batch size 64
- Staged opponent schedule: random (0–200), agent_v38 (200–500), 50/50 self-play (500+)

Exported via `rl/export.py` → `agent_v39.py` (numpy inference, no torch at runtime).

## Hyperparameters

| Parameter | Value |
|-----------|-------|
| Hidden units | 256 × 2 layers |
| Learning rate | 3e-4 |
| γ (discount) | 0.99 |
| λ (GAE) | 0.95 |
| PPO clip ε | 0.2 |
| Entropy coef | 0.01 |
| Value coef | 0.5 |
| Rollout steps | 512 |
| Batch size | 64 |
| Epochs/update | 4 |
| Episodes | 1,000 (initial) |

## Self-Play Result

> _To be filled after evaluation_

- **Score vs agent_v38 (50 games, seed 0)**: TBD
- **Sun/OOB losses (`diagnose_v9.py`)**: TBD
- **Training time**: TBD

## Training Curve

> _To be filled after training_

| Episode | Avg reward (last 50 eps) |
|---------|-------------------------|
| 200 | TBD |
| 500 | TBD |
| 1000 | TBD |

## Conclusion

> _To be filled after evaluation_

Pass (≥55%) / Fail (<55%). What was learned. Whether to submit or extend training.
