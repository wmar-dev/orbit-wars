# Quickstart: RL Training

## Prerequisites

- `uv` package manager installed
- Virtual env with: `kaggle-environments`, `mlx`, `gymnasium`, `numpy`, `torch`

```bash
make install
uv pip install mlx gymnasium torch numpy
```

## Pipeline Verification

```bash
# Test PPO training 5 episodes vs random
uv run python rl/ppo.py --episodes 5 --opponent random --seed 42

# Verify resume works
uv run python rl/ppo.py --episodes 3 --resume
```

## Export Trained Policy

```bash
uv run python rl/export.py --checkpoint rl/checkpoints/ppo_best.pt --output agent_v66.py --algo ppo --verify
```

## Evaluate vs Baseline

```bash
make selfplay AGENT1=agent_v66.py AGENT2=agent_v64.py GAMES=50 SWAP=true
```

## Training Loop

```bash
# Stage 1: Train 5000 episodes vs agent_v64 (approx 20-25 min)
uv run python rl/ppo.py --episodes 5000 --opponent agent_v64.py

# Stage 2: Evaluate checkpoint every 500 episodes
for ckpt in rl/checkpoints/ppo_ep*.pt; do
  echo "=== Evaluating $ckpt ==="
  uv run python rl/export.py --checkpoint "$ckpt" --output /tmp/rl_agent.py --algo ppo --quiet
  make eval AGENT1=/tmp/rl_agent.py AGENT2=agent_v64.py GAMES=20
done

# Stage 3: Resume with self-play escalation
uv run python rl/ppo.py --episodes 10000 --opponent agent_v64.py --resume
```

## Key Files

| File | Purpose |
|------|---------|
| `rl/ppo.py` | PPO training script |
| `rl/obs.py` | Observation encoder + action decoder |
| `rl/env.py` | Gymnasium environment wrapper |
| `rl/export.py` | Export policy to standalone agent |
| `rl/checkpoints/` | Trained policy weights |
| `rl/logs/ppo_train.csv` | Training metrics log |
