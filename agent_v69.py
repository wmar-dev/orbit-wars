"""
Orbit Wars - agent_v69 (experiments round 8)

Built on agent_v68 (current best; 64.0% vs agent_v64 per Round 7,
but 0.0% vs slawekbiel_agent, the strongest loadable benchmark).

Round 8 pivots from constant-tweaking to qualitatively more advanced
techniques aimed squarely at the slawekbiel benchmark wall. Reading
slawekbiel's source (torch-vectorized "the-producer-agent") shows its
edge is structural, not a learned policy: (1) global candidate scoring
that jointly assigns (source, target) pairs across the whole board
instead of per-planet greedy claiming, (2) a "regroup gradient" that
repositions surplus ships from safe rear planets toward stressed front
planets pre-emptively, and (3) reinforcement timing. All three are
reproducible in pure Python.

Round 8 candidates (each behind an independent toggle, isolated code
region, default OFF so agent_v69 == agent_v68 until enabled):
  GLOBAL_ALLOC_ENABLED — Candidate A: replace per-planet greedy target
    claiming with a joint (source, target) assignment that resolves
    conflicts globally (closes slawekbiel's biggest structural edge).
  DEEP_SEARCH_ENABLED — Candidate B: anytime iterative-deepening beam
    search bounded by DEEP_SEARCH_BUDGET_MS, with graceful fallback to
    the v68 greedy/beam move if the budget is exhausted before any
    search completes.
  REGROUP_ENABLED — Candidate C: pre-emptive regroup-gradient
    repositioning — rank owned planets by reachable-enemy-mass stress
    and move surplus from low-stress rear planets toward high-stress
    front planets, distinct from v64's reactive (and discarded)
    DEFENSE_INTERCEPT_ENABLED.

Inherited from v68 (round 7):
  KEPT  CANDIDATE_1_ENABLED — opening rush (step <= OPENING_RUSH_WINDOW)
  DISCARDED  CANDIDATE_2_ENABLED — established-game rush (severe regression)

Inherited from v64 (round 4):
  KEPT  WEIGHTED_EVAL_FIXED_ENABLED    — corrected production-weighted beam eval (52% vs v62)
  KEPT  MULTI_TURN_PLAN_ENABLED        — skip candidates in beam search (54% vs v63)
  DISCARDED  OPPONENT_MODEL_V3_ENABLED — production-weighted opponent in sim (34% vs v63)
  DISCARDED  PHASE_DETECTION_ENABLED    — adjust dispatch params by game phase (48% vs v63)
  DISCARDED  DEFENSE_INTERCEPT_ENABLED — no benefit detected (48%/45% vs v62)

Inherited from v62:
  PASS  SPLINTER_DISPATCH_ENABLED    — send surplus to nearest cheap neutral
  PASS  EVAL_ENHANCED_ENABLED        — planet count + ship count in beam eval
  PASS  OPPONENT_MODEL_V2_ENABLED    — proper position-based opponent in forward sim
  PASS  DYNAMIC_GARRISON_ENABLED     — lower garrison cap 2.5x/400t
"""

import math
import time
import random
import copy

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------

SEARCH_STRATEGY   = "beam"
SEARCH_DEPTH      = 10
TRANSIT_WEIGHT    = 0.1
SEARCH_TIMEOUT_MS = 800
BEAM_K            = 3
MCTS_C            = 1.41
NPLY_BEAM_WIDTH   = 8

# ---------------------------------------------------------------------------
# v63 Experiment toggles — set False to isolate/disable each
# ---------------------------------------------------------------------------

WEIGHTED_EVAL_FIXED_ENABLED    = True   # KEPT — 52% vs v62
DEFENSE_INTERCEPT_ENABLED      = False  # DISCARDED — no benefit detected

# v64 Experiment toggles — set False to isolate/disable each
OPPONENT_MODEL_V3_ENABLED      = False  # DISCARDED — 34% vs v63, too pessimistic in sim
MULTI_TURN_PLAN_ENABLED        = True   # P2 — KEPT (54% vs v63)
PHASE_DETECTION_ENABLED        = False  # DISCARDED — 48% vs v63, aggressive floor reduction leaves planets vulnerable

# ---------------------------------------------------------------------------
# v68 Experiment toggles (Round 7) — set False to isolate/disable each
# ---------------------------------------------------------------------------

CANDIDATE_1_ENABLED            = True   # Opening rush (step <= OPENING_RUSH_WINDOW)
CANDIDATE_2_ENABLED            = False  # Established-game rush (step > OPENING_RUSH_WINDOW)
OPENING_RUSH_WINDOW            = 20     # boundary step between Candidate 1 and Candidate 2

# ---------------------------------------------------------------------------
# v69 Experiment toggles (Round 8) — set False to isolate/disable each
# ---------------------------------------------------------------------------

