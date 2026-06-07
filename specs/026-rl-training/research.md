# Research: RL Training

## Pipeline Status

### What Works
- **PPO training** (`rl/ppo.py`): Compiles, runs, produces checkpoints. Tested 5 episodes vs random.
- **Checkpoints**: Saved as both `.npz` (MLX-native) and `.pt` (torch-compatible). Old checkpoints from a prior May 31 run exist up to episode 2600.
- **Resume training** (`--resume`): Loads latest checkpoint and continues correctly.
- **Export** (`rl/export.py`): Generates self-contained `agent(.py)` with inlined weights as base64 blob (~814KB). Principle VI compliant (only stdlib + numpy imports).
- **Observation encoder** (`rl/obs.py`): Produces 319-dim float32 vectors. Action decoding produces valid kaggle commands.

### Issues Found
1. **Current policy (ep 2603) loses to `random`**: The prior training run used agent_v38 as opponent and self-play. The trained policy is still weaker than the random baseline. This is expected for early-stage RL.
2. **Export expects `.pt` not `.npz`**: `export.py` uses `torch.load()` which requires the torch-serialized `.pt` file, not the MLX-native `.npz`.
3. **Reward signal is generous**: The per-turn reward averages ~+0.125 even in losing games because the capture/production/ship deltas are positive early in the game (neutral captures). This may mask whether the policy is actually improving vs dying faster.

### Training Performance
- ~2 seconds per episode (499 steps) on M-series Apple Silicon
- 1000 episodes ≈ 4-5 minutes
- RL algorithm: PPO with GAE (gamma=0.99, lambda=0.95), MLP 2×256 hidden
- Action space: MultiDiscrete([12, 12, 4]) = source slot, target slot, ship fraction (25/50/75/100%)

## Opponent Escalation Strategy

The existing `get_opponent` schedule:
- Ep 0-200: `random`
- Ep 200-500: `strong_opponent` (agent_v38)
- Ep 500+: Mix of `strong_opponent` and latest self-play checkpoint

**Decision**: Update `strong_opponent` from `agent_v38` → `agent_v64` (current best, 54% vs v63). This is the most impactful change for training strength progression.

**Rationale**: agent_v64 is significantly stronger than v38. Training against a stronger opponent forces the policy to discover more sophisticated strategies. Self-play against the latest checkpoint provides targeted improvement against the current policy's weaknesses.

## Network Architecture

Current: 2-layer MLP (319 → 256 → 256 → 3 action heads + value head)

**Decision**: Keep this architecture for initial training. It's fast enough for real-time inference and the capacity is appropriate for the problem complexity. If training plateaus, consider:
- Wider layers (319 → 512 → 512)
- Residual connections
- Observation normalization (running mean/std)

## Training Hyperparameters

| Parameter | Current Value | Notes |
|-----------|--------------|-------|
| Hidden units | 256 | Adequate for initial training |
| Gamma | 0.99 | Standard for long-horizon tasks |
| GAE lambda | 0.95 | Standard |
| PPO clip | 0.2 | Standard |
| Learning rate | 3e-4 | Standard for Adam |
| Batch size | 64 | Adequate for episode length |
| Epochs | 4 | Standard |
| Rollout steps | 512 | ~1 episode per rollout |
| Max gradient | 0.5 | Prevents gradient explosion |

**Decision**: Keep all hyperparameters at current values. Focus on opponent quality and training duration first before hyperparameter tuning.

## Evaluation Methodology

### Approach
Load the policy checkpoint → run head-to-head games vs agent_v64 using `eval.py h2h`:
1. Create an evaluation agent that loads the checkpoint and wraps it with the export agent's `agent(obs)` function
2. Run `uv run python eval.py h2h --agent0 eval_agent.py --agent1 agent_v64.py --games 50 --swap`

### Existing eval infrastructure
- `export.py` already produces a self-contained agent file
- `eval.py h2h` already supports evaluating any agent file vs any other
- No new eval code needed — the exported agent file IS the eval agent

## Export to Submission

The export pipeline already works end-to-end:
```bash
uv run python rl/export.py --checkpoint rl/checkpoints/ppo_best.pt --output agent_vNN.py --algo ppo --verify
```

This produces a self-contained Python file with no local imports. The generated `agent(obs, config=None)` function follows the kaggle submission format.

## Key Decisions Summary

1. **Opponent progression**: random (0-200) → agent_v64 (200-500+) → self-play + v64 mix (500+)
2. **Network architecture**: Keep 2×256 MLP. Expand later if plateau.
3. **Hyperparameters**: Keep current PPO defaults. Tune only after initial training plateau.
4. **Eval**: Use exported agent file directly with `eval.py h2h`.
5. **Training target**: ≥20% vs v64 after 5000 episodes, ≥40% after 20000 episodes.
