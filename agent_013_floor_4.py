"""
Orbit Wars - Combined Agent Round 6 (agent_v38)

Builds on agent_v33.

Round 6 result: only Candidate U passed (86% vs agent_v33).
Candidates S (4%), T (0%), and V (50% draws) all failed.

Stacked mechanic — Candidate U: Threat-Aware Garrison Floor
  Parses obs.fleets to detect enemy fleets heading toward owned planets.
  Uses angle-matching (ANGLE_EPSILON = 0.1 rad) from each enemy fleet's position
  to each owned planet's position. Raises the garrison floor for threatened planets:
    floor = max(GARRISON_FLOOR_FACTOR * production, incoming_enemy_ships)
  Prevents the agent from draining a planet's garrison offensively right before
  an enemy fleet arrives and captures it. Does NOT add defensive dispatch moves
  (distinction from Candidate I: reactive defense, which failed at 16%/5%).

Candidates NOT stacked (all failed vs agent_v33):
  - Candidate S R6 (fleet deduplication): 4% — angle-matching too aggressive
  - Candidate T R6 (transit-adjusted sizing): 0% — over-sends, can't afford most targets
  - Candidate V R6 (winning-state throttle): 50% (50 draws) — 2:1 threshold never triggers

Safety guards and base logic inherited from agent_v33 (unchanged):
  - Candidate R: Production-squared ROI
  - Candidate S (v31): Reward-blend scoring (REWARD_ALPHA=0.1)
  - Fix 2: Converged orbit-lead + two-pass comet intercept
  - Fix 1: Comet evacuation from documented fields
  - Candidate D: Single-sender coordination
  - Candidate O: GARRISON_FLOOR_FACTOR=3 (baseline; raised per-planet when threatened)
  - Candidate Q: No range cap
  - _path_safe(): full-ray sun check + intermediate planet obstruction
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

W_CAPTURE = 0.5
W_SHIP = 0.2
CAPTURE_SCALE = 10.0
SHIP_SCALE = 20.0

EPSILON = 1e-6
RANGE_FACTOR = 2.0
GARRISON_FLOOR_FACTOR = 5
EVACUATE_THRESHOLD = 3
ORBIT_LEAD_EPS = 0.1
ORBIT_LEAD_MAX_ITER = 10
REWARD_ALPHA = 0.1
ANGLE_EPSILON = 0.1  # radians: threshold for fleet-to-planet angle matching (Candidate U)

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


def _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed,
                          max_iter=ORBIT_LEAD_MAX_ITER, eps=ORBIT_LEAD_EPS):
    x, y = t.x, t.y
    for _ in range(max_iter):
        travel = math.hypot(x - mine.x, y - mine.y) / speed
        nx, ny = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel)
        if math.hypot(nx - x, ny - y) < eps:
            return nx, ny
        x, y = nx, ny
    return x, y


def _build_comet_path_lookup(obs):
    lookup = {}
    comets = obs.get("comets", []) if isinstance(obs, dict) else getattr(obs, "comets", [])
    for group in comets:
        if isinstance(group, dict):
            planet_ids = group.get("planet_ids", [])
            paths = group.get("paths", [])
            path_index = group.get("path_index", 0)
        else:
            planet_ids = getattr(group, "planet_ids", [])
            paths = getattr(group, "paths", [])
            path_index = getattr(group, "path_index", 0)
        for i, pid in enumerate(planet_ids):
            path = paths[i] if i < len(paths) else []
            remaining_turns = max(0, len(path) - path_index)
            lookup[pid] = (path, path_index, remaining_turns)
    return lookup


def _comet_predicted_pos(comet_planet, comet_path_lookup, travel_turns):
    path, path_index, _ = comet_path_lookup[comet_planet.id]
    if not path:
        return comet_planet.x, comet_planet.y, False
    future_idx = min(int(path_index + travel_turns), len(path) - 1)
    if future_idx + 5 >= len(path):
        return comet_planet.x, comet_planet.y, False
    pos = path[future_idx]
    if isinstance(pos, (list, tuple)):
        return float(pos[0]), float(pos[1]), True
    return comet_planet.x, comet_planet.y, True


def _comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed):
    t0 = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
    x1, y1, valid1 = _comet_predicted_pos(comet_planet, comet_path_lookup, t0)
    if not valid1:
        return comet_planet.x, comet_planet.y, False
    t1 = math.hypot(x1 - mine_x, y1 - mine_y) / speed
    x2, y2, valid2 = _comet_predicted_pos(comet_planet, comet_path_lookup, t1)
    if valid2:
        return x2, y2, True
    return x1, y1, True


def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return (t.production ** 2) * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)


def _reward_estimate(target, dispatch_ships):
    capture = target.production / CAPTURE_SCALE
    ship_cost = -dispatch_ships / SHIP_SCALE
    return max(0.0, W_CAPTURE * capture + W_SHIP * ship_cost)


def _angle_diff(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


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

    # Candidate U: build threat dict from enemy fleets → owned planets
    threat = {}
    for f in raw_fleets:
        if isinstance(f, (list, tuple)):
            f_owner, f_x, f_y, f_angle, f_ships = f[1], float(f[2]), float(f[3]), float(f[4]), int(f[6])
        else:
            f_owner, f_x, f_y, f_angle, f_ships = f.owner, f.x, f.y, f.angle, f.ships
        if f_owner == player:
            continue
        for p in my_planets:
            expected = math.atan2(p.y - f_y, p.x - f_x)
            if _angle_diff(f_angle, expected) < ANGLE_EPSILON:
                threat[p.id] = threat.get(p.id, 0) + f_ships

    comet_path_lookup = _build_comet_path_lookup(obs)
    comet_planet_ids = set(comet_path_lookup.keys())

    departing_this_turn = set()
    evacuate_this_turn = set()
    for pid, (path, path_index, remaining_turns) in comet_path_lookup.items():
        p = next((x for x in my_planets if x.id == pid), None)
        if p is None:
            continue
        if remaining_turns == 0:
            departing_this_turn.add(pid)
        elif remaining_turns <= EVACUATE_THRESHOLD:
            evacuate_this_turn.add(pid)

    if not my_planets or not targets:
        return moves

    best_sender = {}
    for t in targets:
        best_score = float('inf')
        best_pid = None
        for src in my_planets:
            if src.id in departing_this_turn:
                continue
            # Candidate U: threat-aware garrison floor
            floor = max(src.production * GARRISON_FLOOR_FACTOR, threat.get(src.id, 0))
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

    for mine in my_planets:
        if mine.id in departing_this_turn:
            continue

        if mine.id in evacuate_this_turn:
            if mine.ships < 1:
                continue
            speed_evac = fleet_speed(mine.ships)
            best_evac = None
            best_evac_score = float('-inf')
            best_evac_pos = (0.0, 0.0)

            for p in planets:
                if p.id == mine.id:
                    continue
                if p.id in comet_planet_ids:
                    x_pred, y_pred, valid = _comet_two_pass(p, mine.x, mine.y, comet_path_lookup, speed_evac)
                    if not valid:
                        continue
                else:
                    x_pred, y_pred = _converged_orbit_lead(p, mine, initial_planets_map, angular_velocity, speed_evac)

                if not _path_safe(mine.x, mine.y, x_pred, y_pred,
                                  all_planets=planets, target_id=p.id, source_id=mine.id):
                    continue

                if p.owner == player:
                    score = p.production / (math.hypot(mine.x - x_pred, mine.y - y_pred) + EPSILON)
                else:
                    score = _roi(p, x_pred, y_pred, mine)

                if score > best_evac_score:
                    best_evac_score = score
                    best_evac = p
                    best_evac_pos = (x_pred, y_pred)

            if best_evac is None:
                continue
            angle = math.atan2(best_evac_pos[1] - mine.y, best_evac_pos[0] - mine.x)
            moves.append([mine.id, angle, mine.ships])
            continue

        candidates = []
        for t in targets:
            if best_sender.get(t.id) != mine.id:
                continue

            speed_for_lead = fleet_speed(t.ships + 1)

            if t.id in comet_planet_ids:
                x_pred, y_pred, valid = _comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed_for_lead)
                if not valid:
                    continue
            else:
                x_pred, y_pred = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)

            if _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
                candidates.append((t, x_pred, y_pred))

        if not candidates:
            continue

        roi_scores = [(_roi(t, bx, by, mine), t, bx, by) for t, bx, by in candidates]
        max_roi = max(r for r, _, _, _ in roi_scores) or 1.0

        def blended_key(item, _max_roi=max_roi):
            roi, t, bx, by = item
            roi_norm = roi / _max_roi
            r_est = _reward_estimate(t, t.ships + 1)
            return (1.0 - REWARD_ALPHA) * roi_norm + REWARD_ALPHA * r_est

        best_roi, best_target, bx, by = max(roi_scores, key=blended_key)

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