GLOBAL_ALLOC_ENABLED   = True   # Candidate A: joint (source, target) assignment, replaces per-planet greedy claim
DEEP_SEARCH_ENABLED    = False  # Candidate B: anytime iterative-deepening beam, bounded by DEEP_SEARCH_BUDGET_MS
DEEP_SEARCH_BUDGET_MS  = 700    # wall-clock budget for Candidate B (leaves >=300ms margin under 1s actTimeout)
DEEP_SEARCH_DEPTH_STEP = 10     # additional simulation depth per iterative-deepening pass
REGROUP_ENABLED        = False  # Candidate C: pre-emptive regroup-gradient repositioning
REGROUP_MIN_SURPLUS    = 3.0    # minimum idle surplus (above garrison floor) before a rear planet regroups

# ---------------------------------------------------------------------------
# v62 Experiment toggles — set False to isolate/disable each
# ---------------------------------------------------------------------------

MULTI_DISPATCH_ENABLED     = False  # DISCARDED: 50% vs v60 (neutral)
THREAT_BUFFER_ENABLED      = False  # DISCARDED: 40% vs v60 (negative)
SPLINTER_DISPATCH_ENABLED  = True   # PASS: 62.5% vs v60
EVAL_ENHANCED_ENABLED      = True   # PASS: 65% vs v60
OPPONENT_MODEL_V2_ENABLED  = True   # PASS: 80% vs v60 (after double-dispatch fix)

DYNAMIC_GARRISON_ENABLED  = True    # PASS: 67.5% vs v60 (from v61)

# ---------------------------------------------------------------------------
# Tunable sub-parameters
# ---------------------------------------------------------------------------

SPLINTER_WINDOW            = 30     # last step where splinter dispatch applies
SPLINTER_SURPLUS_FRACTION  = 1.0    # send all surplus, or fraction thereof

# Exp 6: interceptor defense
INTERCEPT_MIN_THREAT_RATIO = 1.2   # only intercept if fleet.ships > garrison * this
INTERCEPT_MIN_PROD         = 3.0   # only defend planets with production >= this

# Eval weights for Experiment 4
PLANET_COUNT_WEIGHT        = 0.5    # weight per planet owned above opponent
SHIP_COUNT_WEIGHT          = 0.02   # weight per ship owned above opponent

# ---------------------------------------------------------------------------
# Agent constants
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
# Forward simulator (enhanced with x,y for Experiment 5)
# ---------------------------------------------------------------------------

class _SimPlanet:
    __slots__ = ('id', 'owner', 'ships', 'production', 'x', 'y')
    def __init__(self, id, owner, ships, production, x=0.0, y=0.0):
        self.id = id; self.owner = owner
        self.ships = float(ships); self.production = float(production)
        self.x = float(x); self.y = float(y)


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

        if player >= 0:
            if OPPONENT_MODEL_V3_ENABLED:
                self._sim_opponent_step_v3(player)
            elif OPPONENT_MODEL_V2_ENABLED:
                self._sim_opponent_step_v2(player)

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

    def _sim_opponent_step_v2(self, player):
        """Position-based nearest-target opponent dispatch (Experiment 5)."""
        for opp_id in range(4):
            if opp_id == player:
                continue
            opp_planets = [p for p in self.planets if p.owner == opp_id]
            targets = [p for p in self.planets if p.owner != opp_id]
            if not opp_planets or not targets:
                continue
            for src in opp_planets:
                surplus = src.ships - src.production * 3
                if surplus <= 0:
                    continue
                nearest = min(targets, key=lambda t: math.hypot(src.x - t.x, src.y - t.y))
                dist = math.hypot(src.x - nearest.x, src.y - nearest.y)
                speed = 1.0 + 5.0 * (math.log(max(int(surplus), 1)) / math.log(1000)) ** 1.5
                eta = max(1, int(dist / speed))
                self.fleets.append(_SimFleet(opp_id, nearest.id, int(surplus), eta))
                src.ships -= surplus

    def _sim_opponent_step_v3(self, player):
        """Production-weighted opponent dispatch (Experiment round 4, US1).

        Uses ROI-based target selection (production^2 / distance) instead of
        nearest-target, with dynamic garrison floor similar to v62 greedy dispatch.
        """
        for opp_id in range(4):
            if opp_id == player:
                continue
            opp_planets = [p for p in self.planets if p.owner == opp_id]
            targets = [p for p in self.planets if p.owner != opp_id]
            if not opp_planets or not targets:
                continue
            for src in opp_planets:
                floor = src.production * 2.5
                surplus = src.ships - floor
                if surplus <= 0:
                    continue
                # Score targets by production^2 / distance (ROI-style)
                def _v3_roi(t):
                    d = math.hypot(src.x - t.x, src.y - t.y) + 1e-6
                    return (t.production ** 2) / d
                best = max(targets, key=_v3_roi)
                dist = math.hypot(src.x - best.x, src.y - best.y)
                speed = 1.0 + 5.0 * (math.log(max(int(surplus), 1)) / math.log(1000)) ** 1.5
                eta = max(1, int(dist / speed))
                self.fleets.append(_SimFleet(opp_id, best.id, int(surplus), eta))
                src.ships -= surplus

    def score(self, player, transit_weight=TRANSIT_WEIGHT):
        own_prod = sum(p.production for p in self.planets if p.owner == player)
        opp_prod = sum(p.production for p in self.planets if 0 <= p.owner != player)
        own_transit = sum(f.ships for f in self.fleets if f.owner == player)
        opp_transit = sum(f.ships for f in self.fleets if 0 <= f.owner != player)
        base = (own_prod - opp_prod) + transit_weight * (own_transit - opp_transit)
        if EVAL_ENHANCED_ENABLED:
            own_planets = sum(1 for p in self.planets if p.owner == player)
            opp_planets = sum(1 for p in self.planets if 0 <= p.owner != player)
            own_ships = sum(p.ships for p in self.planets if p.owner == player)
            opp_ships = sum(p.ships for p in self.planets if 0 <= p.owner != player)
            base += PLANET_COUNT_WEIGHT * (own_planets - opp_planets)
            base += SHIP_COUNT_WEIGHT * (own_ships - opp_ships)
        return base

    def copy(self):
        ps = [_SimPlanet(p.id, p.owner, p.ships, p.production, p.x, p.y) for p in self.planets]
        fs = [_SimFleet(f.owner, f.target_id, f.ships, f.eta) for f in self.fleets]
        return _SimState(ps, fs)


