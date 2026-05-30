# Experiment: Fleet Path Safety Fix (agent_v9)

**Date**: 2026-05-30
**Agent**: agent_v9.py
**Hypothesis**: The previous sun-avoidance check in agent_v8 only tested the segment source→predicted_target, but fleets travel past the predicted position in a straight line. Fixing the check to cover the full ray to the board edge, and rejecting out-of-bounds predicted positions, should eliminate lost fleets and improve win rate.

## Bugs Fixed vs agent_v8

| Bug | Description | Fix |
|-----|-------------|-----|
| Incomplete sun check | `_segment_dist_to_sun(source, predicted_pos)` only checked up to the predicted target; fleet keeps going past it | Check full ray from source to board edge via `_ray_exits_board()` |
| Out-of-bounds predicted positions | Orbit-lead and comet path prediction can produce `(x, y)` outside `[0, 100]`; launching toward those loses the fleet immediately | Reject any predicted target with `x` or `y` outside `[0, 100]` |

Both fixes unified in `_path_safe(ox, oy, tx, ty)`, replacing all `_segment_dist_to_sun()` calls in candidate selection.

## Results

### v9 vs main.py (50 games, seeds 0–49)

| agent_v9 wins | main.py wins | Draws | Win Rate |
|---------------|--------------|-------|----------|
| 47 | 3 | 0 | **94.0%** |

### v9 vs v8 head-to-head (50 games, seeds 0–49)

| agent_v9 wins | agent_v8 wins | Draws | Win Rate |
|---------------|---------------|-------|----------|
| 35 | 14 | 1 | **70.0%** |

## Conclusion

The path safety fixes produce a meaningful improvement over agent_v8: 70% head-to-head win rate over 50 games, and 94% vs the main.py baseline. The bugs caused fleets to fly into the sun or off the board on paths aimed at orbit-predicted or comet-predicted positions that fell near the sun or near board edges. Eliminating those losses frees ships for productive attacks.

**Best agent**: agent_v9.py (70% vs agent_v8, 94% vs main.py)
