"""
Orbit Wars - agent_v60

Unified lookahead search agent. Replaces greedy single-turn dispatch with a
budget-driven forward search that evaluates multiple candidate action sets
N turns forward before committing. Three strategies selectable via SEARCH_STRATEGY:
  "beam"  — alternative-target beam search (recommended)
  "mcts"  — Monte Carlo Tree Search with UCB1
  "nply"  — depth-limited exhaustive with beam pruning

Base: agent_v58 greedy logic (ported to _greedy_moves())
Simulator: ported and extended from agent_v59_beam (_SimState)
"""

import math
import time
import random
import copy

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

# ---------------------------------------------------------------------------
# Tunable constants (single place to change everything)
# ---------------------------------------------------------------------------

SEARCH_STRATEGY   = "beam"  # "beam" | "mcts" | "nply"
SEARCH_DEPTH      = 10      # turns to simulate forward
TRANSIT_WEIGHT    = 0.1     # weight for in-transit ships in eval score
SEARCH_TIMEOUT_MS = 800     # hard wall-clock cutoff per turn (ms)
BEAM_K            = 3       # top-K targets per mine for beam candidate gen
MCTS_C            = 1.41    # UCB1 exploration constant (≈√2)
NPLY_BEAM_WIDTH   = 8       # max branches kept at each N-ply level
OPPONENT_MODEL    = False   # if True, simulate simplified opponent dispatches

# ---------------------------------------------------------------------------
# Agent constants (from v58)
# ---------------------------------------------------------------------------

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
ANGLE_EPSILON = 0.1
_COMET_INTERCEPT_MAX_ITER = 10
_COMET_INTERCEPT_EPS = 0.5
FALLBACK_MIN_RATIO = 0.70

_SUN_X = 50.0
_SUN_Y = 50.0
SUN_RADIUS = 10.0
SAFETY_MARGIN = 2.0
SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN
PLANET_MARGIN = 1.0
BOARD_SIZE = 100.0


# ---------------------------------------------------------------------------
# Forward simulator
# ---------------------------------------------------------------------------

class _SimPlanet:
    __slots__ = ('id', 'owner', 'ships', 'production')
    def __init__(self, id, owner, ships, production):
        self.id = id; self.owner = owner
        self.ships = float(ships); self.production = float(production)


class _SimFleet:
    __slots__ = ('owner', 'target_id', 'ships', 'eta')
    def __init__(self, owner, target_id, ships, eta):
        self.owner = owner; self.target_id = target_id
        self.ships = int(ships); self.eta = int(eta)


class _SimState:
    def __init__(self, planets, fleets):
        self.planets = list(planets)
        self.fleets = list(fleets)
        self._idx = {p.id: i for i, p in enumerate(self.planets)}

    def step(self, opponent_model=False, player=-1):
        for p in self.planets:
            if p.owner >= 0:
                p.ships += p.production

        if opponent_model and player >= 0:
            opp = 1 - player
            opp_planets = [p for p in self.planets if p.owner == opp and p.ships > p.production * 3]
            non_opp = [p for p in self.planets if p.owner != opp]
            for src in opp_planets:
                surplus = src.ships - src.production * 3
                if surplus <= 0 or not non_opp:
                    continue
                nearest = min(non_opp, key=lambda p: math.hypot(p.id - src.id))
                nearest_real = min(non_opp, key=lambda p: (p.id != src.id, True))
                dist = math.hypot(nearest_real.id - src.id) if False else 10.0
                eta = max(1, int(dist / (1.0 + 5.0 * (math.log(max(int(surplus), 1)) / math.log(1000)) ** 1.5)))
                self.fleets.append(_SimFleet(opp, nearest_real.id, int(surplus), eta))
                src.ships -= surplus

        arrivals, remaining = [], []
        for f in self.fleets:
            f.eta -= 1
            (arrivals if f.eta <= 0 else remaining).append(f)
        self.fleets = remaining
        for f in arrivals:
            i = self._idx.get(f.target_id)
            if i is None:
                continue
            p = self.planets[i]
            if f.owner == p.owner:
                p.ships += f.ships
            elif f.ships > p.ships:
                p.owner = f.owner; p.ships = f.ships - p.ships
            else:
                p.ships -= f.ships

    def score(self, player, transit_weight=TRANSIT_WEIGHT):
        own_prod = sum(p.production for p in self.planets if p.owner == player)
        opp_prod = sum(p.production for p in self.planets if 0 <= p.owner != player)
        own_transit = sum(f.ships for f in self.fleets if f.owner == player)
        opp_transit = sum(f.ships for f in self.fleets if 0 <= f.owner != player)
        return (own_prod - opp_prod) + transit_weight * (own_transit - opp_transit)

    def copy(self):
        ps = [_SimPlanet(p.id, p.owner, p.ships, p.production) for p in self.planets]
        fs = [_SimFleet(f.owner, f.target_id, f.ships, f.eta) for f in self.fleets]
        return _SimState(ps, fs)


