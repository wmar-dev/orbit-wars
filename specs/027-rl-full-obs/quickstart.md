# Quickstart: RL Full Observation

## Verify Observation Encoding

```bash
# Test that 40 planets fit in the observation vector
uv run python -c "
from rl.obs import OBS_SIZE, MAX_PLANETS
print(f'Observation size: {OBS_SIZE}')
print(f'Max planets: {MAX_PLANETS}')
assert OBS_SIZE == 560, f'Expected 560, got {OBS_SIZE}'
assert MAX_PLANETS == 40
print('OK')
"
```

## Train

```bash
# Short test: 20 episodes vs v64 to verify pipeline
uv run python rl/ppo.py --episodes 20 --opponent agent_v64.py --no-curriculum

# Full training: 5000 episodes vs v64
uv run python rl/ppo.py --episodes 5000 --opponent agent_v64.py --no-curriculum
```

## Evaluate

```bash
make eval-rl AGENT=agent_v64.py GAMES=50
```

## Export

```bash
uv run python rl/export.py --checkpoint rl/checkpoints/ppo_best.pt --output agent_v66.py --algo ppo --verify
```
