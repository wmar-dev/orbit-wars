"""
Orbit Wars - Candidate L: Two-Source Coordinated Attack (agent_v24)

Builds on agent_v20 (speed-corrected orbit lead + capture-ROI scoring +
single-sender coordination + all agent_v10 safety guards).

Added mechanic:
  - Two-source coordinated attack (Candidate L): After the main single-sender
    offensive loop, adds a fallback for targets that no single owned planet can
    afford (after garrison floor). If the top-2 planets by surplus can jointly
    cover target.ships + 1, and both are within range, both dispatch their share
    (ceil(needed/2) each) aimed at the orbit-lead predicted position. Single-sender
    assignments for affordable targets are unaffected.

Hypothesis: Single-sender coordination (Candidate D) permanently skips targets
no single planet can afford. Large enemy strongholds are therefore indefinitely
unreachable. Two-source coordination can flip high-value targets that were
previously out of reach.
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

EPSILON = 1e-6
RANGE_FACTOR = 2.0
GARRISON_FLOOR_FACTOR = 5

_SUN_X = 50.0
_SUN_Y = 50.0
SUN_RADIUS = 10.0
SAFETY_MARGIN = 2.0
SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN
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


def _garrison_floor(planet):
    return max(planet.production * GARRISON_FLOOR_FACTOR, 1)


def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return t.production * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    initial_planets_map = {}
    for ip_raw in initial_planets_raw:
        ip = Planet(*ip_raw)
        initial_planets_map[ip.id] = ip

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

    best_sender = {}
    for t in targets:
        best_score = float('inf')
        best_pid = None
        for src in my_planets:
            if src.id in departing_this_turn:
                continue
            floor = _garrison_floor(src)
            surplus = src.ships - floor
            if surplus <= 0:
                continue
            dist = math.hypot(src.x - t.x, src.y - t.y)
            score = dist / max(surplus, 1)
            if score < best_score:
                best_score = score
                best_pid = src.id
        if best_pid is not None:
            best_sender[t.id] = best_pid

    # Track which planets already dispatched this turn (for two-source fallback).
    dispatched_this_turn = set()

    for mine in my_planets:
        if mine.id in departing_this_turn:
            continue

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
            dispatched_this_turn.add(mine.id)
            continue

        candidates = []
        for t in targets:
            if best_sender.get(t.id) != mine.id:
                continue
            speed_for_lead = fleet_speed(t.ships + 1)
            dist = math.hypot(t.x - mine.x, t.y - mine.y)
            travel_turns = dist / speed_for_lead
            if t.id in comet_planet_ids:
                x_pred, y_pred, valid = _comet_predicted_pos(t, comet_path_lookup, travel_turns)
                if not valid:
                    continue
            else:
                x_pred, y_pred = _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)
            if dist <= max_range and _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
                candidates.append((t, x_pred, y_pred))

        if not candidates:
            for t in targets:
                if best_sender.get(t.id) != mine.id:
                    continue
                speed_for_lead = fleet_speed(t.ships + 1)
                dist = math.hypot(t.x - mine.x, t.y - mine.y)
                travel_turns = dist / speed_for_lead
                if t.id in comet_planet_ids:
                    x_pred, y_pred, valid = _comet_predicted_pos(t, comet_path_lookup, travel_turns)
                    if not valid:
                        continue
                else:
                    x_pred, y_pred = _refined_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)
                if _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
                    candidates.append((t, x_pred, y_pred))

        if not candidates:
            continue

        best_target, bx, by = max(
            candidates,
            key=lambda item: _roi(item[0], item[1], item[2], mine),
        )

        ships_needed = best_target.ships + 1
        if mine.ships < ships_needed:
            continue

        angle = math.atan2(by - mine.y, bx - mine.x)
        moves.append([mine.id, angle, ships_needed])
        dispatched_this_turn.add(mine.id)

    # Candidate L: Two-source fallback for targets no single source can afford.
    # Find the highest-ROI target that all single sources skipped due to cost.
    available_sources = [
        p for p in my_planets
        if p.id not in departing_this_turn and p.id not in dispatched_this_turn
        and p.ships - _garrison_floor(p) > 0
    ]
    if len(available_sources) < 2 or not targets:
        return moves

    # Among targets not already being attacked, find the best two-source candidate.
    attacked_targets = {best_sender.get(t.id) and t.id for t in targets if best_sender.get(t.id) in dispatched_this_turn}

    best_joint = None
    best_joint_roi = -1.0
    for t in targets:
        if t.id in attacked_targets:
            continue
        needed = t.ships + 1
        # Check each available source pair.
        sorted_src = sorted(available_sources, key=lambda s: s.ships - _garrison_floor(s), reverse=True)
        if len(sorted_src) < 2:
            break
        s1, s2 = sorted_src[0], sorted_src[1]
        s1_surplus = s1.ships - _garrison_floor(s1)
        s2_surplus = s2.ships - _garrison_floor(s2)
        if s1_surplus + s2_surplus < needed:
            continue

        # Both must be within range of the target.
        s1_nearest = min(math.hypot(tt.x - s1.x, tt.y - s1.y) for tt in targets)
        s2_nearest = min(math.hypot(tt.x - s2.x, tt.y - s2.y) for tt in targets)
        s1_range = s1_nearest * RANGE_FACTOR
        s2_range = s2_nearest * RANGE_FACTOR
        d1 = math.hypot(t.x - s1.x, t.y - s1.y)
        d2 = math.hypot(t.x - s2.x, t.y - s2.y)
        if d1 > s1_range or d2 > s2_range:
            continue

        # Use orbit-lead predicted position from s1 (primary source).
        speed_for_lead = fleet_speed(t.ships + 1)
        if t.id in comet_planet_ids:
            x_pred, y_pred, valid = _comet_predicted_pos(t, comet_path_lookup, d1 / speed_for_lead)
            if not valid:
                continue
        else:
            x_pred, y_pred = _refined_orbit_lead(t, s1, initial_planets_map, angular_velocity, speed_for_lead)

        if not (_path_safe(s1.x, s1.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=s1.id) and
                _path_safe(s2.x, s2.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=s2.id)):
            continue

        roi = _roi(t, x_pred, y_pred, s1)
        if roi > best_joint_roi:
            best_joint_roi = roi
            best_joint = (t, x_pred, y_pred, s1, s2, needed)

    if best_joint is not None:
        t, bx, by, s1, s2, needed = best_joint
        each = math.ceil(needed / 2)
        angle1 = math.atan2(by - s1.y, bx - s1.x)
        angle2 = math.atan2(by - s2.y, bx - s2.x)
        if s1.ships >= each:
            moves.append([s1.id, angle1, each])
        if s2.ships >= needed - each:
            moves.append([s2.id, angle2, needed - each])

    return moves