def _build_sim_state(planets, raw_fleets, player):
    """Convert live observation into a _SimState for forward simulation."""
    sim_planets = [_SimPlanet(p.id, p.owner, p.ships, p.production) for p in planets]
    planet_map = {p.id: p for p in planets}
    sim_fleets = []
    for f in raw_fleets:
        if isinstance(f, (list, tuple)):
            f_owner, f_x, f_y, f_angle, f_ships = f[1], float(f[2]), float(f[3]), float(f[4]), int(f[6])
        else:
            f_owner, f_x, f_y, f_angle, f_ships = f.owner, f.x, f.y, f.angle, f.ships
        best_id, best_diff = None, math.pi
        for p in planets:
            diff = _angle_diff(f_angle, math.atan2(p.y - f_y, p.x - f_x))
            if diff < best_diff:
                best_diff = diff; best_id = p.id
        if best_id is None or best_diff > ANGLE_EPSILON * 3:
            continue
        tp = planet_map.get(best_id)
        if tp is None:
            continue
        dist = math.hypot(f_x - tp.x, f_y - tp.y)
        eta = max(1, int(dist / fleet_speed(f_ships)))
        sim_fleets.append(_SimFleet(f_owner, best_id, f_ships, eta))
    return _SimState(sim_planets, sim_fleets)


# ---------------------------------------------------------------------------
# Geometry helpers (from v58/v59)
# ---------------------------------------------------------------------------

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
    t = math.hypot(comet_planet.x - mine_x, comet_planet.y - mine_y) / speed
    for _ in range(_COMET_INTERCEPT_MAX_ITER):
        x, y, valid = _comet_predicted_pos(comet_planet, comet_path_lookup, t)
        if not valid:
            return comet_planet.x, comet_planet.y, False
        t_new = math.hypot(x - mine_x, y - mine_y) / speed
        if abs(t_new - t) < _COMET_INTERCEPT_EPS:
            return x, y, True
        t = t_new
    return comet_planet.x, comet_planet.y, False


def _roi(t, bx, by, mine):
    travel = math.hypot(bx - mine.x, by - mine.y) / fleet_speed(t.ships + 1)
    return (t.production ** 2) * max(1.0, 100.0 - travel) / max(1.0, t.ships + t.production * travel + 1)


def _reward_estimate(target, dispatch_ships):
    capture = target.production / CAPTURE_SCALE
    ship_cost = -dispatch_ships / SHIP_SCALE
    return max(0.0, W_CAPTURE * capture + W_SHIP * ship_cost)