def _build_sim_state(planets, raw_fleets, player):
    sim_planets = [_SimPlanet(p.id, p.owner, p.ships, p.production, p.x, p.y) for p in planets]
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
# Geometry helpers
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


def _get_planet_prod(pid, planets):
    for p in planets:
        if p.id == pid:
            return p.production
    return 0.0


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
# Phase detection (Experiment round 4, US3)
# ---------------------------------------------------------------------------

def _detect_phase(planets, targets, player):
    """Determine game phase: expansion, mid_game, or elimination.

    Returns (phase_name, gff_multiplier, disable_splinter).
    """
    non_neutral = [p for p in planets if p.owner >= 0]
    total = len(non_neutral)
    if total == 0:
        return "expansion", 1.0, False
    own = sum(1 for p in non_neutral if p.owner == player)
    pct = own / total
    owners = set(p.owner for p in planets if p.owner >= 0 and p.owner != player)
    if pct > 0.80 or len(owners) <= 1:
        return "elimination", 0.7, True
    elif pct > 0.40:
        return "mid_game", 0.85, False
    return "expansion", 1.0, False


# ---------------------------------------------------------------------------
# Candidate A (Round 8): global coordinated allocation
# ---------------------------------------------------------------------------

def _global_alloc_moves(active_sources, targets, comet_path_lookup, comet_planet_ids,
                         planets, initial_planets_map, angular_velocity):
    """Joint (source, target) assignment, replacing the per-planet greedy claim.

    Every (source, target) pair with a safe path is scored using the same
    ROI/reward blend as the per-planet path, with ROI normalized per-source
    (against that source's own best option, exactly as in the per-planet
    path) so each score reflects "how good is this target relative to this
    source's own alternatives" — a per-source utility that is meaningfully
    comparable across sources. Pairs are then assigned highest-score-first:
    a source whose top pick is already claimed by a higher-scoring pair
    falls through to its next-best remaining target ("redirect remaining
    sources"), giving a globally coherent assignment instead of one
    dependent on iteration order.

    A source's first surviving pair (i.e. its highest-scoring target not
    yet claimed by another source) is its "best_target", exactly as in the
    per-planet path — if that target is unaffordable or path-unsafe once
    enemy reinforcement is accounted for, the source gives up entirely
    (matching the per-planet path's behavior with MULTI_DISPATCH_ENABLED
    off), rather than trying a cheaper splinter target.
    """
    source_candidates = []  # source_idx -> [(t, bx, by, roi)]
    source_max_roi = []
    for mine, floor in active_sources:
        cands = []
        max_roi = 0.0
        for t in targets:
            speed_for_lead = fleet_speed(t.ships + 1)
            if t.id in comet_planet_ids:
                x_pred, y_pred, valid = _comet_two_pass(t, mine.x, mine.y, comet_path_lookup, speed_for_lead)
                if not valid:
                    continue
            else:
                x_pred, y_pred = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed_for_lead)
            if _path_safe(mine.x, mine.y, x_pred, y_pred, all_planets=planets, target_id=t.id, source_id=mine.id):
                roi = _roi(t, x_pred, y_pred, mine)
                cands.append((t, x_pred, y_pred, roi))
                if roi > max_roi:
                    max_roi = roi
        source_candidates.append(cands)
        source_max_roi.append(max_roi if max_roi > 0 else 1.0)

    pairs = []  # (score, source_idx, target, bx, by)
    for src_idx, cands in enumerate(source_candidates):
        for t, bx, by, roi in cands:
            roi_norm = roi / source_max_roi[src_idx]
            r_est = _reward_estimate(t, t.ships + 1)
            score = (1.0 - REWARD_ALPHA) * roi_norm + REWARD_ALPHA * r_est
            pairs.append((score, src_idx, t, bx, by))
    pairs.sort(key=lambda p: p[0], reverse=True)

    moves = []
    assigned_source = set()
    claimed = set()

    for score, src_idx, t, bx, by in pairs:
        if src_idx in assigned_source:
            continue
        if not MULTI_DISPATCH_ENABLED and t.id in claimed:
            continue

        mine, floor = active_sources[src_idx]
        best_target, bbx, bby = t, bx, by

        if best_target.owner == -1:
            ships_needed = best_target.ships + 1
        else:
            ships_needed, bbx, bby = _enemy_fleet_size(
                best_target, bbx, bby, mine.x, mine.y, initial_planets_map, angular_velocity
            )
            if not _path_safe(mine.x, mine.y, bbx, bby, all_planets=planets,
                               target_id=best_target.id, source_id=mine.id):
                assigned_source.add(src_idx)
                continue

        if mine.ships < ships_needed:
            assigned_source.add(src_idx)
            continue

        assigned_source.add(src_idx)
        claimed.add(best_target.id)
        angle = math.atan2(bby - mine.y, bbx - mine.x)
        moves.append([mine.id, angle, ships_needed])

    return moves


