# Data Model: RL Full Observation

## FullObservation (560-dim float32)

### Planet Slots (40 × 7 = 280)
| Offset | Feature | Scale |
|--------|---------|-------|
| +0 | owner_self (1 if owned by player) | 0/1 |
| +1 | owner_enemy (1 if owned by another player) | 0/1 |
| +2 | owner_neutral (1 if owner=-1) | 0/1 |
| +3 | x / 100.0 | 0..1 |
| +4 | y / 100.0 | 0..1 |
| +5 | ships / 500.0 | 0..1 |
| +6 | production / 10.0 | 0..0.5 |

Sorted by angle from center, then by distance from center (static planets first, then orbiting).

### Fleet Hot Slots (8 × 5 = 40)
First 8 fleets sorted by distance from player's centroid.
| Offset | Feature | Scale |
|--------|---------|-------|
| +0 | owner_self | 0/1 |
| +1 | owner_enemy | 0/1 |
| +2 | owner_neutral | 0/1 |
| +3 | x / 100.0 | 0..1 |
| +4 | y / 100.0 | 0..1 |

### Fleet Summary Slots (42 × 3 = 126)
14 distance bins × 3 owners. Each bin: (total_ships / 500.0, avg_angle_sin, avg_angle_cos).

### Comet Slots (10 × 3 = 30)
| Offset | Feature | Scale |
|--------|---------|-------|
| +0 | x / 100.0 | 0..1 |
| +1 | y / 100.0 | 0..1 |
| +2 | ships / 500.0 | 0..1 |

### Globals (4)
| Offset | Feature | Scale |
|--------|---------|-------|
| +0 | player_id / 3.0 | 0..1 |
| +1 | angular_velocity × 10.0 | -0.5..0.5 |
| +2 | step / 200.0 | 0..2.5 |
| +3 | planet_count / 40.0 | 0..1 |

### Action Mask (80)
| Offset | Bits | Meaning |
|--------|------|---------|
| 0-39 | 40 | Source-valid: planet is owned AND has surplus ships after garrison floor |
| 40-79 | 40 | Target-valid: slot is occupied by any planet |

## MultiFleetAction (5 × MultiDiscrete[40, 40, 4])

Each of 5 fleet slots independently chooses:
- **source**: Planet slot index (0-39). Dropped if same as target, not owned, or already used by another slot.
- **target**: Target planet slot index (0-39). Must differ from source.
- **fraction**: 0=25%, 1=50%, 2=75%, 3=100% of surplus ships.

**Total discrete options**: 5 × (40 × 40 × 4) = 5 × 6400, implemented as 5 × 3 independent logit vectors.

## PolicyNet (MLX neural network)

- **Input**: 560-dim float32
- **Hidden layers**: 2 × Linear(256) with ReLU
- **Output heads**:
  - `actor_src_{i}`: 5 heads × Linear(256, 40) → source logits for fleet slot i
  - `actor_tgt_{i}`: 5 heads × Linear(256, 40) → target logits for fleet slot i
  - `actor_frac_{i}`: 5 heads × Linear(256, 4) → fraction logits for fleet slot i
  - `critic`: Linear(256, 1) → state value
- **Weight count**: ~(560×256 + 256×256 + 5×(256×40 + 256×40 + 256×4) + 256) ≈ 370K params (up from 207K)

## Checkpoint File (NPZ format)

Same format as before, with additional layer keys for the 5× action heads:
- `actor_src_0.weight`, `actor_src_0.bias`, ... `actor_src_4.*`
- `actor_tgt_0.*`, ... `actor_tgt_4.*`
- `actor_frac_0.*`, ... `actor_frac_4.*`