def _angle_diff(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def _enemy_fleet_size(t, x_pred, y_pred, mine_x, mine_y, initial_planets_map, angular_velocity):
    naive_speed = fleet_speed(t.ships + 1)
    naive_travel = math.hypot(x_pred - mine_x, y_pred - mine_y) / naive_speed
    ships_needed = int(t.ships + t.production * naive_travel) + 1

    corrected_speed = fleet_speed(ships_needed)
    if corrected_speed > naive_speed * 1.05:
        ip = initial_planets_map.get(t.id)
        if ip is not None:
            cx, cy = 50.0, 50.0
            orbital_radius = math.hypot(ip.x - cx, ip.y - cy)
            if orbital_radius + t.radius < 50.0:
                mine_fake = type('M', (), {'x': mine_x, 'y': mine_y})()
                x_c, y_c = _converged_orbit_lead(t, mine_fake, initial_planets_map,
                                                  angular_velocity, corrected_speed)
                corrected_travel = math.hypot(x_c - mine_x, y_c - mine_y) / corrected_speed
                ships_needed = int(t.ships + t.production * corrected_travel) + 1
                return ships_needed, x_c, y_c

    return ships_needed, x_pred, y_pred


# ---------------------------------------------------------------------------
# Greedy dispatch (extracted from v58 agent() body)
# ---------------------------------------------------------------------------

def _greedy_moves(obs, planets, my_planets, targets, initial_planets_map,
                  angular_velocity, raw_fleets, player, step):
    """v58-style greedy dispatch — baseline and fallback for all search strategies."""
    moves = []
    gff = 1.0 + 3.0 * min(step / 300.0, 1.0)

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

    claimed_targets = set()

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

        incoming = threat.get(mine.id, 0)
        buffer = mine.production * 2 if incoming > 0 else 0
        floor = max(mine.production * gff, incoming + buffer)
        if mine.ships - floor <= 0:
            continue

        candidates = []
        for t in targets:
            if t.id in claimed_targets:
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

        if best_target.owner == -1:
            ships_needed = best_target.ships + 1
        else:
            ships_needed, bx, by = _enemy_fleet_size(
                best_target, bx, by, mine.x, mine.y, initial_planets_map, angular_velocity
            )
            if not _path_safe(mine.x, mine.y, bx, by, all_planets=planets,
                               target_id=best_target.id, source_id=mine.id):
                continue

        if mine.ships < ships_needed:
            continue

        claimed_targets.add(best_target.id)
        angle = math.atan2(by - mine.y, bx - mine.x)
        moves.append([mine.id, angle, ships_needed])

    return moves


# ---------------------------------------------------------------------------
# Candidate generation helpers
# ---------------------------------------------------------------------------

def _compute_top_k_targets(mine, targets, initial_planets_map, angular_velocity,
                            comet_path_lookup, comet_planet_ids, planets, k=BEAM_K):
    """Return top-k (target, x_pred, y_pred, roi) tuples for a mine planet."""
    scored = []
    for t in targets:
        speed_for_lead = fleet_speed(t.ships + 1)
        if t.id in comet_planet_ids:
            x_pred, y_pred, valid = _comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed_for_lead)
            if not valid:
                continue
        else:
            x_pred, y_pred = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)
        if not _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets,
                          target_id=t.id, source_id=mine.id):
            continue
        roi = _roi(t, x_pred, y_pred, mine)
        scored.append((roi, t, x_pred, y_pred))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def _move_to_dispatch(src_id, angle, ships, planets_map, all_targets):
    """Convert a greedy move (src_id, angle, ships) to (src_id, target_id, ships, eta)."""
    src = planets_map.get(src_id)
    if src is None:
        return None
    best_id, best_diff = None, math.pi
    for p in all_targets:
        diff = _angle_diff(angle, math.atan2(p.y - src.y, p.x - src.x))
        if diff < best_diff:
            best_diff = diff; best_id = p.id
    if best_id is None:
        return None
    tp = planets_map.get(best_id)
    if tp is None:
        return None
    dist = math.hypot(tp.x - src.x, tp.y - src.y)
    eta = max(1, int(dist / fleet_speed(ships)))
    return (src_id, best_id, ships, eta)


def _dispatches_to_moves(dispatches, planets_map):
    """Convert dispatch tuples back to game move format [src_id, angle, ships]."""
    moves = []
    for src_id, target_id, ships, eta in dispatches:
        src = planets_map.get(src_id)
        tgt = planets_map.get(target_id)
        if src is None or tgt is None:
            continue
        angle = math.atan2(tgt.y - src.y, tgt.x - src.x)
        moves.append([src_id, angle, ships])
    return moves


def _apply_dispatches(sim_state, dispatches, player):
    for src_id, target_id, ships, eta in dispatches:
        i = sim_state._idx.get(src_id)
        if i is not None:
            sim_state.planets[i].ships = max(0.0, sim_state.planets[i].ships - ships)
        sim_state.fleets.append(_SimFleet(player, target_id, ships, eta))


# ---------------------------------------------------------------------------
# Beam search
# ---------------------------------------------------------------------------