# ---------------------------------------------------------------------------
# Greedy dispatch
# ---------------------------------------------------------------------------

def _greedy_moves(obs, planets, my_planets, targets, initial_planets_map,
                  angular_velocity, raw_fleets, player, step):
    moves = []
    if PHASE_DETECTION_ENABLED:
        phase, phase_mult, disable_splinter = _detect_phase(planets, targets, player)
    else:
        phase, phase_mult, disable_splinter = "expansion", 1.0, False
    if DYNAMIC_GARRISON_ENABLED:
        gff = 1.0 + 1.5 * min(step / 400.0, 1.0) * phase_mult
    else:
        gff = 1.0 + 3.0 * min(step / 300.0, 1.0) * phase_mult

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

    # Track in-flight coverage per target (Exp 1: MULTI_DISPATCH)
    target_coverage = {}  # target_id -> total ships committed this turn

    # ------------------------------------------------------------------
    # Exp 6: Interceptor defense pre-pass
    # ------------------------------------------------------------------
    intercepted_planets = set()   # our planets already reinforced this turn
    intercept_senders = set()     # allied planets already used for intercept

    if DEFENSE_INTERCEPT_ENABLED:
        # Build per-fleet threat details: target planet, ships, eta
        fleet_threats = []  # (target_planet, fleet_ships, fleet_eta)
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
                    dist = math.hypot(f_x - p.x, f_y - p.y)
                    eta = max(1, int(dist / fleet_speed(f_ships)) + 1)
                    fleet_threats.append((p, f_ships, eta))

        # Sort by threat severity (largest fleet first), then by target production
        fleet_threats.sort(key=lambda x: -x[1] * _get_planet_prod(x[0], planets))

        for target_planet, fleet_ships, fleet_eta in fleet_threats:
            if target_planet.id in intercepted_planets:
                continue
            if target_planet.id in departing_this_turn:
                continue
            if target_planet.production < INTERCEPT_MIN_PROD:
                continue

            # Estimate garrison at arrival: current ships + production during transit
            garrison_at_arrival = target_planet.ships + target_planet.production * fleet_eta
            if fleet_ships <= garrison_at_arrival * INTERCEPT_MIN_THREAT_RATIO:
                continue

            # We will lose this planet — find nearest ally that can reinforce in time
            needed = int(fleet_ships - garrison_at_arrival) + 1

            best_source = None
            best_eta = float('inf')
            for src in my_planets:
                if src.id == target_planet.id:
                    continue
                if src.id in departing_this_turn:
                    continue
                if src.id in evacuate_this_turn:
                    continue
                if src.id in intercept_senders:
                    continue
                speed = fleet_speed(needed)
                dist = math.hypot(src.x - target_planet.x, src.y - target_planet.y)
                src_eta = max(1, int(dist / speed))
                if src_eta >= fleet_eta:
                    continue  # too late — arrives after enemy fleet
                # Check path safety
                if _path_safe(src.x, src.y, target_planet.x, target_planet.y,
                              all_planets=planets, target_id=target_planet.id, source_id=src.id):
                    if src_eta < best_eta:
                        best_eta = src_eta
                        best_source = src

            if best_source is None:
                continue

            # Check source can afford to send needed ships
            src_incoming = threat.get(best_source.id, 0)
            src_floor = max(best_source.production * gff, src_incoming)
            if best_source.ships - src_floor < needed:
                continue

            # Dispatch intercept
            angle = math.atan2(target_planet.y - best_source.y, target_planet.x - best_source.x)
            moves.append([best_source.id, angle, needed])
            intercepted_planets.add(target_planet.id)
            intercept_senders.add(best_source.id)

    claimed_targets = set()
    active_sources = []  # Candidate A: (mine, floor) deferred to _global_alloc_moves

    for mine in my_planets:
        if mine.id in departing_this_turn:
            continue
        if mine.id in intercept_senders:
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
            if MULTI_DISPATCH_ENABLED:
                target_coverage[best_evac.id] = target_coverage.get(best_evac.id, 0) + int(mine.ships)
            continue

        incoming = threat.get(mine.id, 0)

        # Experiment 2: reduced buffer when no active threat
        if THREAT_BUFFER_ENABLED:
            buffer = mine.production * 1 if incoming > 0 else 0
        else:
            buffer = mine.production * 2 if incoming > 0 else 0

        floor = max(mine.production * gff, incoming + buffer)
        if mine.ships - floor <= 0:
            continue

        # Candidate A: defer target-claiming to the global joint assignment pass
        if GLOBAL_ALLOC_ENABLED:
            active_sources.append((mine, floor))
            continue

        candidates = []
        for t in targets:
            # Experiment 1: skip exclusivity check — allow shared-target dispatch
            if not MULTI_DISPATCH_ENABLED and t.id in claimed_targets:
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

        # Experiment 1: check target coverage before claiming
        if MULTI_DISPATCH_ENABLED:
            existing = target_coverage.get(best_target.id, 0)
            if best_target.owner >= 0:
                # For enemy planets: check if combined fleet >= ships_needed
                if existing + ships_needed < ships_needed:  # always true if >0 ships
                    pass
        else:
            if mine.ships < ships_needed:
                continue

        # Experiment 3: splinter dispatch — if best target is unaffordable,
        # send surplus to nearest affordable neutral instead of skipping
        if SPLINTER_DISPATCH_ENABLED and step <= SPLINTER_WINDOW and not disable_splinter:
            if mine.ships < ships_needed and best_target.owner == -1:
                surplus = mine.ships - floor
                if surplus > 0:
                    # Find nearest affordable neutral not yet claimed
                    best_splinter = None
                    best_splinter_dist = float('inf')
                    best_splinter_pos = (0.0, 0.0)
                    for t, xp, yp in candidates:
                        if t.owner != -1:
                            continue
                        if not MULTI_DISPATCH_ENABLED and t.id in claimed_targets:
                            continue
                        needed = t.ships + 1
                        send = min(surplus, needed)
                        if send < t.ships + 1:
                            continue
                        dist = math.hypot(xp - mine.x, yp - mine.y)
                        if dist < best_splinter_dist:
                            best_splinter_dist = dist
                            best_splinter = t
                            best_splinter_pos = (xp, yp)
                            ships_needed = send
                    if best_splinter is not None:
                        best_target = best_splinter
                        bx, by = best_splinter_pos
        else:
            if mine.ships < ships_needed:
                continue

        # Final affordability check
        if not MULTI_DISPATCH_ENABLED and mine.ships < ships_needed:
            continue

        if MULTI_DISPATCH_ENABLED:
            target_coverage[best_target.id] = target_coverage.get(best_target.id, 0) + ships_needed

        claimed_targets.add(best_target.id)
        angle = math.atan2(by - mine.y, bx - mine.x)
        moves.append([mine.id, angle, ships_needed])

    if GLOBAL_ALLOC_ENABLED and active_sources:
        moves.extend(_global_alloc_moves(active_sources, targets, comet_path_lookup, comet_planet_ids,
                                          planets, initial_planets_map, angular_velocity))

    return moves


