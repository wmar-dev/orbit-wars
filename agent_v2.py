"""
Orbit Wars - Production-Weighted Targeting Agent

Strategy: patient production-weighted targeting.

Score all non-owned planets by production/distance and wait to afford the
best-scored target within striking range, rather than settling for any
affordable planet right now.

Key insight over nearest-sniper: we target high-production planets even if
they require saving up a few extra turns — the production snowball is worth
the wait. The nearest-sniper grabs the cheapest/nearest planet regardless
of value.

"Striking range" is defined as a multiple of the nearest planet's distance,
so we don't wait forever for a far-away planet.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
# Consider targets within this factor of the nearest planet's distance.
# 2.0 means: if nearest is at distance 10, consider all targets within distance 20.
RANGE_FACTOR = 2.0


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    if not my_planets or not targets:
        return moves

    for mine in my_planets:
        # Distance to nearest non-owned planet (regardless of affordability).
        nearest_dist = min(
            math.hypot(t.x - mine.x, t.y - mine.y) for t in targets
        )
        max_range = nearest_dist * RANGE_FACTOR

        # Among targets within striking range, find the best production/distance score.
        candidates = [
            t for t in targets
            if math.hypot(t.x - mine.x, t.y - mine.y) <= max_range
        ]
        if not candidates:
            candidates = targets

        best_target = max(
            candidates,
            key=lambda t: t.production / (math.hypot(t.x - mine.x, t.y - mine.y) + EPSILON),
        )

        ships_needed = best_target.ships + 1
        if mine.ships < ships_needed:
            # Wait — accumulate ships to afford the best nearby target.
            continue

        angle = math.atan2(best_target.y - mine.y, best_target.x - mine.x)
        moves.append([mine.id, angle, ships_needed])

    return moves


if __name__ == "__main__":
    from kaggle_environments import make as _make

    _env = _make("orbit_wars", configuration={"seed": 42}, debug=True)
    _env.run([agent, "main.py"])
    _final = _env.steps[-1]
    for i, s in enumerate(_final):
        print(f"Player {i}: reward={s['reward']}, status={s['status']}")
    # Render in a notebook: _env.render(mode="ipython", width=800, height=600)