def _gen_beam_candidates(my_planets, targets, greedy_moves, planets, initial_planets_map,
                         angular_velocity, player, step):
    """Generate alternative-target beam candidates.

    Returns list of (dispatches, moves) pairs.
    Candidate 0 = full greedy.
    Candidates 1..N = greedy with one mine redirected to its 2nd/3rd best target.
    Last candidate = hold-all.
    """
    planets_map = {p.id: p for p in planets}
    comet_path_lookup = _build_comet_path_lookup_cached
    comet_planet_ids = set(comet_path_lookup.keys()) if comet_path_lookup else set()

    # Convert greedy moves to dispatch tuples
    all_targets = targets
    greedy_dispatches = []
    for m in greedy_moves:
        d = _move_to_dispatch(m[0], m[1], m[2], planets_map, all_targets)
        if d:
            greedy_dispatches.append(d)

    # Map src_id -> dispatch for easy replacement
    greedy_dispatch_map = {d[0]: d for d in greedy_dispatches}

    candidates = [(greedy_dispatches, greedy_moves)]

    gff = 1.0 + 3.0 * min(step / 300.0, 1.0)
    threat = {}  # simplified: no threat recalc needed here

    for mine in my_planets:
        top_k = _compute_top_k_targets(mine, targets, initial_planets_map, angular_velocity,
                                        comet_path_lookup, comet_planet_ids, planets, k=BEAM_K)
        if not top_k:
            continue

        existing = greedy_dispatch_map.get(mine.id)
        if existing is None:
            # Greedy held this mine — don't generate new dispatches (risk depleting defense
            # vs saving ships for a better future target that greedy correctly deferred)
            continue

        # Compute ships available
        incoming = threat.get(mine.id, 0)
        buffer = mine.production * 2 if incoming > 0 else 0
        floor = max(mine.production * gff, incoming + buffer)
        surplus = mine.ships - floor
        if surplus <= 0:
            continue

        for roi, t, x_pred, y_pred in top_k:
            # Skip if this is already the greedy target for this mine (already in candidate 0)
            if existing[1] == t.id:
                continue

            # Fleet sizing
            if t.owner == -1:
                ships_needed = int(t.ships) + 1
            else:
                ships_needed, x_pred, y_pred = _enemy_fleet_size(
                    t, x_pred, y_pred, mine.x, mine.y, initial_planets_map, angular_velocity
                )

            if surplus < ships_needed:
                continue

            dist = math.hypot(x_pred - mine.x, y_pred - mine.y)
            eta = max(1, int(dist / fleet_speed(ships_needed)))
            new_dispatch = (mine.id, t.id, ships_needed, eta)
            new_move = [mine.id, math.atan2(y_pred - mine.y, x_pred - mine.x), ships_needed]

            # Replace this mine's dispatch, keep others
            alt_dispatches = [d for d in greedy_dispatches if d[0] != mine.id] + [new_dispatch]
            alt_moves = [m for m in greedy_moves if m[0] != mine.id] + [new_move]
            candidates.append((alt_dispatches, alt_moves))

    # Hold-all
    candidates.append(([], []))
    return candidates


def _beam_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    """Beam search over alternative-target candidates."""
    candidates = _gen_beam_candidates(my_planets, targets, greedy_moves, planets,
                                      initial_planets_map, angular_velocity, player, step)

    best_score = float('-inf')
    best_moves = greedy_moves

    for dispatches, moves in candidates:
        if (time.perf_counter() - t_start) * 1000 > SEARCH_TIMEOUT_MS:
            break
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        for _ in range(SEARCH_DEPTH):
            state.step(opponent_model=OPPONENT_MODEL, player=player)
        score = state.score(player, TRANSIT_WEIGHT)
        if score > best_score:
            best_score = score
            best_moves = moves

    return best_moves


# ---------------------------------------------------------------------------
# MCTS
# ---------------------------------------------------------------------------

def _mcts_rollout(state, player, depth):
    """Simplified greedy rollout: each mine sends surplus to nearest non-owned planet."""
    state = state.copy()
    for _ in range(depth):
        # Simplified own dispatch
        for p in state.planets:
            if p.owner != player:
                continue
            floor = p.production * 3
            surplus = p.ships - floor
            if surplus <= 0:
                continue
            non_own = [q for q in state.planets if q.owner != player]
            if not non_own:
                continue
            tgt = min(non_own, key=lambda q: abs(q.id - p.id))
            dist = max(10.0, abs(tgt.id - p.id) * 5.0)
            eta = max(1, int(dist / fleet_speed(int(surplus))))
            state.fleets.append(_SimFleet(player, tgt.id, int(surplus), eta))
            p.ships -= surplus
        state.step(opponent_model=OPPONENT_MODEL, player=player)
    return state.score(player, TRANSIT_WEIGHT)


