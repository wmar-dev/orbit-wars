# Data Model: RL Training

## PolicyNet (MLX neural network)

- **Input**: 319-dim float32 vector (observation encoding)
- **Hidden layers**: 2 × Linear(256) with ReLU activation
- **Output heads**:
  - `actor_src`: Linear(256, 12) → source planet logits
  - `actor_tgt`: Linear(256, 12) → target planet logits
  - `actor_frac`: Linear(256, 4) → ship fraction logits (25/50/75/100%)
  - `critic`: Linear(256, 1) → state value
- **Weight count**: ~207K parameters

## Observation Vector (319-dim float32)

| Offset | Length | Content |
|--------|--------|---------|
| 0 | 84 | 12 planet slots × 7 features each |
| 84 | 150 | 30 fleet slots × 5 features each |
| 234 | 30 | 10 comet slots × 3 features each |
| 264 | 3 | Global features (player_id, angular_velocity, step) |
| 267 | 52 | Action mask bits (float32 0/1) |

### Planet features (per slot): owner_self, owner_enemy, owner_neutral, x/100, y/100, ships/500, production/10

### Fleet features (per slot): owner_self, owner_enemy, owner_neutral, x/100, y/100

### Action mask (52 bits): bits 0-11 = source valid (owned + surplus), bits 12-23 = target valid (exists, different slot)

## Action Space (MultiDiscrete[12, 12, 4])

- action[0]: source planet slot index (0-11)
- action[1]: target planet slot index (0-11)
- action[2]: ship fraction index (0=25%, 1=50%, 2=75%, 3=100% of surplus)

## Reward Signal

- **Per-turn**: weighted blend of capture bonus + production delta + ship delta (clipped to [-1, 1])
- **Terminal**: win = +1.0, loss = -1.0, draw = 0.0 (for 2-player)
- **Weights**: capture 0.5, production 0.3, ships 0.2

## Checkpoint File (NPZ format)

- Keys: `{layer_name}.weight` and `{layer_name}.bias` for each of fc1, fc2, actor_src, actor_tgt, actor_frac, critic
- Metadata: `__episode__` (int), `__score__` (float)
- Typical size: ~620 KB

## Training Log (CSV)

Columns: episode, ep_reward, ep_steps, elapsed_s, opponent
