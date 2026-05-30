"""
Orbit Wars - Defensive Reinforcement Agent

Strategy: production-weighted targeting with sun-path avoidance + defensive reinforcement.

Extends agent_v3 by adding a defense pre-pass each turn: scan enemy fleets heading
toward owned planets, and dispatch reinforcements from nearby owned planets with surplus
ships if the threatened planet's projected garrison is insufficient.

Key change over agent_v3: before the attack loop, run a defense pre-pass that checks
every enemy fleet for heading alignment toward each owned planet, estimates arrival
strength vs. garrison, and dispatches reinforcements from the nearest surplus source.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0
SAFETY_MULTIPLIER = 10

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


def _heading_toward(fleet, planet):
    """True if fleet's heading aligns within ~18° of vector to planet (dot product > 0.95)."""
    dx, dy = planet.x - fleet.x, planet.y - fleet.y
    dist = math.hypot(dx, dy)
    if dist < 0.1:
        return True
    return (dx * math.cos(fleet.angle) + dy * math.sin(fleet.angle)) / dist > 0.95


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    if not my_planets or not targets:
        return moves

    # Track which planets have already been used as reinforcement sources this turn
    reinforced_from = set()

    # Parse enemy fleets — raw format is [id, owner, x, y, angle, ships, from_planet_id]
    from kaggle_environments.envs.orbit_wars.orbit_wars import Fleet as KFleet
    enemy_fleets = [KFleet(*f) for f in raw_fleets if f[1] != player]

    # Defense pre-pass
    for enemy_fleet in enemy_fleets:
        for threatened in my_planets:
            if not _heading_toward(enemy_fleet, threatened):
                continue
            dist_to_threatened = math.hypot(enemy_fleet.x - threatened.x, enemy_fleet.y - threatened.y)
            arrival_turns = dist_to_threatened / fleet_speed(enemy_fleet.ships)
            projected_garrison = threatened.ships + threatened.production * arrival_turns
            if enemy_fleet.ships <= projected_garrison:
                continue  # not at risk

            # Find nearest owned planet (other than threatened) with surplus
            best_source = None
            best_source_dist = float("inf")
            for source in my_planets:
                if source.id == threatened.id:
                    continue
                if source.id in reinforced_from:
                    continue
                surplus = source.ships - source.production * SAFETY_MULTIPLIER
                if surplus <= 0:
                    continue
                d = math.hypot(source.x - threatened.x, source.y - threatened.y)
                if d < best_source_dist:
                    best_source_dist = d
                    best_source = source

            if best_source is None:
                continue

            surplus = best_source.ships - best_source.production * SAFETY_MULTIPLIER
            ships_to_send = min(int(surplus), int(enemy_fleet.ships - projected_garrison) + 1)
            if ships_to_send < 1:
                continue

            angle = math.atan2(threatened.y - best_source.y, threatened.x - best_source.x)
            moves.append([best_source.id, angle, ships_to_send])
            reinforced_from.add(best_source.id)

    # Attack loop (same as agent_v3)
    for mine in my_planets:
        if mine.id in reinforced_from:
            continue  # already used for defense this turn

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