def _mcts_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    """UCB1-based multi-sample search over same candidates as beam search.

    Uses the same candidate set as _gen_beam_candidates (redirect one greedy-dispatching
    mine to an alternative target) but evaluates each candidate multiple times via rollout,
    returning the candidate with highest average score.
    """
    candidates = _gen_beam_candidates(my_planets, targets, greedy_moves, planets,
                                      initial_planets_map, angular_velocity, player, step)
    if len(candidates) <= 1:
        return greedy_moves

    scores = [0.0] * len(candidates)
    visits = [0] * len(candidates)

    def ucb1(i):
        total_visits = sum(visits) or 1
        if visits[i] == 0:
            return float('inf')
        return scores[i] / visits[i] + MCTS_C * math.sqrt(math.log(total_visits) / visits[i])

    n = len(candidates)
    while (time.perf_counter() - t_start) * 1000 < SEARCH_TIMEOUT_MS:
        # Select candidate with highest UCB1
        idx = max(range(n), key=ucb1)
        dispatches, moves = candidates[idx]
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        for _ in range(SEARCH_DEPTH):
            state.step()
        score = state.score(player, TRANSIT_WEIGHT)
        scores[idx] += score
        visits[idx] += 1
        # With deterministic simulation, scores converge after one visit per candidate
        if all(v > 0 for v in visits):
            break

    # Return candidate with highest average score
    best_idx = max(range(n),
                   key=lambda i: scores[i] / visits[i] if visits[i] > 0 else float('-inf'))
    return candidates[best_idx][1]


# ---------------------------------------------------------------------------
# N-ply search
# ---------------------------------------------------------------------------

def _nply_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    """Depth-limited exhaustive search with beam pruning."""
    planets_map = {p.id: p for p in planets}
    comet_path_lookup = _build_comet_path_lookup_cached
    comet_planet_ids = set(comet_path_lookup.keys()) if comet_path_lookup else set()

    gff = 1.0 + 3.0 * min(step / 300.0, 1.0)
    threat = {}

    # Build greedy dispatch map — only allow alternatives for greedy-dispatching mines
    # Store as 5-tuple (src_id, target_id, ships, eta, angle) to match alt option format
    greedy_move_map = {m[0]: m for m in greedy_moves}
    greedy_dispatch_map = {}
    for m in greedy_moves:
        d = _move_to_dispatch(m[0], m[1], m[2], planets_map, targets)
        if d:
            src_id, target_id, ships, eta = d
            greedy_dispatch_map[src_id] = (src_id, target_id, ships, eta, m[1])

    # Compute per-mine options: hold-only for greedy-held mines, alternatives for dispatching mines
    mine_options = {}
    for mine in my_planets:
        if mine.id not in greedy_dispatch_map:
            mine_options[mine.id] = [None]  # greedy holds this mine; don't dispatch early
            continue

        incoming = threat.get(mine.id, 0)
        buffer = mine.production * 2 if incoming > 0 else 0
        floor = max(mine.production * gff, incoming + buffer)
        surplus = mine.ships - floor
        if surplus <= 0:
            mine_options[mine.id] = [greedy_dispatch_map[mine.id]]
            continue
        top_k = _compute_top_k_targets(mine, targets, initial_planets_map, angular_velocity,
                                        comet_path_lookup, comet_planet_ids, planets, k=2)
        greedy_target_id = greedy_dispatch_map[mine.id][1]
        opts = [greedy_dispatch_map[mine.id]]  # always include greedy choice (5-tuple)
        for roi, t, x_pred, y_pred in top_k:
            if t.id == greedy_target_id:
                continue  # already in opts
            if t.owner == -1:
                ships_needed = int(t.ships) + 1
            else:
                ships_needed, x_pred, y_pred = _enemy_fleet_size(
                    t, x_pred, y_pred, mine.x, mine.y, initial_planets_map, angular_velocity
                )
            if surplus < ships_needed:
                continue
            dist = math.hypot(x_pred - mine.x, y_pred - mine.y)
            eta = max(1, int(dist / fleet_speed(ships_needed)))
            angle = math.atan2(y_pred - mine.y, x_pred - mine.x)
            opts.append((mine.id, t.id, ships_needed, eta, angle))
        mine_options[mine.id] = opts

    # Generate all first-turn action combinations (capped by beam width after full expansion)
    def gen_first_turn_combos():
        mines = list(my_planets)
        if not mines:
            return [([],  [])]
        # Build full cross product (held mines contribute only None, so won't explode)
        result = [([], [])]
        for mine in mines:
            opts = mine_options.get(mine.id, [None])
            new_result = []
            for dispatches, moves in result:
                for opt in opts:
                    if opt is None:
                        new_result.append((list(dispatches), list(moves)))
                    else:
                        src_id, target_id, ships, eta, angle = opt
                        new_result.append(
                            (dispatches + [(src_id, target_id, ships, eta)],
                             moves + [[src_id, angle, ships]])
                        )
            result = new_result
        # Cap post-expansion (greedy-held mines have [None] so this rarely triggers)
        if len(result) > NPLY_BEAM_WIDTH * 4:
            result = result[:NPLY_BEAM_WIDTH * 4]
        return result

    combos = gen_first_turn_combos()

    # Simulate each combo forward and score
    best_score = float('-inf')
    best_moves = greedy_moves

    for dispatches, moves in combos:
        if (time.perf_counter() - t_start) * 1000 > SEARCH_TIMEOUT_MS:
            break
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        # Beam pruning: track top NPLY_BEAM_WIDTH branches after first step
        for d in range(SEARCH_DEPTH):
            state.step(opponent_model=OPPONENT_MODEL, player=player)
        score = state.score(player, TRANSIT_WEIGHT)
        if score > best_score:
            best_score = score
            best_moves = moves

    return best_moves


