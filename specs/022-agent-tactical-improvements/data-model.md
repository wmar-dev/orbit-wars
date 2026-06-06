# Data Model: Agent Tactical Improvements

**Date**: 2026-06-06 | **Branch**: `022-agent-tactical-improvements`

## Modified Entities

### Garrison Floor Computation

The garrison floor determines how many ships a planet must retain before it can dispatch.

**Current (v60)**:
```
gff = 1.0 + 3.0 × min(step / 300.0, 1.0)        # ramps 1.0 → 4.0 over 300 turns
floor = max(mine.production × gff, incoming + buffer)
buffer = mine.production × 2 if incoming > 0 else 0
```

**New (v61, DYNAMIC_GARRISON_ENABLED)**:
```
gff = 1.0 + 1.5 × min(step / 400.0, 1.0)         # ramps 1.0 → 2.5 over 400 turns
floor = max(mine.production × gff, incoming + buffer)
buffer = mine.production × 2 if incoming > 0 else 0
```

Key changes:
- Max garrison multiplier: 4× → 2.5×
- Ramp window: 300 turns → 400 turns (slower increase)
- Threat buffer logic: unchanged (still fires only when enemy fleet detected)

---

### Early-Dispatch State

New state tracked within a single call to `_greedy_moves` in turns 0–15:

| Field | Type | Description |
|-------|------|-------------|
| `early_claimed` | `set[int]` | Planet IDs claimed by the early-dispatch path this turn |
| `early_dispatched` | `set[int]` | Mine planet IDs that already dispatched via early path |

Both sets are local to a single `_greedy_moves` call (not persisted across turns). Mines in `early_dispatched` are skipped by the main dispatch loop. Targets in `early_claimed` are excluded from further candidates in both the early and main loops.

**Fleet sizing formula for early dispatch**:
```
travel_turns = hypot(x_pred - mine.x, y_pred - mine.y) / fleet_speed(needed)
needed = t.ships + int(t.production × travel_turns) + 1
```
This is the same formula used by `_enemy_fleet_size` for neutral planets, applied before the main loop.

---

### Forward Simulation Score Function

Two scoring modes, selected at beam-search call time:

**Horizon-only (v60, default when WEIGHTED_EVAL_ENABLED=False)**:
```
score = state.score(player, TRANSIT_WEIGHT)    # called once at depth horizon
```

**Cumulative (v61, WEIGHTED_EVAL_ENABLED=True)**:
```
total_score = Σ state.score(player, TRANSIT_WEIGHT) over each step
```

`_SimState.score()` is unchanged:
```python
def score(self, player, transit_weight):
    own_prod = Σ p.production for p in planets if p.owner == player
    opp_prod = Σ p.production for p in planets if 0 <= p.owner != player
    own_transit = Σ f.ships for f in fleets if f.owner == player
    opp_transit = Σ f.ships for f in fleets if 0 <= f.owner != player
    return (own_prod - opp_prod) + transit_weight × (own_transit - opp_transit)
```

The change is in the beam search loop: `score = sum(state.score(player, TRANSIT_WEIGHT) for each step)` replaces `score = state.score(player, TRANSIT_WEIGHT)` called once at the end.

---

## Unchanged Entities

| Entity | Status | Notes |
|--------|--------|-------|
| `_SimPlanet` | Unchanged | Same fields: id, owner, ships, production |
| `_SimFleet` | Unchanged | Same fields: owner, target_id, ships, eta |
| `_SimState.step()` | Unchanged | Production tick + fleet arrival resolution |
| `_build_sim_state()` | Unchanged | Live obs → _SimState conversion |
| Geometry helpers | Unchanged | `_path_safe`, `_segment_dist_to_sun`, orbit lead, comet intercept |
| `_gen_beam_candidates()` | Unchanged | Alternative-target candidate generation from v60 |
| `_beam_search()` | Modified (score loop only) | Calls cumulative scorer when WEIGHTED_EVAL_ENABLED |
| `_greedy_moves()` | Modified (early-dispatch + gff) | Two additions at top and one constant change |

## Toggle Constants (top of agent_v61.py)

| Constant | Type | Default | Effect |
|----------|------|---------|--------|
| `EARLY_DISPATCH_ENABLED` | bool | `True` | Activates turns-0-15 nearest-neutral fast path |
| `EARLY_DISPATCH_WINDOW` | int | `15` | Last turn where early-dispatch applies |
| `DYNAMIC_GARRISON_ENABLED` | bool | `True` | Uses lower gff cap (2.5×) and slower ramp |
| `WEIGHTED_EVAL_ENABLED` | bool | `True` | Cumulative production score over rollout depth |