# ---------------------------------------------------------------------------
# Candidate C (Round 8): regroup-gradient repositioning
# ---------------------------------------------------------------------------

def _regroup_moves(my_planets, targets, planets, initial_planets_map, angular_velocity,
                    comet_path_lookup, comet_planet_ids, step, dispatching_ids):
    """Pre-emptive repositioning: move surplus from low-stress rear planets
    toward high-stress front planets, over safe orbital-lead paths only.

    "Stress" is the inverse-distance-weighted enemy ship mass reachable from
    a planet — a continuous proxy for how exposed/contested it is. Only
    planets that did not already dispatch via the greedy pass
    (`dispatching_ids`) and that hold surplus above the garrison floor are
    considered as regroup sources; their surplus flows toward the
    highest-stress owned planet that is more stressed than the source itself.
    """
    if len(my_planets) < 2:
        return []

    enemy_planets = [t for t in targets if t.owner >= 0]
    if not enemy_planets:
        return []

    def stress(p):
        return sum(e.ships / (math.hypot(p.x - e.x, p.y - e.y) + 1.0) for e in enemy_planets)

    stresses = {p.id: stress(p) for p in my_planets}

    if DYNAMIC_GARRISON_ENABLED:
        gff = 1.0 + 1.5 * min(step / 400.0, 1.0)
    else:
        gff = 1.0 + 3.0 * min(step / 300.0, 1.0)

    moves = []
    for rear in my_planets:
        if rear.id in dispatching_ids:
            continue
        floor = rear.production * gff
        surplus = rear.ships - floor
        if surplus < REGROUP_MIN_SURPLUS:
            continue

        fronts = [p for p in my_planets if p.id != rear.id and stresses[p.id] > stresses[rear.id]]
        if not fronts:
            continue
        front = max(fronts, key=lambda p: stresses[p.id])

        send = int(surplus)
        speed = fleet_speed(send)
        if front.id in comet_planet_ids:
            x_pred, y_pred, valid = _comet_two_pass(front, rear.x, rear.y, comet_path_lookup, speed)
            if not valid:
                continue
        else:
            x_pred, y_pred = _converged_orbit_lead(front, rear, initial_planets_map, angular_velocity, speed)

        if not _path_safe(rear.x, rear.y, x_pred, y_pred, all_planets=planets,
                           target_id=front.id, source_id=rear.id):
            continue

        angle = math.atan2(y_pred - rear.y, x_pred - rear.x)
        moves.append([rear.id, angle, send])

    return moves


