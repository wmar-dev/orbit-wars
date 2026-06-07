"""
T004: Observation encoder for Orbit Wars RL training.

Converts a raw kaggle-environments observation into a fixed-size float32
vector (319 values) plus a boolean action-validity mask (52 values).

Layout (see data-model.md):
  [0:84]    12 planet slots × 7 features
  [84:234]  30 fleet slots  × 5 features
  [234:264] 10 comet slots  × 3 features
  [264:267] 3 global features
  [267:319] 52 boolean mask bits (float32 0/1)

Planet features per slot (7):
  owner_self, owner_enemy, owner_neutral, x/100, y/100, ships/500, production/10

Fleet features per slot (5):
  owner_self, owner_enemy, owner_neutral, x/100, y/100

Comet features per slot (3):
  x/100, y/100, ships/500

Globals (3):
  player_id/3, angular_velocity*10, step/200

Mask bits (52):
  [0:12]  source-valid: player owns that planet slot AND has surplus ships (>0 after garrison)
  [12:24] target-valid: slot is occupied and different index from valid sources
  [24:52] reserved zeros
"""

import math
import numpy as np

MAX_PLANETS = 12
MAX_FLEETS  = 30
MAX_COMETS  = 10

PLANET_FEATURES = 7
FLEET_FEATURES  = 5
COMET_FEATURES  = 3
GLOBAL_FEATURES = 3
MASK_BITS       = 52

OBS_SIZE = (MAX_PLANETS * PLANET_FEATURES
            + MAX_FLEETS * FLEET_FEATURES
            + MAX_COMETS * COMET_FEATURES
            + GLOBAL_FEATURES
            + MASK_BITS)  # 319

# Offsets into the flat vector
_P_START = 0
_F_START = MAX_PLANETS * PLANET_FEATURES           # 84
_C_START = _F_START + MAX_FLEETS * FLEET_FEATURES   # 234
_G_START = _C_START + MAX_COMETS * COMET_FEATURES   # 264
_M_START = _G_START + GLOBAL_FEATURES               # 267

GARRISON_FLOOR_FACTOR = 3  # mirrored from agent_v38


def _angle_from_center(x, y, cx=50.0, cy=50.0):
    """Angle of (x,y) relative to board center — used for deterministic sort."""
    return math.atan2(y - cy, x - cx)


