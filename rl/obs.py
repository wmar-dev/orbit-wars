"""
Observation encoder for Orbit Wars RL training (full-board).

Layout (560 floats):
  [0:280]    40 planet slots × 7 features
  [280:320]   8 fleet-hot slots × 5 features
  [320:446]  42 fleet-summary bins × 3 features
  [446:476]  10 comet slots × 3 features
  [476:480]   4 global features
  [480:560]  80 mask bits (float32 0/1)

Planet features (7): owner_self, owner_enemy, owner_neutral, x/100, y/100, ships/500, production/10
Fleet-hot features (5): owner_self, owner_enemy, owner_neutral, x/100, y/100
Fleet-summary (3): ship_count/500, angle_sin, angle_cos
Comet features (3): x/100, y/100, ships/500
Globals: player_id/3, angular_velocity*10, step/200, planet_count/40
Mask bits: [0:40] source-valid, [40:80] target-valid
"""

import math
import numpy as np

MAX_PLANETS = 40
FLEET_HOT_SLOTS = 8
FLEET_SUMMARY_BINS = 42
FLEET_TOTAL = FLEET_HOT_SLOTS + FLEET_SUMMARY_BINS
MAX_COMETS = 10

PLANET_FEATURES = 7
FLEET_HOT_FEATURES = 5
FLEET_SUMMARY_FEATURES = 3
COMET_FEATURES = 3
GLOBAL_FEATURES = 4
MASK_BITS = 80

_P_PLANETS = 0
_P_FLEET_HOT = MAX_PLANETS * PLANET_FEATURES
_P_FLEET_SUM = _P_FLEET_HOT + FLEET_HOT_SLOTS * FLEET_HOT_FEATURES
_P_COMETS = _P_FLEET_SUM + FLEET_SUMMARY_BINS * FLEET_SUMMARY_FEATURES
_P_GLOBALS = _P_COMETS + MAX_COMETS * COMET_FEATURES
_P_MASK = _P_GLOBALS + GLOBAL_FEATURES

OBS_SIZE = _P_MASK + MASK_BITS

GARRISON_FLOOR_FACTOR = 3

NUM_FLEETS_PER_TURN = 5
NUM_ACTION_VALUES = NUM_FLEETS_PER_TURN * 3  # 15

_FRACTIONS = [0.25, 0.5, 0.75, 1.0]


def _angle_from_center(x, y, cx=50.0, cy=50.0):
    return math.atan2(y - cy, x - cx)


def _dist_from_center(x, y, cx=50.0, cy=50.0):
    return math.hypot(x - cx, y - cy)