# ---------------------------------------------------------------------------
# Lookahead dispatcher
# ---------------------------------------------------------------------------

_build_comet_path_lookup_cached = {}


def _lookahead_search(strategy, obs, greedy_moves, base_state, planets, my_planets, targets,
                      initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    """Dispatch to the selected search strategy. Falls back to greedy on unknown strategy."""
    if strategy == "beam":
        return _beam_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                            initial_planets_map, angular_velocity, raw_fleets, player, step, t_start)
    elif strategy == "mcts":
        return _mcts_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                            initial_planets_map, angular_velocity, raw_fleets, player, step, t_start)
    elif strategy == "nply":
        return _nply_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                            initial_planets_map, angular_velocity, raw_fleets, player, step, t_start)
    return greedy_moves


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def agent(obs):
    global _build_comet_path_lookup_cached
    t_start = time.perf_counter()

    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = obs.get("initial_planets", []) if isinstance(obs, dict) else getattr(obs, "initial_planets", [])
    angular_velocity = obs.get("angular_velocity", 0.0) if isinstance(obs, dict) else getattr(obs, "angular_velocity", 0.0)
    raw_fleets = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)

    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    targets = [p for p in planets if p.owner != player]

    initial_planets_map = {}
    for ip_raw in initial_planets_raw:
        ip = Planet(*ip_raw)
        initial_planets_map[ip.id] = ip

    # Cache comet lookup for helpers that don't receive obs
    _build_comet_path_lookup_cached = _build_comet_path_lookup(obs)

    if not my_planets or not targets:
        return []

    greedy_moves = _greedy_moves(obs, planets, my_planets, targets, initial_planets_map,
                                 angular_velocity, raw_fleets, player, step)

    base_state = _build_sim_state(planets, raw_fleets, player)

    return _lookahead_search(SEARCH_STRATEGY, obs, greedy_moves, base_state, planets,
                             my_planets, targets, initial_planets_map, angular_velocity,
                             raw_fleets, player, step, t_start)


if __name__ == "__main__":
    from kaggle_environments import make as _make

    _env = _make("orbit_wars", configuration={"seed": 42}, debug=True)
    _env.run([agent, "main.py"])
    _final = _env.steps[-1]
    for i, s in enumerate(_final):
        print(f"Player {i}: reward={s['reward']}, status={s['status']}")