# ---------------------------------------------------------------------------
# Candidate generation helpers
# ---------------------------------------------------------------------------

def _compute_top_k_targets(mine, targets, initial_planets_map, angular_velocity,
                            comet_path_lookup, comet_planet_ids, planets, k=BEAM_K):
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

def _gen_idle_rush_candidate(mine, top_k, greedy_dispatches, greedy_moves,
                              initial_planets_map, angular_velocity):
    """Additional beam candidate for an otherwise-idle planet (no greedy
    dispatch proposed this turn): rush its full fleet to the cheapest
    target it can outright afford (no garrison/floor reservation). The
    existing greedy/skip candidates are untouched, so _beam_search's
    10-turn forward sim picks this only if it beats waiting."""
    best = None  # (ships_needed, t, x_pred, y_pred)
    for roi, t, x_pred, y_pred in top_k:
        if t.owner == -1:
            ships_needed = int(t.ships) + 1
        else:
            ships_needed, x_pred, y_pred = _enemy_fleet_size(
                t, x_pred, y_pred, mine.x, mine.y, initial_planets_map, angular_velocity
            )
        if mine.ships < ships_needed:
            continue
        if best is None or ships_needed < best[0]:
            best = (ships_needed, t, x_pred, y_pred)

    if best is None:
        return None

    ships_needed, t, x_pred, y_pred = best
    dist = math.hypot(x_pred - mine.x, y_pred - mine.y)
    eta = max(1, int(dist / fleet_speed(ships_needed)))
    new_dispatch = (mine.id, t.id, ships_needed, eta)
    new_move = [mine.id, math.atan2(y_pred - mine.y, x_pred - mine.x), ships_needed]

    alt_dispatches = greedy_dispatches + [new_dispatch]
    alt_moves = greedy_moves + [new_move]
    return (alt_dispatches, alt_moves)


def _gen_beam_candidates(my_planets, targets, greedy_moves, planets, initial_planets_map,
                         angular_velocity, player, step):
    planets_map = {p.id: p for p in planets}
    comet_path_lookup = _build_comet_path_lookup_cached
    comet_planet_ids = set(comet_path_lookup.keys()) if comet_path_lookup else set()

    all_targets = targets
    greedy_dispatches = []
    for m in greedy_moves:
        d = _move_to_dispatch(m[0], m[1], m[2], planets_map, all_targets)
        if d:
            greedy_dispatches.append(d)

    greedy_dispatch_map = {d[0]: d for d in greedy_dispatches}

    candidates = [(greedy_dispatches, greedy_moves)]

    gff = 1.0 + 3.0 * min(step / 300.0, 1.0)

    for mine in my_planets:
        top_k = _compute_top_k_targets(mine, targets, initial_planets_map, angular_velocity,
                                        comet_path_lookup, comet_planet_ids, planets, k=BEAM_K)
        if not top_k:
            continue

        existing = greedy_dispatch_map.get(mine.id)
        if existing is None:
            is_opening = step <= OPENING_RUSH_WINDOW
            rush_enabled = CANDIDATE_1_ENABLED if is_opening else CANDIDATE_2_ENABLED
            if rush_enabled:
                rush = _gen_idle_rush_candidate(mine, top_k, greedy_dispatches, greedy_moves,
                                                 initial_planets_map, angular_velocity)
                if rush is not None:
                    candidates.append(rush)
            continue

        surplus = mine.ships - mine.production * gff
        if surplus <= 0:
            continue

        for roi, t, x_pred, y_pred in top_k:
            if existing[1] == t.id:
                continue

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

            alt_dispatches = [d for d in greedy_dispatches if d[0] != mine.id] + [new_dispatch]
            alt_moves = [m for m in greedy_moves if m[0] != mine.id] + [new_move]
            candidates.append((alt_dispatches, alt_moves))

        if MULTI_TURN_PLAN_ENABLED:
            # Skip candidate: this mine sends no fleet (wait-and-build)
            skip_dispatches = [d for d in greedy_dispatches if d[0] != mine.id]
            skip_moves = [m for m in greedy_moves if m[0] != mine.id]
            candidates.append((skip_dispatches, skip_moves))

    candidates.append(([], []))
    return candidates