def encode_obs(obs, player_id: int) -> tuple[np.ndarray, np.ndarray]:
    vec = np.zeros(OBS_SIZE, dtype=np.float32)
    mask = np.zeros(MASK_BITS, dtype=bool)

    raw_planets = obs.planets
    raw_fleets = obs.fleets
    raw_comets = obs.comets

    # ----- Planets -----
    sorted_planets = sorted(raw_planets, key=lambda p: _angle_from_center(p[2], p[3]))
    planet_id_to_slot = {}
    for slot, p in enumerate(sorted_planets[:MAX_PLANETS]):
        pid, owner, x, y, radius, ships, production = p
        planet_id_to_slot[pid] = slot
        base = _P_PLANETS + slot * PLANET_FEATURES
        if owner == player_id:
            vec[base] = 1.0
        elif owner == -1:
            vec[base + 2] = 1.0
        else:
            vec[base + 1] = 1.0
        vec[base + 3] = x / 100.0
        vec[base + 4] = y / 100.0
        vec[base + 5] = ships / 500.0
        vec[base + 6] = production / 10.0
        mask[slot + MAX_PLANETS] = True  # target-valid

    # ----- Fleets: hot slots (closest 8) -----
    def fleet_dist(f):
        return _dist_from_center(f[2], f[3])

    sorted_fleets = sorted(raw_fleets, key=fleet_dist)
    for slot, f in enumerate(sorted_fleets[:FLEET_HOT_SLOTS]):
        fid, owner, x, y, angle, from_pid, ships = f
        base = _P_FLEET_HOT + slot * FLEET_HOT_FEATURES
        if owner == player_id:
            vec[base] = 1.0
        elif owner == -1:
            vec[base + 2] = 1.0
        else:
            vec[base + 1] = 1.0
        vec[base + 3] = x / 100.0
        vec[base + 4] = y / 100.0

    # ----- Fleets: summary bins (distance-based, binned by owner + distance) -----
    n_bins_per_owner = FLEET_SUMMARY_BINS // 3  # 14 bins per owner
    for owner_type, owner_val in [(0, player_id), (1, -1), (2, None)]:
        if owner_val is None:
            filtered = [f for f in raw_fleets if f[1] not in (player_id, -1)]
        else:
            filtered = [f for f in raw_fleets if f[1] == owner_val]
        # Assign bins by distance from center
        for f in filtered:
            fid, owner, x, y, angle, from_pid, ships = f
            dist = _dist_from_center(x, y)
            bin_idx = min(int(dist / (100.0 / n_bins_per_owner)), n_bins_per_owner - 1)
            slot = owner_type * n_bins_per_owner + bin_idx
            base = _P_FLEET_SUM + slot * FLEET_SUMMARY_FEATURES
            vec[base] += ships / 500.0
            vec[base + 1] += math.sin(angle)
            vec[base + 2] += math.cos(angle)

    # ----- Comets -----
    def comet_sort_key(c):
        if isinstance(c, dict):
            return c.get('path_index', 999)
        return getattr(c, 'path_index', 999)

    sorted_comets = sorted(raw_comets, key=comet_sort_key)
    for slot, c in enumerate(sorted_comets[:MAX_COMETS]):
        if isinstance(c, dict):
            paths = c.get('paths', [])
            idx = c.get('path_index', 0)
        else:
            paths = getattr(c, 'paths', [])
            idx = getattr(c, 'path_index', 0)
        if not paths:
            continue
        cx_sum, cy_sum = 0.0, 0.0
        count = 0
        for planet_path in paths:
            if not planet_path:
                continue
            step_idx = min(idx, len(planet_path) - 1)
            pos = planet_path[step_idx]
            cx_sum += pos[0]
            cy_sum += pos[1]
            count += 1
        if count == 0:
            continue
        cx = cx_sum / count
        cy = cy_sum / count
        cships = float(count) * 5.0
        base = _P_COMETS + slot * COMET_FEATURES
        vec[base] = cx / 100.0
        vec[base + 1] = cy / 100.0
        vec[base + 2] = cships / 500.0

    # ----- Globals -----
    vec[_P_GLOBALS] = player_id / 3.0
    vec[_P_GLOBALS + 1] = float(obs.angular_velocity) * 10.0
    step = obs.step if hasattr(obs, 'step') else 0
    vec[_P_GLOBALS + 2] = step / 200.0
    vec[_P_GLOBALS + 3] = len(raw_planets) / MAX_PLANETS

    # ----- Action mask (source-valid: slots 0-39, target-valid: slots 40-79) -----
    for slot, p in enumerate(sorted_planets[:MAX_PLANETS]):
        pid, owner, x, y, radius, ships, production = p
        if owner == player_id:
            garrison = max(GARRISON_FLOOR_FACTOR * production, 1)
            surplus = ships - garrison
            if surplus > 0:
                mask[slot] = True  # source-valid

    vec[_P_MASK:_P_MASK + MASK_BITS] = mask.astype(np.float32)

    return vec, mask


def decode_action(action: np.ndarray, obs, player_id: int) -> list:
    """
    Decode a 15-value action array (5 fleet slots × 3 values) into kaggle move list.
    Each fleet slot: [src_slot, tgt_slot, frac_idx].
    Max 1 fleet per source planet per turn.
    """
    raw_planets = obs.planets
    sorted_planets = sorted(raw_planets, key=lambda p: _angle_from_center(p[2], p[3]))
    moves = []
    used_src_ids = set()

    for fleet_idx in range(NUM_FLEETS_PER_TURN):
        offset = fleet_idx * 3
        src_slot = int(action[offset])
        tgt_slot = int(action[offset + 1])
        frac_idx = int(action[offset + 2])

        if src_slot == tgt_slot:
            continue
        if src_slot >= len(sorted_planets) or tgt_slot >= len(sorted_planets):
            continue

        src_p = sorted_planets[src_slot]
        tgt_p = sorted_planets[tgt_slot]
        src_pid, src_owner = src_p[0], src_p[1]
        src_x, src_y = src_p[2], src_p[3]
        src_ships = src_p[5]
        src_prod = src_p[6]
        tgt_x, tgt_y = tgt_p[2], tgt_p[3]

        if src_owner != player_id:
            continue
        if src_pid in used_src_ids:
            continue

        garrison = max(GARRISON_FLOOR_FACTOR * src_prod, 1)
        surplus = src_ships - garrison
        if surplus <= 0:
            continue

        fraction = _FRACTIONS[min(frac_idx, len(_FRACTIONS) - 1)]
        num_ships = max(1, int(surplus * fraction))
        angle = math.atan2(tgt_y - src_y, tgt_x - src_x)
        moves.append([src_pid, angle, num_ships])
        used_src_ids.add(src_pid)

    return moves
