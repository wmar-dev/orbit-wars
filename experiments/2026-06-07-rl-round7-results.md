# Round 7: Full Observation + Multi-Fleet PPO (027-rl-full-obs)

## Result
**0% win rate vs v64** (evaluated at 9200 episodes). Policy does not converge.

## Changes from Round 6
| Component | Before | After |
|-----------|--------|-------|
| MAX_PLANETS | 12 | 40 |
| OBS_SIZE | 319 | 560 |
| Fleet encoding | 30 raw slots | 8 hot + 42 summary bins |
| Action slots/turn | 1 | 5 |
| Action dimension | 3 | 15 (MultiDiscrete[40,40,4]*5) |
| Mask bits | 52 | 80 |

## Training
- **Episodes**: 9200 (all vs `agent_v64.py`, no curriculum)
- **Hardware**: Apple Silicon GPU (MLX)
- **Architecture**: Shared MLP (2 × 256, ReLU) → 5× (src, tgt, frac) heads + value
- **Hyperparams**: PPO with GAE, LR=3e-4, clip=0.2, entropy=0.01, batch=64, 4 epochs/update
- **Avg throughput**: ~24 episodes/min
- **Total wall time**: ~6.5 hours (3 consecutive runs)

## Win Rate Trend (from training blended reward, `reward > 0.5`)

| Episodes | Win% | Avg Reward |
|----------|------|------------|
| 0-499 | 9.4% | -0.818 |
| 1000-1499 | 9.4% | -0.747 |
| 2000-2499 | 10.4% | -0.751 |
| 4000-4499 | 12.4% | -0.689 |
| 6000-6499 | 14.0% | -0.644 |
| 9000-9499 | 10.5% | -0.692 |

No upward trend. Fluctuates 9-14% throughout.

## Direct Evaluation (agent_v66.py, exported from ep9200)
- vs random: 22/100 (22%)
- vs v64: 0/100 (0%)

## Analysis
1. **Observation fix helped** — blind 12-planet window was replaced with 40-planet full-board encoding, 8 nearest fleet slots, 42-bin fleet summary, 80-bit mask. Forward pass verified deterministic (0.00 max diff). Weights identical between MLX and numpy export.

2. **Multi-fleet action works** — 5 independent fleet slots per turn, each with source/target/fraction. `decode_action` drops invalid actions (same src/tgt, not owned, no surplus, duplicate source). The pipeline produces valid multi-fleet moves.

3. **But PPO doesn't converge** — The win rate stays flat at ~10% for 9200 episodes. Possible causes:
   - 2×256 MLP too small for 560-dim obs + 15-dim action
   - Blended reward signal (capture + production + ship delta) doesn't correlate with winning
   - Too much entropy (entropy coeff 0.01) prevents exploitation
   - v64 is too strong — policy never experiences winning states to learn from

4. **Compared to Round 6**: The observation+action fixes moved from 0% "win signal" to ~10%, but still far from a competitive agent. v64 dispatches 5-10 heuristic-optimized fleets/turn and reliably beats both random and RL policies.

## Candidate Next Steps
- **Reward surgery**: Terminal-only reward (win/loss), remove per-turn blending
- **Deeper network**: 3x512 or residual connections
- **Entropy annealing**: Start at 0.05, decay to 0.001
- **Behavioral cloning**: Pre-train on v64 trajectories (imitation learning)
- **Reduce learning rate**: Try 1e-4 or 3e-5
- **Curriculum**: Start vs random, switch to v64 only after reaching >80% win rate
- **Gumbel-Softmax action sampling**: Replace argmax with differentiable sampling

## Files
- `rl/ppo.py` — PPO training script with 560-dim obs, 5-fleet action
- `rl/obs.py` — Observation encoder (40 planets, 8 hot + 42 summary fleet bins)
- `rl/env.py` — Gymnasium wrapper with multi-fleet action space
- `rl/export.py` — Numpy export with 5× action heads
- `agent_v66.py` — Exported agent (ep 9200)
- `rl/checkpoints/` — MLX (.npz) and PyTorch (.pt) checkpoints (keep 5 latest)
