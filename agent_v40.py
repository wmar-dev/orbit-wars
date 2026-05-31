"""
Orbit Wars - agent_v40

Builds on agent_v38. Adds three replay-informed improvements from analysis
of Isaiah @ Tufa Labs (replay 78315039):
  1. Production-weighted planet priority (normalised value score, 2x production weight)
  2. Coordinated multi-planet attacks (top-target grouping replaces single-sender)
  3. Ship-banking phase (suppresses attacks when holding production advantage)

Variant flags (set before eval, best combination locked in after T020-T025):
  BANKING_VARIANT: "A" = fixed 800, "B" = prod*25 turns, "C" = adaptive step-gated
  FALLBACK_VARIANT: "A" = direct attack enemy high-prod, "C" = hybrid

Base logic inherited from agent_v38 (unchanged):
  - Candidate U: Threat-Aware Garrison Floor
  - Candidate R: Production-squared ROI (replaced by value score but helpers kept)
  - Candidate S (v31): Reward-blend scoring (kept as fallback)
  - Fix 2: Converged orbit-lead + two-pass comet intercept
  - Fix 1: Comet evacuation from documented fields
  - Candidate D: Single-sender coordination (replaced by top-target grouping)
  - Candidate O: GARRISON_FLOOR_FACTOR=3
  - Candidate Q: No range cap
  - _path_safe(): full-ray sun check + intermediate planet obstruction
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
GARRISON_FLOOR_FACTOR = 3
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

# --- agent_v40: replay-informed improvement constants ---

# Variant flags — change before each eval run; best combo locked in after T020-T025
BANKING_VARIANT = "B"   # "A"=fixed 800, "B"=prod*25 turns, "C"=adaptive step-gated
FALLBACK_VARIANT = "C"  # "A"=direct attack enemy high-prod, "C"=hybrid

# Planet value score weights (FR-001, data-model.md)
PROD_WEIGHT = 2.0
DIST_WEIGHT = 1.0
MAX_PROD = 5            # fixed per CONTEST.md
MAX_DIST = 141.4        # diagonal of 100x100 board
HIGH_PROD_THRESHOLD = 4
ENEMY_PENALTY = 0.5
MAX_SHIPS_ESTIMATE = 500.0

# Banking phase (FR-004)
BANK_PROD_THRESHOLD = 1.3    # production advantage ratio to enter banking mode
BANK_FIXED_THRESHOLD = 800   # Variant A: fixed ship ceiling
BANK_TURNS_FACTOR = 25       # Variant B: ceiling = my_prod * BANK_TURNS_FACTOR
BANK_STEP_CAP = 200          # Variant C: banking only before this game step
BANK_ADAPTIVE_THRESHOLD = 600  # Variant C: fixed ship ceiling

# Race condition detection (FR-001 addendum)
RACE_EPSILON = 0.2  # wider than ANGLE_EPSILON — accounts for orbit-lead prediction error


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


def _planet_value(planet, source_x, source_y):
    """Production-weighted value score, both factors normalised to [0,1]."""
    prod_norm = planet.production / MAX_PROD
    dist = math.hypot(planet.x - source_x, planet.y - source_y)
    dist_norm = min(dist / MAX_DIST, 1.0)
    base = PROD_WEIGHT * prod_norm - DIST_WEIGHT * dist_norm
    if planet.owner >= 0:  # enemy-owned: apply garrison penalty
        garrison_norm = min(planet.ships / MAX_SHIPS_ESTIMATE, 1.0)
        base -= ENEMY_PENALTY * garrison_norm
    return base


def _enemy_incoming(target_x, target_y, raw_fleets, player):
    """Count enemy ships in fleets heading toward (target_x, target_y)."""
    total = 0
    for f in raw_fleets:
        if isinstance(f, (list, tuple)):
            f_owner, f_x, f_y, f_angle, f_ships = int(f[1]), float(f[2]), float(f[3]), float(f[4]), int(f[6])
        else:
            f_owner, f_x, f_y, f_angle, f_ships = f.owner, f.x, f.y, f.angle, f.ships
        if f_owner == player:
            continue
        expected = math.atan2(target_y - f_y, target_x - f_x)
        if _angle_diff(f_angle, expected) < RACE_EPSILON:
            total += f_ships
    return total


def _banking_mode(my_planets, enemy_planets, step, variant):
    """Return True if the agent should suppress attacks this turn."""
    if not enemy_planets:  # no enemy planets yet — never bank, nothing to bank against
        return False
    my_prod = sum(p.production for p in my_planets)
    enemy_prod = sum(p.production for p in enemy_planets)
    prod_advantage = my_prod / max(enemy_prod, 1)
    if prod_advantage < BANK_PROD_THRESHOLD:
        return False
    my_ships = sum(p.ships for p in my_planets)
    if variant == "A":
        return my_ships < BANK_FIXED_THRESHOLD
    elif variant == "B":
        return my_ships < my_prod * BANK_TURNS_FACTOR
    elif variant == "C":
        return step < BANK_STEP_CAP and my_ships < BANK_ADAPTIVE_THRESHOLD
    return False


def _predict_target(t, mine, initial_planets_map, angular_velocity, comet_planet_ids, comet_path_lookup, planets):
    """Return (x_pred, y_pred, safe) for a target planet using orbit-lead or comet two-pass."""
    speed_for_lead = fleet_speed(t.ships + 1)
    if t.id in comet_planet_ids:
        x_pred, y_pred, valid = _comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed_for_lead)
        if not valid:
            return None, None, False
    else:
        x_pred, y_pred = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)
    safe = _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id)
    return x_pred, y_pred, safe


def agent(obs):
    moves = []
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner >= 0 and p.owner != player]
    targets = [p for p in planets if p.owner != player]
    neutral_targets = [p for p in planets if p.owner == -1]
    enemy_targets = [p for p in planets if p.owner >= 0 and p.owner != player]

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

    # US3: banking phase check — suppress attacks if holding production advantage
    banking = _banking_mode(my_planets, enemy_planets, step, BANKING_VARIANT)

    # Evacuation loop (unchanged from agent_v38)
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

    # US3: if banking, skip all offensive sends
    if banking:
        return moves

    # US1 / US2: per-planet targeting with production-boosted ROI scoring.
    # Keeps v38's proven per-planet independence; adds production weight to ROI
    # so high-production targets rank higher when ROI is close.
    # US2 coordination: track which planets targeted same destination.
    assigned_primary = set()
    assigned_secondary = set()

    # US1: identify high-production neutrals for fallback logic
    high_prod_neutrals = [t for t in neutral_targets if t.production >= HIGH_PROD_THRESHOLD]
    high_prod_enemies = [t for t in enemy_targets if t.production >= HIGH_PROD_THRESHOLD]

    # Sender assignment: same as v38 (dist/surplus)
    best_sender = {}
    for t in targets:
        best_score = float('inf')
        best_pid = None
        for src in my_planets:
            if src.id in departing_this_turn:
                continue
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

    # Per-planet targeting: v38 logic with race-condition ship scaling (T009)
    primary_moves = {}  # target_id -> (mine, bx, by, ships_needed, angle)
    for mine in my_planets:
        if mine.id in departing_this_turn or mine.id in evacuate_this_turn:
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
        ref_x = mine.x
        ref_y = mine.y

        def blended_key(item, _max_roi=max_roi):
            roi, t, bx, by = item
            roi_norm = roi / _max_roi
            r_est = _reward_estimate(t, t.ships + 1)
            return (1.0 - REWARD_ALPHA) * roi_norm + REWARD_ALPHA * r_est

        best_roi, best_target, bx, by = max(roi_scores, key=blended_key)

        enemy_inc = 0
        if best_target.owner == -1:
            enemy_inc = _enemy_incoming(bx, by, raw_fleets, player)
        ships_needed = max(best_target.ships + 1, best_target.ships + enemy_inc + 1)

        if mine.ships < ships_needed:
            continue

        angle = math.atan2(by - mine.y, bx - mine.x)
        moves.append([mine.id, angle, ships_needed])
        if best_target.production >= HIGH_PROD_THRESHOLD:
            assigned_primary.add(mine.id)
        else:
            assigned_secondary.add(mine.id)

    return moves


if __name__ == "__main__":
    from kaggle_environments import make as _make

    _env = _make("orbit_wars", configuration={"seed": 42}, debug=True)
    _env.run([agent, "main.py"])
    _final = _env.steps[-1]
    for i, s in enumerate(_final):
        print(f"Player {i}: reward={s['reward']}, status={s['status']}")
