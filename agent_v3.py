"""
Orbit Wars - Sun-Aware Production-Weighted Targeting Agent

Strategy: production-weighted targeting with sun-path avoidance.

Inherits the core strategy from agent_v2: score all nearby non-owned
planets by production/distance and wait to afford the best-scored target
within striking range. Adds one filter: any fleet dispatch whose
straight-line path from source planet to target passes within
SUN_EXCLUSION units of the sun center (50, 50) is skipped. If no
sun-safe targets exist within range, the agent falls back to any
sun-safe target. If all targets cross the sun, the planet skips its turn.

Key insight over agent_v2: avoids fleet destruction from sun crossings,
which is a hard resource loss. Trade-off is slightly longer travel arcs
on some maps, which may reduce early-game aggression.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0

# Sun geometry — hardcoded constants not exposed in the observation.
_SUN_X = 50.0
_SUN_Y = 50.0
SUN_RADIUS = 10.0
SAFETY_MARGIN = 2.0
SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN  # 12.0


def _segment_dist_to_sun(ax, ay, bx, by):
    """Minimum distance from the line segment A->B to the sun center."""
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(ax - _SUN_X, ay - _SUN_Y)
    t = max(0.0, min(1.0, (((_SUN_X - ax) * dx) + ((_SUN_Y - ay) * dy)) / l2))
    return math.hypot(ax + t * dx - _SUN_X, ay + t * dy - _SUN_Y)


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
        nearest_dist = min(
            math.hypot(t.x - mine.x, t.y - mine.y) for t in targets
        )
        max_range = nearest_dist * RANGE_FACTOR

        # Candidates: within range AND sun-safe.
        candidates = [
            t for t in targets
            if math.hypot(t.x - mine.x, t.y - mine.y) <= max_range
            and _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
        ]

        # Fallback: any sun-safe target if none in range.
        if not candidates:
            candidates = [
                t for t in targets
                if _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
            ]

        # Skip this planet if all targets cross the sun.
        if not candidates:
            continue

        best_target = max(
            candidates,
            key=lambda t: t.production / (math.hypot(t.x - mine.x, t.y - mine.y) + EPSILON),
        )

        ships_needed = best_target.ships + 1
        if mine.ships < ships_needed:
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
