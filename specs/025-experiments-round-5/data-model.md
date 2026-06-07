# Data Model: Experiments Round 5

## P1 — Multi-Source Coordinated Attack

### SourcePlanet
- `id`: int — planet ID
- `x`, `y`: float — position
- `ships`: float — current ships
- `production`: float — production per turn
- `surplus`: float — ships above garrison floor
- `gff`: float — current garrison floor factor

### TargetToSources
```
{target_id: [(source_planet, ships_needed, x_pred, y_pred), ...]}
```
Built from per-source top-K target lists. Each target maps to a list of source planets that have it in their top-K.

### CombinedDispatch
- `source_ids`: (int, int) — two source planet IDs
- `target_id`: int — shared target planet ID
- `ships_needed_total`: float — combined ships needed to capture target
- `ships_from_a`, `ships_from_b`: float — per-source split
- `total_score`: float — simulated score of the combined dispatch

## P2 — Fleet-Size-Optimized Dispatch

### FleetSizeConvergence
- `initial_guess`: int — starting estimate (target.ships + 1)
- `iterations`: int — number of correction passes (max 5)
- `converged_value`: int — self-consistent fleet size
- `oversend_factor`: float — multiplier applied for distant high-production targets (1.0–1.5)
- `final_ships`: int — converged_value * oversend_factor

### SpeedCache
- `{fleet_size: speed_value}` — cache fleet_speed results to avoid recomputing log during convergence

## P3 — 4-Player State Adaptation

### OpponentState
- `count`: int — number of surviving opponents (0–3)
- `phase`: str — "ffa_4p" (3 opponents), "ffa_3p" (2 opponents), "endgame" (1 opponent)
- `conservative_mult`: float — garrison floor multiplier (1.2, 1.0, or 0.8)
- `splinter_window`: int — turns to splinter (40, 30, or 10)
- `aggressiveness`: str — "defensive", "balanced", or "aggressive"

## Shared State Across All Experiments

### Feature Toggles (constants in agent_v65.py)
```python
MULTI_SOURCE_ENABLED      = True   # P1
FLEET_SIZE_OPT_ENABLED    = True   # P2
FFA_ADAPT_ENABLED         = True   # P3
```

### Communication Patterns
- **P1 → Beam Search**: Extra candidate tuples added to `_gen_beam_candidates` return value
- **P2 → Greedy Dispatch**: Modified `_enemy_fleet_size` and neutral capture sizing
- **P3 → Greedy Dispatch**: Modified `gff` computation and `SPLINTER_WINDOW` in `_greedy_moves`
