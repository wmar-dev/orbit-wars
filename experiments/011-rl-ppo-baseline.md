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
| --------- | ----- |
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

- **Score vs agent_v38 (50 games)**: **0%** (0 wins, 0 draws, 50 losses) — FAIL
- **Score vs main.py (20 games)**: 25% — agent is learning but weak
- **Sun/OOB losses**: Not yet audited (unnecessary given 0% win rate)
- **Training time**: ~23 minutes (1,000 episodes, CPU)

## Training Curve

| Episode | Sample reward | Opponent |
| ------- | ------------- | -------- |
| 0 | +25.98 | random |
| 194 | +2.22 | random |
| 294 | +37.12 | agent_v38 |
| 494 | +0.86 | agent_v38 |
| 894 | +10.94 | self-play |
| 994 | +33.34 | self-play |
| **Last 10 avg** | **+36.90** | self-play |

## Conclusion

**FAIL** — 0% score vs agent_v38 after 1,000 episodes.

The agent learned some structure (can beat main.py 25% of the time, reward increased during self-play) but is not yet competitive against agent_v38. Root cause: 1,000 episodes is insufficient for an MLP policy to overcome a well-tuned heuristic agent. The reward signal is per-turn (not sparse), so credit assignment is not the issue.

**Recommendation**: Extend to 5,000–10,000 episodes. The reward curve shows active learning during self-play (ep 800–1000), suggesting more training will continue to improve the policy. Do not submit this checkpoint. Re-evaluate after extended training.
