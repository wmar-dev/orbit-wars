# Quickstart: Experiments Round 5 Implementation Guide

## Prerequisites

- `agent_v64.py` (baseline) exists and is stable
- Python 3.8+
- `kaggle-environments>=1.28.0`

## Step 1: Create Agent v65

```bash
cp agent_v64.py agent_v65.py
```

Update the docstring header:
```python
"""
Orbit Wars - agent_v65 (experiments round 5)

Built on agent_v64 (multi-turn skip candidates, 54% vs v63).

Experiments round 5:
  TEST   MULTI_SOURCE_ENABLED         — multi-source coordinated attacks (P1)
  TEST   FLEET_SIZE_OPT_ENABLED       — iterative fleet size convergence (P2)
  TEST   FFA_ADAPT_ENABLED            — 4-player state adaptation (P3)
"""
```

## Step 2: Add Feature Toggles

In the constants section (after v64 toggles, around line 52):

```python
# v65 Experiment toggles — set False to isolate/disable each
MULTI_SOURCE_ENABLED      = True   # P1 — multi-source coordinated attacks
FLEET_SIZE_OPT_ENABLED    = True   # P2 — iterative fleet size convergence
FFA_ADAPT_ENABLED         = True   # P3 — 4-player state adaptation
```

## Step 3: Implement P1 — Multi-Source Coordination

### 3a. Add helper function after `_compute_top_k_targets`

```python
def _build_target_to_sources_map(my_planets, targets, initial_planets_map,
                                  angular_velocity, comet_path_lookup,
                                  comet_planet_ids, planets, gff, k=BEAM_K):
    target_to_sources = {}  # target_id -> list of (mine, ships_needed, x_pred, y_pred)
    for mine in my_planets:
        surplus = mine.ships - mine.production * gff
        if surplus <= 0:
            continue
        top_k = _compute_top_k_targets(mine, targets, initial_planets_map,
                                       angular_velocity, comet_path_lookup,
                                       comet_planet_ids, planets, k=k)
        for _, t, x_pred, y_pred in top_k:
            if t.id not in target_to_sources:
                target_to_sources[t.id] = []
            ships_needed = int(t.ships) + 1 if t.owner == -1 else \
                _enemy_fleet_size(t, x_pred, y_pred, mine.x, mine.y,
                                 initial_planets_map, angular_velocity)[0]
            target_to_sources[t.id].append((mine, ships_needed, x_pred, y_pred))
    return target_to_sources
```

### 3b. Add to `_gen_beam_candidates`

After the skip candidate section (around line 865), before `candidates.append(([], []))`:

```python
if MULTI_SOURCE_ENABLED:
    target_to_sources = _build_target_to_sources_map(
        my_planets, targets, initial_planets_map, angular_velocity,
        comet_path_lookup, comet_planet_ids, planets, gff
    )
    for target_id, sources in target_to_sources.items():
        if len(sources) < 2:
            continue
        s1, ships1, x1, y1 = sources[0]
        s2, ships2, x2, y2 = sources[1]
        combined_ships = ships1 + ships2
        combined_speed = fleet_speed(combined_ships)
        tgt = planets_map.get(target_id)
        if tgt is None:
            continue
        dist1 = math.hypot(tgt.x - s1.x, tgt.y - s1.y)
        dist2 = math.hypot(tgt.x - s2.x, tgt.y - s2.y)
        eta1 = max(1, int(dist1 / combined_speed))
        eta2 = max(1, int(dist2 / combined_speed))
        d1 = (s1.id, target_id, ships1, eta1)
        d2 = (s2.id, target_id, ships2, eta2)
        angle1 = math.atan2(tgt.y - s1.y, tgt.x - s1.x)
        angle2 = math.atan2(tgt.y - s2.y, tgt.x - s2.x)
        alt_dispatches = [d for d in greedy_dispatches if d[0] not in (s1.id, s2.id)] + [d1, d2]
        alt_moves = [m for m in greedy_moves if m[0] not in (s1.id, s2.id)] + [[s1.id, angle1, ships1], [s2.id, angle2, ships2]]
        candidates.append((alt_dispatches, alt_moves))
```

