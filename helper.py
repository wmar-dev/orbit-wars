"""
Orbit Wars — helper.py

Pure-function game-mechanics library for Orbit Wars agents.
All functions are stateless and side-effect-free.
Import any subset for use in a custom agent:

    from helper import fleet_speed, path_safe, converged_orbit_lead, roi
"""

import math

__all__ = [
    # Constants
    "GARRISON_FLOOR_FACTOR",
    "EVACUATE_THRESHOLD",
    "ORBIT_LEAD_EPS",
    "ORBIT_LEAD_MAX_ITER",
    "REWARD_ALPHA",
    "ANGLE_EPSILON",
    "RACE_EPSILON",
    "SUN_RADIUS",
    "SAFETY_MARGIN",
    "SUN_EXCLUSION",
    "PLANET_MARGIN",
    "BOARD_SIZE",
    "W_CAPTURE",
    "W_SHIP",
    "CAPTURE_SCALE",
    "SHIP_SCALE",
    "PROD_WEIGHT",
    "DIST_WEIGHT",
    "MAX_PROD",
    "MAX_DIST",
    "HIGH_PROD_THRESHOLD",
    "ENEMY_PENALTY",
    "MAX_SHIPS_ESTIMATE",
    "BANK_PROD_THRESHOLD",
    "BANK_TURNS_FACTOR",
    "EPSILON",
    # Geometry
    "segment_dist_to_point",
    "segment_dist_to_sun",
    "ray_exits_board",
    "angle_to",
    "angle_diff",
    # Path safety
    "path_safe",
    # Fleet mechanics
    "fleet_speed",
    # Orbital prediction
    "predict_planet_pos",
    "converged_orbit_lead",
    # Comet mechanics
    "build_comet_path_lookup",
    "comet_predicted_pos",
    "comet_two_pass",
    # Scoring
    "roi",
    "reward_estimate",
    "planet_value",
    "enemy_incoming",
    # Strategy helpers
    "banking_mode",
    "predict_target",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GARRISON_FLOOR_FACTOR = 3       # Candidate O (v26): minimum ships to keep per production unit
EVACUATE_THRESHOLD = 3          # evacuate comet planets with ≤ this many turns remaining
ORBIT_LEAD_EPS = 0.1            # convergence tolerance for orbit-lead iteration (units)
ORBIT_LEAD_MAX_ITER = 10        # maximum iterations for orbit-lead convergence
REWARD_ALPHA = 0.1              # Candidate S (v31): weight of reward estimate in blended ROI
ANGLE_EPSILON = 0.1             # Candidate U (v38): angle tolerance for threat detection (radians)
RACE_EPSILON = 0.2              # v40: wider angle tolerance for race-condition detection (radians)
SUN_RADIUS = 10.0               # game constant
SAFETY_MARGIN = 2.0             # extra clearance beyond sun radius
SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN  # 12.0
PLANET_MARGIN = 1.0             # clearance beyond planet radius for obstruction check
BOARD_SIZE = 100.0              # game constant
_SUN_X = 50.0                   # game constant
_SUN_Y = 50.0                   # game constant
W_CAPTURE = 0.5                 # reward signal: weight of capture value
W_SHIP = 0.2                    # reward signal: weight of ship cost
CAPTURE_SCALE = 10.0            # reward signal: normalisation for capture value
SHIP_SCALE = 20.0               # reward signal: normalisation for ship cost
PROD_WEIGHT = 2.0               # v40 planet value: production weight
DIST_WEIGHT = 1.0               # v40 planet value: distance weight
MAX_PROD = 5                    # CONTEST.md: maximum planet production
MAX_DIST = 141.4                # diagonal of 100×100 board
HIGH_PROD_THRESHOLD = 4         # v40: production threshold for "high-value" planet classification
ENEMY_PENALTY = 0.5             # v40 planet value: garrison penalty for enemy-owned planets
MAX_SHIPS_ESTIMATE = 500.0      # v40: normalisation ceiling for enemy garrison estimate
BANK_PROD_THRESHOLD = 1.3       # v40 Variant B: production advantage ratio to enter banking mode
BANK_TURNS_FACTOR = 25          # v40 Variant B: bank until ships >= my_prod * this factor
EPSILON = 1e-6                  # small value to prevent division by zero

# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


def segment_dist_to_point(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def segment_dist_to_sun(ax, ay, bx, by):
    return segment_dist_to_point(ax, ay, bx, by, _SUN_X, _SUN_Y)


def ray_exits_board(ox, oy, angle):
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


def angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


def angle_diff(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))

# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def path_safe(ox, oy, tx, ty, all_planets=None, target_id=None, source_id=None):
    if not (0 <= tx <= BOARD_SIZE and 0 <= ty <= BOARD_SIZE):
        return False
    angle = math.atan2(ty - oy, tx - ox)
    ex, ey = ray_exits_board(ox, oy, angle)
    if segment_dist_to_sun(ox, oy, ex, ey) < SUN_EXCLUSION:
        return False
    if all_planets:
        for p in all_planets:
            if p.id == target_id or p.id == source_id:
                continue
            if segment_dist_to_point(ox, oy, tx, ty, p.x, p.y) < p.radius + PLANET_MARGIN:
                return False
    return True

# ---------------------------------------------------------------------------
# Fleet mechanics
# ---------------------------------------------------------------------------


def fleet_speed(n):
    if n <= 0:
        return 1.0
    return 1.0 + 5.0 * (math.log(n) / math.log(1000)) ** 1.5

# ---------------------------------------------------------------------------
# Orbital prediction
# ---------------------------------------------------------------------------


def predict_planet_pos(planet, initial_planets_map, angular_velocity, travel_turns):
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


def converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed):
    """Iteratively refine intercept point until position converges within ORBIT_LEAD_EPS."""
    x, y = t.x, t.y
    for _ in range(ORBIT_LEAD_MAX_ITER):
        travel = math.hypot(x - mine.x, y - mine.y) / speed
        nx, ny = predict_planet_pos(t, initial_planets_map, angular_velocity, travel)
        if math.hypot(nx - x, ny - y) < ORBIT_LEAD_EPS:
            return nx, ny
        x, y = nx, ny
    return x, y

