# Research: RL Full Observation

## Key Decisions

### Observation Size: 644 floats (up from 319)

| Component | Slots | Features | Total | Notes |
|-----------|-------|----------|-------|-------|
| Planets | 40 | 7 | 280 | owner_self, owner_enemy, owner_neutral, x/100, y/100, ships/500, production/10 |
| Fleet hot | 8 | 5 | 40 | Closest 8 fleets regardless of owner |
| Fleet summary | 42 | 3 | 126 | Binned by distance + owner: 3 owners × 14 distance bins (ships + avg angle) |
| Comets | 10 | 3 | 30 | x/100, y/100, ships/500 |
| Globals | 4 | 1 | 4 | player_id/3, angular_velocity×10, step/200, planet_count/40 |
| Action mask | 80 | 1 | 80 | Bits 0-39 source-valid, bits 40-79 target-valid |
| **Total** | | | **560** | |

**Rationale**: Pure slot-based encoding with 40 planets and 50 fleets would produce 40×7 + 50×5 = 530 just for planets+fleets. The fleet-hot approach preserves the most critical (closest) fleets individually while summarizing distant ones statistically — a common approach in RL for variable-size entity sets. This keeps the total manageable at 560.

### Multi-Fleet Action: 5 × 3 independent heads

Each of 5 fleet slots has: source_logits (40), target_logits (40), frac_logits (4). Total: 5 × 84 = 420 output logits.

**Implementation**: PolicyNet gets 5 actor_src heads, 5 actor_tgt heads, 5 actor_frac heads. Each fleet slot's action is sampled independently. Invalid actions (source=target, source not owned) are silently dropped.

**Constraint**: At most one fleet per source planet per turn (FR-007).

### Planet Type Flag

Add an 8th planet feature: `is_orbiting` (0.0 for static, 1.0 for orbiting). Determined by checking if `orbital_radius + planet_radius < 50` using `initial_planets` positions. Falls back to static if `initial_planets` not available.

### Comet Path Prediction

Instead of encoding raw paths, encode the next 2 waypoints relative to current comet position as (dx1, dy1, dx2, dy2) in 4 additional comet features. Total comet features: 7 (x, y, ships, dx1, dy1, dx2, dy2).

### Files Changed

| File | Changes |
|------|---------|
| `rl/obs.py` | MAX_PLANETS=40, MAX_FLEETS=50, OBS_SIZE recalc, fleet-hot + fleet-summary encoding, planet_type flag, comet deltas |
| `rl/ppo.py` | PolicyNet input 560, 5× action heads, action masking for 5 fleets |
| `rl/env.py` | Action space → 5 × MultiDiscrete([40, 40, 4]), step() decodes 5 fleets |
| `rl/export.py` | NumPy forward pass with 5× action heads, inlined _encode updated |
| `Makefile` | eval-rl target preserved |

### Export Compatibility

The `.pt` checkpoint format is preserved. The numpy forward pass in export.py is updated to output 5×3 logit vectors. The agent template's `_encode` and `_forward` are updated to match new OBS_SIZE and multi-fleet structure.

### Training Viability

The previous round showed 0% vs v64 with 319-dim obs and single-fleet action. The two changes here address the identified bottlenecks:
1. **Full observation** → agent sees all planets, cannot be blindsided by unseen territory
2. **Multi-fleet dispatch** → agent can execute multi-pronged attacks matching heuristic throughput

Expected improvement: Even a random multi-fleet policy should occasionally stumble into effective strategies by chance, creating a learning signal the old single-fleet approach never had.

### Risk: Action Space Size

5 × 40 × 40 × 4 = 32,000 discrete actions per fleet slot. With 5 slots, the naive combinatorial space is enormous. The independent sampling (each slot chooses ignoring other slots) keeps the effective per-step decisions at 5 × 1600 = 8000 logits, which is manageable for a 256-unit MLP.

### Risk: Fleet Redundancy

Multiple fleet slots may target the same planet or the same source. The constraint "at most one fleet per source" (FR-007) is enforced post-sampling by zeroing duplicate sources. This is a training signal problem — the agent must learn not to waste slots.
