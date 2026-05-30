"""
Orbit Wars - Orbit-Lead Targeting Agent

Strategy: production-weighted targeting with sun-path avoidance + orbit-lead prediction.

Extends agent_v3 by predicting where orbiting planets will be when the fleet
arrives, rather than targeting their current position. For non-orbiting (static)
planets the behavior is identical to agent_v3.

Key change over agent_v3: before computing heading angle and sun-avoidance check,
replace (t.x, t.y) with _predict_planet_pos(t, ...) which projects the planet's
orbital position forward by estimated travel time.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0

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


def _predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns):
    """Return predicted (x, y) for a planet after travel_turns turns.

    For orbiting planets, project the current angular position forward.
    For static planets, return current position unchanged.
    """
    ip = initial_planets_map.get(planet.id)
    if ip is None:
        return planet.x, planet.y
    cx, cy = 50.0, 50.0
    orbital_radius = math.hypot(ip.x - cx, ip.y - cy)
    if orbital_radius + planet.radius >= 50.0:
        return planet.x, planet.y  # static planet
    theta = math.atan2(planet.y - cy, planet.x - cx)
    theta_pred = theta + angular_velocity * travel_turns
    return cx + orbital_radius * math.cos(theta_pred), cy + orbital_radius * math.sin(theta_pred)


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    # Build initial_planets_map for orbit-lead prediction
    initial_planets_map = {}
    for ip_raw in initial_planets_raw:
        ip = Planet(*ip_raw)
        initial_planets_map[ip.id] = ip

    if not my_planets or not targets:
        return moves

    for mine in my_planets:
        nearest_dist = min(
            math.hypot(t.x - mine.x, t.y - mine.y) for t in targets
        )
        max_range = nearest_dist * RANGE_FACTOR

        # Candidates: within range AND sun-safe path to predicted position.
        candidates = []
        for t in targets:
            dist = math.hypot(t.x - mine.x, t.y - mine.y)
            if dist > max_range:
                continue
            travel_turns = dist / fleet_speed(mine.ships + 1)
            x_pred, y_pred = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel_turns)
            if _segment_dist_to_sun(mine.x, mine.y, x_pred, y_pred) >= SUN_EXCLUSION:
                candidates.append((t, x_pred, y_pred))

        # Fallback: any sun-safe target if none in range.
        if not candidates:
            for t in targets:
                dist = math.hypot(t.x - mine.x, t.y - mine.y)
                travel_turns = dist / fleet_speed(mine.ships + 1)
                x_pred, y_pred = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel_turns)
                if _segment_dist_to_sun(mine.x, mine.y, x_pred, y_pred) >= SUN_EXCLUSION:
                    candidates.append((t, x_pred, y_pred))

        if not candidates:
            continue

        best_target, bx, by = max(
            candidates,
            key=lambda item: item[0].production / (math.hypot(item[0].x - mine.x, item[0].y - mine.y) + EPSILON),
        )

        ships_needed = best_target.ships + 1
        if mine.ships < ships_needed:
            continue

        angle = math.atan2(by - mine.y, bx - mine.x)
        moves.append([mine.id, angle, ships_needed])

    return moves


if __name__ == "__main__":
    from kaggle_environments import make as _make

    _env = _make("orbit_wars", configuration={"seed": 42}, debug=True)
    _env.run([agent, "main.py"])
    _final = _env.steps[-1]
    for i, s in enumerate(_final):
        print(f"Player {i}: reward={s['reward']}, status={s['status']}")