## Step 4: Implement P2 — Iterative Fleet Size Convergence

### 4a. Modify `_enemy_fleet_size` to iterate until convergence

```python
def _enemy_fleet_size(t, x_pred, y_pred, mine_x, mine_y, initial_planets_map, angular_velocity):
    if not FLEET_SIZE_OPT_ENABLED:
        # Original two-pass logic (unchanged)
        ...
    
    target_prod = t.production
    target_ships = t.ships
    distance = math.hypot(x_pred - mine_x, y_pred - mine_y)
    
    ships_needed = max(1, int(target_ships) + 1)
    for _ in range(5):  # max iterations
        speed = fleet_speed(ships_needed)
        travel = distance / speed
        new_needed = int(target_ships + target_prod * travel) + 1
        if abs(new_needed - ships_needed) <= 1:
            ships_needed = new_needed
            break
        ships_needed = new_needed
    
    # Oversend for distant high-production targets
    if target_prod >= 8 and distance > 40:
        oversend = min(1.5, max(1.0, target_prod * 0.05))
        ships_needed = max(ships_needed, int(ships_needed * oversend))
    
    return ships_needed, x_pred, y_pred
```

### 4b. Fix neutral capture sizing

In `_greedy_moves`, replace:
```python
ships_needed = best_target.ships + 1
```
with:
```python
if FLEET_SIZE_OPT_ENABLED:
    ships_needed = max(1, int(best_target.ships + best_target.production * 
        (math.hypot(bx - mine.x, by - mine.y) / fleet_speed(max(1, int(best_target.ships) + 1)))) + 1)
else:
    ships_needed = best_target.ships + 1
```

## Step 5: Implement P3 — 4-Player State Adaptation

### 5a. Add opponent count helper

```python
def _count_opponents(planets, player):
    return len(set(p.owner for p in planets if 0 <= p.owner != player))
```

### 5b. Modify `_greedy_moves` garrison floor

```python
if FFA_ADAPT_ENABLED:
    opp_count = _count_opponents(planets, player)
    if opp_count >= 3:
        gff_mult = 1.2
        splinter_window = 40
    elif opp_count <= 1:
        gff_mult = 0.8
        splinter_window = 10
    else:
        gff_mult = 1.0
        splinter_window = 30
else:
    gff_mult = 1.0
    splinter_window = 30
```

The `gff` computation becomes:
```python
if DYNAMIC_GARRISON_ENABLED:
    gff = gff_mult * (1.0 + 1.5 * min(step / 400.0, 1.0) * phase_mult)
else:
    gff = gff_mult * (1.0 + 3.0 * min(step / 300.0, 1.0) * phase_mult)
```

And the existing `SPLINTER_WINDOW` reference on line 694 uses the adapted value.

## Step 6: Eval Each Experiment

Test individually (others False) vs v64:

```bash
# P1 only
python -c "
from kaggle_environments import make
env = make('orbit_wars', configuration={'seed': 42}, debug=True)
env.run(['agent_v65.py', 'agent_v64.py'])
print([(i, s.reward) for i, s in enumerate(env.steps[-1])])
"

# Automated 50-game eval:
make selfplay AGENT1=agent_v65.py AGENT2=agent_v64.py GAMES=50 SWAP=true
```

## Step 7: Combine All Passing

Set all passing toggles to True, re-eval vs v64, then run 4-player eval:

```bash
# 4-player eval: v65 vs 3 copies of v64
python -c "
from kaggle_environments import make
env = make('orbit_wars', debug=True)
env.run(['agent_v65.py', 'agent_v64.py', 'agent_v64.py', 'agent_v64.py'])
scores = [s.reward for s in env.steps[-1]]
print(f'v65: {scores[0]} / v64 avg: {sum(scores[1:])/3:.1f}')
"
```

## Step 8: Update Makefile

```makefile
AGENT = agent_v65.py
```
