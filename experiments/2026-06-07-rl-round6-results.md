# Round 6: RL Training Experiments

**Date**: 2026-06-07 | **Branch**: 026-rl-training

## Summary

Two training runs with PPO (MLX/Apple Silicon) vs agent_v64:

1. **Run 1 (curriculum)**: 500 episodes — random (0-200) → agent_v64 (200-500)
2. **Run 2 (no-curriculum)**: ~3800 episodes — all vs agent_v64
3. **Run 3 (extended)**: +~200 episodes vs agent_v64 (to ep 4084)

## Results

| Run | Episodes | Opponent | Win Rate vs v65 | Avg Reward vs v64 | Avg Steps vs v64 |
|-----|----------|----------|-----------------|------------------|-----------------|
| 1 | 500 | random → v64 | 0% | +7.2 | 181 |
| 2 | ~1600 | v64 only | 0% | +6.7 | 175 |
| 3 | ~3800 | v64 only | 0% | +6.6 | 174 |

## Analysis

**No statistically significant improvement detected across all 4800 v64-only episodes.**

- Reward: consistently 6.5-7.2 across all buckets (flat)
- Step count: consistently 172-181 across all buckets (flat)
- Long games (300+ steps): ~9.4% of episodes
- Full games (499 steps): ~4.0% of episodes

One cherry-picked episode (4082) showed 499 steps with +45 reward, but this is an outlier within the noise.

## Diagnosis

**Verdict: PPO with current setup is not viable against v64 without significant changes.**

Likely causes:
1. **Reward signal too weak**: Per-turn capture+production+ship deltas against a strong opponent provide little signal. The terminal win/loss reward (+1/-1) happens too rarely (4% of episodes reach full length) and is too sparse.
2. **Network capacity**: 2×256 MLP (207K params) may be insufficient for the complex spatiotemporal reasoning required.
3. **Action space difficulty**: 12×12×4 = 576 discrete actions, but most are invalid (masked away), complicating exploration.
4. **v64 is too strong**: It uses sophisticated heuristics refined over 64 iterations. Vanilla PPO needs orders of magnitude more compute to match this.

## Recommendations

1. **Increase network size**: Try 3×512 or 4×256 MLP
2. **Adjust PPO hyperparameters**: Higher LR, more epochs, larger batch
3. **Reward shaping**: Add terminal reward shaping (scaled by game length), reduce per-turn noise
4. **Opponent curriculum**: Step down from weaker opponents (e.g., v38 → v50 → v60 → v64)
5. **Sparsify action space**: Reduce MAX_PLANETS from 12 to match actual planet count (usually 8-10)
6. **Try longer training**: 50K+ episodes may be necessary
7. **Consider on-policy alternatives**: PPO may not be the best choice for this domain

## Status

**DISCARDED** — Current approach not viable as-is.
