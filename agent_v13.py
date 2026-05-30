"""
Orbit Wars - Candidate C: Threat-Aware Defense (agent_v13)

Builds on agent_v10 (intermediate planet obstruction + orbit-lead refinement).

Mechanic added:
  Threat-aware defense — at turn start, compute incoming enemy fleet ships
  for each owned planet. If threat > planet.ships + planet.production * 5,
  dispatch reinforcement from the closest owned planet with spare ships
  (source.ships - garrison_floor > 0). At most one reinforcement dispatch
  per threatened planet per turn. Offensive logic is unchanged.

  Garrison floor for defense source evaluation: max(production * 5, 1).
  Directly addresses agent_v6's over-defense failure (see
  experiments/2026-05-29-defensive-reinforce.md) by using a strict threshold.

Evaluation result: 10% win rate vs agent_v10 (20 games, seeds 0–19) — FAIL (threshold: 55%)
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0
DEFENSE_GARRISON_FACTOR = 5   # production multiplier for defense trigger threshold
DEFENSE_FLOOR_FACTOR = 5      # garrison floor for defense source eligibility

_SUN_X = 50.0
_SUN_Y = 50.0
SUN_RADIUS = 10.0
SAFETY_MARGIN = 2.0
SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN  # 12.0
PLANET_MARGIN = 1.0
BOARD_SIZE = 100.0


def _segment_dist_to_point(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def _segment_dist_to_sun(ax, ay, bx, by):
    return _segment_dist_to_point(ax, ay, bx, by, _SUN_X, _SUN_Y)


def _ray_exits_board(ox, oy, angle):
    dx, dy = math.cos(angle), math.sin(angle)
    t_candidates = []
    if dx > 0:
        t_candidates.append((BOARD_SIZE - ox) / dx)
    elif dx < 0:
        t_candidates.append(-ox / dx)
    if dy > 0:
        t_candidates.append((BOARD_SIZE - oy) / dy)
    elif dy < 0:
        t_candidates.append(-oy / dy)
    t = min(t for t in t_candidates if t > 0)
    return ox + dx * t, oy + dy * t


def _path_safe(ox, oy, tx, ty, all_planets=None, target_id=None, source_id=None):
    if not (0 <= tx <= BOARD_SIZE and 0 <= ty <= BOARD_SIZE):
        return False
    angle = math.atan2(ty - oy, tx - ox)
    ex, ey = _ray_exits_board(ox, oy, angle)
    if _segment_dist_to_sun(ox, oy, ex, ey) < SUN_EXCLUSION:
        return False
    if all_planets:
        for p in all_planets:
            if p.id == target_id or p.id == source_id:
                continue
            clearance = p.radius + PLANET_MARGIN
            if _segment_dist_to_point(ox, oy, tx, ty, p.x, p.y) < clearance:
                return False
    return True


def fleet_speed(n):
    if n <= 0:
        return 1.0
    return 1.0 + 5.0 * (math.log(n) / math.log(1000)) ** 1.5


def _predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns):
    ip = initial_planets_map.get(planet.id)
    if ip is None:
        return planet.x, planet.y
    cx, cy = 50.0, 50.0
    orbital_radius = math.hypot(ip.x - cx, ip.y - cy)
    if orbital_radius + planet.radius >= 50.0:
        return planet.x, planet.y
    theta = math.atan2(planet.y - cy, planet.x - cx)
    theta_pred = theta + angular_velocity * travel_turns
    return cx + orbital_radius * math.cos(theta_pred), cy + orbital_radius * math.sin(theta_pred)


def _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed):
    t0 = math.hypot(t.x - mine.x, t.y - mine.y) / speed
    x1, y1 = _predict_planet_pos(t, initial_planets_map, angular_velocity, t0)
    t1 = math.hypot(x1 - mine.x, y1 - mine.y) / speed
    return _predict_planet_pos(t, initial_planets_map, angular_velocity, t1)


def _build_comet_path_lookup(obs):
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


def _comet_predicted_pos(comet_planet, comet_path_lookup, travel_turns):
    path, path_index, remaining_steps = comet_path_lookup[comet_planet.id]
    if not path:
        return comet_planet.x, comet_planet.y, False
    future_idx = min(int(path_index + travel_turns), len(path) - 1)
    if future_idx + 5 >= len(path):
        return comet_planet.x, comet_planet.y, False
    pos = path[future_idx]
    if isinstance(pos, (list, tuple)):
        return float(pos[0]), float(pos[1]), True
    return comet_planet.x, comet_planet.y, True


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    initial_planets_map = {}
    for ip_raw in initial_planets_raw:
        ip = Planet(*ip_raw)
        initial_planets_map[ip.id] = ip

    # Build threat map: sum enemy fleet ships per owned planet id.
    threat = {}
    enemy_player = 3 - player  # player is 1 or 2; enemy is the other
    for fleet in raw_fleets:
        if isinstance(fleet, dict):
            owner = fleet.get("owner", -1)
            dest_id = fleet.get("destination", -1)
            ships = fleet.get("ships", 0)
        else:
            owner = getattr(fleet, "owner", -1)
            dest_id = getattr(fleet, "destination", -1)
            ships = getattr(fleet, "ships", 0)
        if owner == enemy_player:
            threat[dest_id] = threat.get(dest_id, 0) + ships

    comet_path_lookup = _build_comet_path_lookup(obs)
    comet_planet_ids = set(comet_path_lookup.keys())

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

    # Candidate C: defense pass — dispatch reinforcements to threatened planets.
    # Track which planets have already been used as a defense source this turn.
    defense_sources_used = set()
    for threatened in my_planets:
        if threatened.id in departing_this_turn:
            continue
        incoming = threat.get(threatened.id, 0)
        threshold = threatened.ships + threatened.production * DEFENSE_GARRISON_FACTOR
        if incoming <= threshold:
            continue
        # Find closest owned planet with spare ships to send as reinforcement.
        best_source = None
        best_dist = float('inf')
        for src in my_planets:
            if src.id == threatened.id:
                continue
            if src.id in departing_this_turn:
                continue
            if src.id in defense_sources_used:
                continue
            floor = max(src.production * DEFENSE_FLOOR_FACTOR, 1)
            surplus = src.ships - floor
            if surplus <= 0:
                continue
            dist = math.hypot(src.x - threatened.x, src.y - threatened.y)
            if dist < best_dist and _path_safe(src.x, src.y, threatened.x, threatened.y, all_planets=planets, target_id=threatened.id, source_id=src.id):
                best_dist = dist
                best_source = src
        if best_source is None:
            continue
        floor = max(best_source.production * DEFENSE_FLOOR_FACTOR, 1)
        reinforce = best_source.ships - floor
        if reinforce <= 0:
            continue
        angle = math.atan2(threatened.y - best_source.y, threatened.x - best_source.x)
        moves.append([best_source.id, angle, reinforce])
        defense_sources_used.add(best_source.id)

    # Offense pass — unchanged from agent_v10.
    for mine in my_planets:
        if mine.id in departing_this_turn:
            continue
        if mine.id in defense_sources_used:
            continue  # already dispatched as defense this turn

        nearest_dist = min(
            math.hypot(t.x - mine.x, t.y - mine.y) for t in targets
        )
        max_range = nearest_dist * RANGE_FACTOR

        if mine.id in evacuate_next_turn:
            safe = [
                t for t in targets
                if _path_safe(mine.x, mine.y, t.x, t.y, all_planets=planets, target_id=t.id, source_id=mine.id)
            ]
            if not safe:
                continue
            best = max(
                safe,
                key=lambda t: t.production / (math.hypot(t.x - mine.x, t.y - mine.y) + EPSILON),
            )
            if mine.ships < 1:
                continue
            angle = math.atan2(best.y - mine.y, best.x - mine.x)
            moves.append([mine.id, angle, mine.ships])
            continue

        speed = fleet_speed(mine.ships + 1)

        candidates = []
        for t in targets:
            dist = math.hypot(t.x - mine.x, t.y - mine.y)
            travel_turns = dist / speed

            if t.id in comet_planet_ids:
                x_pred, y_pred, valid = _comet_predicted_pos(t, comet_path_lookup, travel_turns)
                if not valid:
                    continue
            else:
                x_pred, y_pred = _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed)

            if dist <= max_range and _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
                candidates.append((t, x_pred, y_pred))

        if not candidates:
            for t in targets:
                dist = math.hypot(t.x - mine.x, t.y - mine.y)
                travel_turns = dist / speed

                if t.id in comet_planet_ids:
                    x_pred, y_pred, valid = _comet_predicted_pos(t, comet_path_lookup, travel_turns)
                    if not valid:
                        continue
                else:
                    x_pred, y_pred = _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed)

                if _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
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