def _beam_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    candidates = _gen_beam_candidates(my_planets, targets, greedy_moves, planets,
                                      initial_planets_map, angular_velocity, player, step)

    best_score = float('-inf')
    best_moves = greedy_moves

    for dispatches, moves in candidates:
        if (time.perf_counter() - t_start) * 1000 > SEARCH_TIMEOUT_MS:
            break
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        if WEIGHTED_EVAL_FIXED_ENABLED:
            score = 0.0
            for _ in range(SEARCH_DEPTH):
                state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
                own_prod = sum(p.production for p in state.planets if p.owner == player)
                opp_prod = sum(p.production for p in state.planets if 0 <= p.owner != player)
                score += (own_prod - opp_prod)
            own_transit = sum(f.ships for f in state.fleets if f.owner == player)
            opp_transit = sum(f.ships for f in state.fleets if 0 <= f.owner != player)
            score += TRANSIT_WEIGHT * (own_transit - opp_transit)
            if EVAL_ENHANCED_ENABLED:
                own_planets = sum(1 for p in state.planets if p.owner == player)
                opp_planets = sum(1 for p in state.planets if 0 <= p.owner != player)
                own_ships = sum(p.ships for p in state.planets if p.owner == player)
                opp_ships = sum(p.ships for p in state.planets if 0 <= p.owner != player)
                score += PLANET_COUNT_WEIGHT * (own_planets - opp_planets)
                score += SHIP_COUNT_WEIGHT * (own_ships - opp_ships)
        else:
            for _ in range(SEARCH_DEPTH):
                state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
            score = state.score(player, TRANSIT_WEIGHT)
        if score > best_score:
            best_score = score
            best_moves = moves

    return best_moves


# ---------------------------------------------------------------------------
# MCTS
# ---------------------------------------------------------------------------

def _mcts_rollout(state, player, depth):
    state = state.copy()
    for _ in range(depth):
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
            tgt = min(non_own, key=lambda q: math.hypot(p.x - q.x, p.y - q.y))
            dist = math.hypot(p.x - tgt.x, p.y - tgt.y)
            eta = max(1, int(dist / fleet_speed(int(surplus))))
            state.fleets.append(_SimFleet(player, tgt.id, int(surplus), eta))
            p.ships -= surplus
        state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
    return state.score(player, TRANSIT_WEIGHT)


def _mcts_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
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
        idx = max(range(n), key=ucb1)
        dispatches, moves = candidates[idx]
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        for _ in range(SEARCH_DEPTH):
            state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
        score = state.score(player, TRANSIT_WEIGHT)
        scores[idx] += score
        visits[idx] += 1
        if all(v > 0 for v in visits):
            break

    best_idx = max(range(n),
                   key=lambda i: scores[i] / visits[i] if visits[i] > 0 else float('-inf'))
    return candidates[best_idx][1]


# ---------------------------------------------------------------------------
# N-ply search
# ---------------------------------------------------------------------------

def _nply_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                 initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    planets_map = {p.id: p for p in planets}
    comet_path_lookup = _build_comet_path_lookup_cached
    comet_planet_ids = set(comet_path_lookup.keys()) if comet_path_lookup else set()

    gff = 1.0 + 3.0 * min(step / 300.0, 1.0)
    threat = {}

    greedy_move_map = {m[0]: m for m in greedy_moves}
    greedy_dispatch_map = {}
    for m in greedy_moves:
        d = _move_to_dispatch(m[0], m[1], m[2], planets_map, targets)
        if d:
            src_id, target_id, ships, eta = d
            greedy_dispatch_map[src_id] = (src_id, target_id, ships, eta, m[1])

    mine_options = {}
    for mine in my_planets:
        if mine.id not in greedy_dispatch_map:
            mine_options[mine.id] = [None]
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
        opts = [greedy_dispatch_map[mine.id]]
        for roi, t, x_pred, y_pred in top_k:
            if t.id == greedy_target_id:
                continue
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

    def gen_first_turn_combos():
        mines = list(my_planets)
        if not mines:
            return [([],  [])]
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
        if len(result) > NPLY_BEAM_WIDTH * 4:
            result = result[:NPLY_BEAM_WIDTH * 4]
        return result

    combos = gen_first_turn_combos()

    best_score = float('-inf')
    best_moves = greedy_moves

    for dispatches, moves in combos:
        if (time.perf_counter() - t_start) * 1000 > SEARCH_TIMEOUT_MS:
            break
        state = base_state.copy()
        _apply_dispatches(state, dispatches, player)
        for d in range(SEARCH_DEPTH):
            state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
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
# Candidate B (Round 8): anytime iterative-deepening beam search
# ---------------------------------------------------------------------------