def encode_obs(obs, player_id: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Encode a kaggle orbit_wars observation into a fixed-size float32 vector
    and a boolean action mask.

    Args:
        obs: kaggle_environments Struct with .planets, .fleets, .comets,
             .initial_planets, .angular_velocity, .step
        player_id: int, the player index being trained (0 or 1)

    Returns:
        vec:  np.ndarray shape (319,) dtype float32
        mask: np.ndarray shape (52,)  dtype bool
              mask[0:12]  = source-valid flags
              mask[12:24] = target-valid flags
    """
    vec  = np.zeros(OBS_SIZE, dtype=np.float32)
    mask = np.zeros(MASK_BITS, dtype=bool)

    raw_planets = obs.planets  # list of [id, owner, x, y, radius, ships, production]
    raw_fleets  = obs.fleets   # list of [id, owner, x, y, angle, from_planet_id, ships]
    raw_comets  = obs.comets   # list with .paths, .path_index attributes (or list)

    # ----- Planets -----
    # Sort by angle from center for deterministic ordering
    sorted_planets = sorted(
        raw_planets,
        key=lambda p: _angle_from_center(p[2], p[3])
    )

    planet_id_to_slot = {}
    for slot, p in enumerate(sorted_planets[:MAX_PLANETS]):
        pid, owner, x, y, radius, ships, production = p
        planet_id_to_slot[pid] = slot
        base = _P_START + slot * PLANET_FEATURES
        # owner one-hot
        if owner == player_id:
            vec[base + 0] = 1.0
        elif owner == -1:
            vec[base + 2] = 1.0
        else:
            vec[base + 1] = 1.0
        vec[base + 3] = x / 100.0
        vec[base + 4] = y / 100.0
        vec[base + 5] = ships / 500.0
        vec[base + 6] = production / 10.0
        # mask: slot is occupied
        mask[slot + MAX_PLANETS] = True  # target valid (index 12–23)

    # ----- Fleets -----
    # Sort by distance-squared from obs center (50, 50) — proxy for "closest first"
    def fleet_sort_key(f):
        return (f[2] - 50.0) ** 2 + (f[3] - 50.0) ** 2

    sorted_fleets = sorted(raw_fleets, key=fleet_sort_key)
    for slot, f in enumerate(sorted_fleets[:MAX_FLEETS]):
        fid, owner, x, y, angle, from_pid, ships = f
        base = _F_START + slot * FLEET_FEATURES
        if owner == player_id:
            vec[base + 0] = 1.0
        elif owner == -1:
            vec[base + 2] = 1.0
        else:
            vec[base + 1] = 1.0
        vec[base + 3] = x / 100.0
        vec[base + 4] = y / 100.0

    # ----- Comets -----
    # Comet structure: paths is a list of planet-paths (one per comet planet).
    # Each planet-path is a list of [x, y] positions along the orbit.
    # path_index is how many steps remain (soonest-expiring = lowest path_index).
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

        # Use centroid of all comet-planet positions at current step
        cx_sum, cy_sum = 0.0, 0.0
        count = 0
        for planet_path in paths:
            if not planet_path:
                continue
            step_idx = min(idx, len(planet_path) - 1)
            pos = planet_path[step_idx]  # [x, y]
            cx_sum += pos[0]
            cy_sum += pos[1]
            count += 1

        if count == 0:
            continue

        cx = cx_sum / count
        cy = cy_sum / count
        cships = float(count) * 5.0  # approximate: comet ships proportional to planet count

        base = _C_START + slot * COMET_FEATURES
        vec[base + 0] = cx / 100.0
        vec[base + 1] = cy / 100.0
        vec[base + 2] = cships / 500.0

    # ----- Globals -----
    vec[_G_START + 0] = player_id / 3.0
    vec[_G_START + 1] = float(obs.angular_velocity) * 10.0
    step = obs.step if hasattr(obs, 'step') else 0
    vec[_G_START + 2] = step / 200.0

    # ----- Action mask (source-valid: slots 0–11) -----
    for slot, p in enumerate(sorted_planets[:MAX_PLANETS]):
        pid, owner, x, y, radius, ships, production = p
        if owner == player_id:
            garrison = max(GARRISON_FLOOR_FACTOR * production, 1)
            surplus = ships - garrison
            if surplus > 0:
                mask[slot] = True  # source valid

    # Append mask bits into vector (float32)
    vec[_M_START:_M_START + MASK_BITS] = mask.astype(np.float32)

    return vec, mask


def decode_action(action: np.ndarray, obs, player_id: int) -> list:
    """
    Decode a factored discrete action [src_slot, tgt_slot, fraction_idx] into
    a list of fleet dispatch commands for kaggle-environments.

    Each command is [source_id, target_angle, num_ships] matching the format
    used by the existing agent files (e.g. agent_v38.py).

    fraction_idx: 0=25%, 1=50%, 2=75%, 3=100% of surplus
    """
    FRACTIONS = [0.25, 0.5, 0.75, 1.0]  # no-op removed; always send ships

    src_slot, tgt_slot, frac_idx = int(action[0]), int(action[1]), int(action[2])
    fraction = FRACTIONS[min(frac_idx, len(FRACTIONS) - 1)]

    if src_slot == tgt_slot:
        return []

    raw_planets = obs.planets
    sorted_planets = sorted(raw_planets, key=lambda p: _angle_from_center(p[2], p[3]))

    if src_slot >= len(sorted_planets) or tgt_slot >= len(sorted_planets):
        return []

    src_p = sorted_planets[src_slot]
    tgt_p = sorted_planets[tgt_slot]

    src_pid, src_owner = src_p[0], src_p[1]
    src_x,   src_y    = src_p[2], src_p[3]
    src_ships = src_p[5]
    src_prod  = src_p[6]
    tgt_x,   tgt_y    = tgt_p[2], tgt_p[3]

    if src_owner != player_id:
        return []

    garrison = max(GARRISON_FLOOR_FACTOR * src_prod, 1)
    surplus = src_ships - garrison
    if surplus <= 0:
        return []

    num_ships = max(1, int(surplus * fraction))
    angle = math.atan2(tgt_y - src_y, tgt_x - src_x)

    return [[src_pid, angle, num_ships]]
