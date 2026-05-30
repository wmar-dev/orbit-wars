"""
Orbit Wars - Fleet-Speed Scoring + Fast-Fleet Agent

Strategy: production-weighted targeting with sun-path avoidance + fleet-speed scoring
and minimum fast-fleet send.

Extends agent_v3 with two improvements:
1. Score targets by production / travel_turns (not raw distance), where travel_turns
   accounts for fleet speed — larger fleets reach farther planets faster, making
   high-production distant planets score better when we have a large garrison.
2. Always send at least MIN_FAST_FLEET=10 ships, so fleets travel at ~2× speed
   compared to a 1-ship crawl.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0
MIN_FAST_FLEET = 10

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


def fleet_speed(n):
    """Fleet speed formula from CONTEST.md."""
    if n <= 0:
        return 1.0
    return 1.0 + 5.0 * (math.log(n) / math.log(1000)) ** 1.5


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

        candidates = [
            t for t in targets
            if math.hypot(t.x - mine.x, t.y - mine.y) <= max_range
            and _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
        ]

        if not candidates:
            candidates = [
                t for t in targets
                if _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
            ]

        if not candidates:
            continue

        # Score by production / travel_turns (fleet-speed-aware)
        best_target = max(
            candidates,
            key=lambda t: t.production / (
                math.hypot(t.x - mine.x, t.y - mine.y) / fleet_speed(mine.ships) + EPSILON
            ),
        )

        ships_needed = best_target.ships + 1

        # Always send at least MIN_FAST_FLEET for speed advantage
        ships_to_send = max(ships_needed, MIN_FAST_FLEET)
        ships_to_send = min(ships_to_send, mine.ships)

        if mine.ships < ships_needed:
            continue

        angle = math.atan2(best_target.y - mine.y, best_target.x - mine.x)
        moves.append([mine.id, angle, ships_to_send])

    return moves


if __name__ == "__main__":
    from kaggle_environments import make as _make

    _env = _make("orbit_wars", configuration={"seed": 42}, debug=True)
    _env.run([agent, "main.py"])
    _final = _env.steps[-1]
    for i, s in enumerate(_final):
        print(f"Player {i}: reward={s['reward']}, status={s['status']}")
