"""
Orbit Wars - Combined Agent (stacked passing mechanics)

Strategy: production-weighted targeting with sun-path avoidance, stacking mechanics
from isolated experiment agents that individually reached ≥55% win rate vs agent_v3.

Stacked mechanics (both passed ≥55%):
  1. Orbit-lead prediction (from agent_v4, 85% win rate) — predict orbiting planet
     positions at fleet arrival time using angular_velocity and initial_planets.
  2. Comet opportunism (from agent_v5, 55% win rate) — use precomputed comet paths
     for predicted comet positions; handle departing/evacuating comet sources.

Mechanics NOT included (failed ≥55% threshold):
  - Defensive reinforcement (agent_v6, 20% win rate) — blocked attack moves
  - Fleet-speed scoring + fast-fleet (agent_v7, 50% win rate) — did not improve

Application order: orbit-lead prediction applied to planet target positions first,
then comet path prediction applied to comet targets, then scoring and sun-avoidance check.
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
    """Return predicted (x, y) for an orbiting planet after travel_turns turns."""
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


def _build_comet_path_lookup(obs):
    """Build {planet_id: (path_list, path_index, remaining_steps)} from obs.comets."""
    lookup = {}
    comets = obs.get("comets", []) if isinstance(obs, dict) else getattr(obs, "comets", [])
    for group in comets:
        if isinstance(group, dict):
            planet_ids = group.get("planet_ids", [])
            paths = group.get("paths", [])
            path_index = group.get("path_index", 0)
            remaining_steps = group.get("remaining_steps", 0)
        else:
            planet_ids = getattr(group, "planet_ids", [])
            paths = getattr(group, "paths", [])
            path_index = getattr(group, "path_index", 0)
            remaining_steps = getattr(group, "remaining_steps", 0)
        for i, pid in enumerate(planet_ids):
            path = paths[i] if i < len(paths) else []
            lookup[pid] = (path, path_index, remaining_steps)
    return lookup


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    # Orbit-lead: build initial_planets_map
    initial_planets_map = {}
    for ip_raw in initial_planets_raw:
        ip = Planet(*ip_raw)
        initial_planets_map[ip.id] = ip

    # Comet opportunism: build comet path lookup
    comet_path_lookup = _build_comet_path_lookup(obs)
    comet_planet_ids = set(comet_path_lookup.keys())

    # Classify owned comets by departure urgency
    departing_this_turn = set()
    evacuate_next_turn = set()
    for pid, (path, path_index, remaining_steps) in comet_path_lookup.items():
        p = next((x for x in my_planets if x.id == pid), None)
        if p is None:
            continue
        if remaining_steps == 0:
            departing_this_turn.add(pid)
        elif remaining_steps == 1:
            evacuate_next_turn.add(pid)

    if not my_planets or not targets:
        return moves

    for mine in my_planets:
        # Skip owned comets departing this turn
        if mine.id in departing_this_turn:
            continue

        nearest_dist = min(
            math.hypot(t.x - mine.x, t.y - mine.y) for t in targets
        )
        max_range = nearest_dist * RANGE_FACTOR

        # Evacuate comet: dispatch ALL ships to best sun-safe target now
        if mine.id in evacuate_next_turn:
            sun_safe = [
                t for t in targets
                if _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
            ]
            if not sun_safe:
                continue
            best = max(
                sun_safe,
                key=lambda t: t.production / (math.hypot(t.x - mine.x, t.y - mine.y) + EPSILON),
            )
            if mine.ships < 1:
                continue
            angle = math.atan2(best.y - mine.y, best.x - mine.x)
            moves.append([mine.id, angle, mine.ships])
            continue

        # Build candidates with combined orbit-lead + comet path prediction
        candidates = []
        for t in targets:
            dist = math.hypot(t.x - mine.x, t.y - mine.y)
            travel_turns = dist / fleet_speed(mine.ships + 1)

            if t.id in comet_planet_ids:
                # Comet opportunism: use predicted path position
                path, path_index, remaining_steps = comet_path_lookup[t.id]
                future_idx = int(path_index + travel_turns)
                if future_idx + 5 >= len(path):
                    continue  # comet leaving soon
                pos = path[future_idx]
                if isinstance(pos, (list, tuple)):
                    x_pred, y_pred = float(pos[0]), float(pos[1])
                else:
                    x_pred, y_pred = t.x, t.y
            else:
                # Orbit-lead: predict orbiting planet position
                x_pred, y_pred = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel_turns)

            if dist <= max_range and _segment_dist_to_sun(mine.x, mine.y, x_pred, y_pred) >= SUN_EXCLUSION:
                candidates.append((t, x_pred, y_pred))

        # Fallback: any sun-safe target
        if not candidates:
            for t in targets:
                dist = math.hypot(t.x - mine.x, t.y - mine.y)
                travel_turns = dist / fleet_speed(mine.ships + 1)
                if t.id in comet_planet_ids:
                    path, path_index, remaining_steps = comet_path_lookup[t.id]
                    future_idx = int(path_index + travel_turns)
                    if future_idx + 5 >= len(path):
                        continue
                    pos = path[future_idx]
                    if isinstance(pos, (list, tuple)):
                        x_pred, y_pred = float(pos[0]), float(pos[1])
                    else:
                        x_pred, y_pred = t.x, t.y
                else:
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