def _score_state_at_depth(state, player, depth, t_start, budget_ms):
    """Simulate up to `depth` steps (or until `budget_ms` elapses) and score."""
    if WEIGHTED_EVAL_FIXED_ENABLED:
        score = 0.0
        for _ in range(depth):
            if (time.perf_counter() - t_start) * 1000 > budget_ms:
                break
            state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
            own_prod = sum(p.production for p in state.planets if p.owner == player)
            opp_prod = sum(p.production for p in state.planets if 0 <= p.owner != player)
            score += (own_prod - opp_prod)
        own_transit = sum(f.ships for f in state.fleets if f.owner == player)
        opp_transit = sum(f.ships for f in state.fleets if 0 <= f.owner != player)
        score += TRANSIT_WEIGHT * (own_transit - opp_transit)
        if EVAL_ENHANCED_ENABLED:
            own_planets = sum(1 for p in state.planets if p.owner == player)
            opp_planets = sum(1 for p in state.planets if 0 <= p.owner != player)
            own_ships = sum(p.ships for p in state.planets if p.owner == player)
            opp_ships = sum(p.ships for p in state.planets if 0 <= p.owner != player)
            score += PLANET_COUNT_WEIGHT * (own_planets - opp_planets)
            score += SHIP_COUNT_WEIGHT * (own_ships - opp_ships)
        return score

    for _ in range(depth):
        if (time.perf_counter() - t_start) * 1000 > budget_ms:
            break
        state.step(opponent_model=OPPONENT_MODEL_V2_ENABLED, player=player)
    return state.score(player, TRANSIT_WEIGHT)


def _deep_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                  initial_planets_map, angular_velocity, raw_fleets, player, step, t_start):
    """Anytime iterative-deepening beam: re-score the same candidate move-sets at
    progressively greater simulation depth while elapsed time stays under
    DEEP_SEARCH_BUDGET_MS, keeping the best result from the deepest pass that
    completed. Falls back to `greedy_moves` if no pass completes (FR-010)."""
    candidates = _gen_beam_candidates(my_planets, targets, greedy_moves, planets,
                                       initial_planets_map, angular_velocity, player, step)
    if not candidates:
        return greedy_moves

    best_moves = greedy_moves
    found_any = False
    depth = SEARCH_DEPTH

    while (time.perf_counter() - t_start) * 1000 < DEEP_SEARCH_BUDGET_MS:
        iter_best_score = float('-inf')
        iter_best_moves = None
        timed_out = False
        for dispatches, moves in candidates:
            if (time.perf_counter() - t_start) * 1000 > DEEP_SEARCH_BUDGET_MS:
                timed_out = True
                break
            state = base_state.copy()
            _apply_dispatches(state, dispatches, player)
            score = _score_state_at_depth(state, player, depth, t_start, DEEP_SEARCH_BUDGET_MS)
            if score > iter_best_score:
                iter_best_score = score
                iter_best_moves = moves

        if timed_out or iter_best_moves is None:
            break

        best_moves = iter_best_moves
        found_any = True
        depth += DEEP_SEARCH_DEPTH_STEP

    if not found_any:
        return greedy_moves
    return best_moves


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

    _build_comet_path_lookup_cached = _build_comet_path_lookup(obs)

    if not my_planets or not targets:
        return []

    greedy_moves = _greedy_moves(obs, planets, my_planets, targets, initial_planets_map,
                                 angular_velocity, raw_fleets, player, step)

    if REGROUP_ENABLED:
        comet_planet_ids = set(_build_comet_path_lookup_cached.keys())
        dispatching_ids = {m[0] for m in greedy_moves}
        greedy_moves = greedy_moves + _regroup_moves(
            my_planets, targets, planets, initial_planets_map, angular_velocity,
            _build_comet_path_lookup_cached, comet_planet_ids, step, dispatching_ids)

    base_state = _build_sim_state(planets, raw_fleets, player)

    if DEEP_SEARCH_ENABLED:
        return _deep_search(obs, greedy_moves, base_state, planets, my_planets, targets,
                            initial_planets_map, angular_velocity, raw_fleets, player, step, t_start)

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