# ---------------------------------------------------------------------------
# Comet mechanics
# ---------------------------------------------------------------------------


def build_comet_path_lookup(obs):
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


def comet_predicted_pos(comet_planet, comet_path_lookup, travel_turns):
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


def comet_two_pass(comet_planet, mine_x, mine_y, comet_path_lookup, speed):
    """Two-pass comet intercept: estimate travel time, read predicted position, refine."""
    t0 = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
    x1, y1, valid1 = comet_predicted_pos(comet_planet, comet_path_lookup, t0)
    if not valid1:
        return comet_planet.x, comet_planet.y, False
    t1 = math.hypot(x1 - mine_x, y1 - mine_y) / speed
    x2, y2, valid2 = comet_predicted_pos(comet_planet, comet_path_lookup, t1)
    if valid2:
        return x2, y2, True
    return x1, y1, True

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return (t.production ** 2) * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)


def reward_estimate(target, dispatch_ships):
    capture = target.production / CAPTURE_SCALE
    ship_cost = -dispatch_ships / SHIP_SCALE
    return max(0.0, W_CAPTURE * capture + W_SHIP * ship_cost)


def planet_value(planet, source_x, source_y):
    """Production-weighted value score, both factors normalised to [0, 1]."""
    prod_norm = planet.production / MAX_PROD
    dist = math.hypot(planet.x - source_x, planet.y - source_y)
    dist_norm = min(dist / MAX_DIST, 1.0)
    base = PROD_WEIGHT * prod_norm - DIST_WEIGHT * dist_norm
    if planet.owner >= 0:
        garrison_norm = min(planet.ships / MAX_SHIPS_ESTIMATE, 1.0)
        base -= ENEMY_PENALTY * garrison_norm
    return base


def enemy_incoming(target_x, target_y, raw_fleets, player):
    """Count enemy ships in fleets heading toward (target_x, target_y)."""
    total = 0
    for f in raw_fleets:
        if isinstance(f, (list, tuple)):
            f_owner, f_x, f_y, f_angle, f_ships = int(f[1]), float(f[2]), float(f[3]), float(f[4]), int(f[6])
        else:
            f_owner, f_x, f_y, f_angle, f_ships = f.owner, f.x, f.y, f.angle, f.ships
        if f_owner == player:
            continue
        expected = angle_to(f_x, f_y, target_x, target_y)
        if angle_diff(f_angle, expected) < RACE_EPSILON:
            total += f_ships
    return total

# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------


def banking_mode(my_planets, enemy_planets, step):
    """Return True if agent should suppress attacks (Variant B: ship-banking phase)."""
    if not enemy_planets:
        return False
    my_prod = sum(p.production for p in my_planets)
    enemy_prod = sum(p.production for p in enemy_planets)
    if my_prod / max(enemy_prod, 1) < BANK_PROD_THRESHOLD:
        return False
    my_ships = sum(p.ships for p in my_planets)
    return my_ships < my_prod * BANK_TURNS_FACTOR


def predict_target(t, mine, initial_planets_map, angular_velocity,
                   comet_planet_ids, comet_path_lookup, planets):
    """Return (x_pred, y_pred, safe) for a target using orbit-lead or comet two-pass."""
    speed = fleet_speed(t.ships + 1)
    if t.id in comet_planet_ids:
        x_pred, y_pred, valid = comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed)
        if not valid:
            return None, None, False
    else:
        x_pred, y_pred = converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed)
    safe = path_safe(mine.x, mine.y, x_pred, y_pred,
                     all_planets=planets, target_id=t.id, source_id=mine.id)
    return x_pred, y_pred, safe
