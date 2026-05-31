"""
Orbit Wars — agent_v41

Clean reimplementation of agent_v40. All game-mechanics calculations are
imported from helper.py (Principle VI Option B multi-file package).
Dead code from agent_v40 removed; variant flags replaced with locked-in values.

Proven mechanics inherited (unchanged logic, cleaner structure):
  - helper.path_safe: full-ray sun check + intermediate planet obstruction
  - helper.converged_orbit_lead + helper.comet_two_pass: accurate intercept
  - Comet evacuation (EVACUATE_THRESHOLD = 3 turns)
  - Threat-aware garrison floor (Candidate U): ANGLE_EPSILON = 0.1 rad
  - Production-squared ROI (Candidate R)
  - Reward-blend scoring (Candidate S, REWARD_ALPHA = 0.1)
  - GARRISON_FLOOR_FACTOR = 3 (Candidate O)
  - No range cap (Candidate Q)
  - Banking mode Variant B: suppress attacks when ships < my_prod * 25
  - Race-condition ship scaling for neutral targets (RACE_EPSILON = 0.2)
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet
import helper
from helper import (
    GARRISON_FLOOR_FACTOR,
    EVACUATE_THRESHOLD,
    REWARD_ALPHA,
    ANGLE_EPSILON,
    RACE_EPSILON,
    EPSILON,
)


def _do_evacuation(mine, planets, comet_planet_ids, comet_path_lookup,
                   initial_planets_map, angular_velocity, player, moves):
    best_evac = None
    best_score = float("-inf")
    best_pos = (0.0, 0.0)

    for p in planets:
        if p.id == mine.id:
            continue
        x_pred, y_pred, safe = helper.predict_target(
            p, mine, initial_planets_map, angular_velocity,
            comet_planet_ids, comet_path_lookup, planets,
        )
        if not safe:
            continue
        if p.owner == player:
            score = p.production / (math.hypot(mine.x - x_pred, mine.y - y_pred) + EPSILON)
        else:
            score = helper.roi(p, x_pred, y_pred, mine)
        if score > best_score:
            best_score = score
            best_evac = p
            best_pos = (x_pred, y_pred)

    if best_evac is not None:
        moves.append([mine.id, helper.angle_to(mine.x, mine.y, best_pos[0], best_pos[1]), mine.ships])


def agent(obs):
    moves = []

    # --- Observation parsing ---
    player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    initial_planets_raw = (obs.get("initial_planets", []) if isinstance(obs, dict)
                           else getattr(obs, "initial_planets", []))
    angular_velocity = (obs.get("angular_velocity", 0.0) if isinstance(obs, dict)
                        else getattr(obs, "angular_velocity", 0.0))
    raw_fleets = (obs.get("fleets", []) if isinstance(obs, dict)
                  else getattr(obs, "fleets", []))
    step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)

    # --- State derivation ---
    planets = [Planet(*p) for p in raw_planets]
    my_planets = [p for p in planets if p.owner == player]
    enemy_planets = [p for p in planets if p.owner >= 0 and p.owner != player]
    targets = [p for p in planets if p.owner != player]

    initial_planets_map = {Planet(*ip).id: Planet(*ip) for ip in initial_planets_raw}

    # --- Threat detection (Candidate U) ---
    threat = {}
    for f in raw_fleets:
        if isinstance(f, (list, tuple)):
            f_owner, f_x, f_y, f_angle, f_ships = f[1], float(f[2]), float(f[3]), float(f[4]), int(f[6])
        else:
            f_owner, f_x, f_y, f_angle, f_ships = f.owner, f.x, f.y, f.angle, f.ships
        if f_owner == player:
            continue
        for p in my_planets:
            expected = helper.angle_to(f_x, f_y, p.x, p.y)
            if helper.angle_diff(f_angle, expected) < ANGLE_EPSILON:
                threat[p.id] = threat.get(p.id, 0) + f_ships

    # --- Comet setup ---
    comet_path_lookup = helper.build_comet_path_lookup(obs)
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

    # --- Banking phase check ---
    if helper.banking_mode(my_planets, enemy_planets, step):
        for mine in my_planets:
            if mine.id not in evacuate_this_turn or mine.ships < 1:
                continue
            _do_evacuation(mine, planets, comet_planet_ids, comet_path_lookup,
                           initial_planets_map, angular_velocity, player, moves)
        return moves

    # --- Comet evacuation ---
    for mine in my_planets:
        if mine.id in departing_this_turn or mine.id not in evacuate_this_turn:
            continue
        if mine.ships < 1:
            continue
        _do_evacuation(mine, planets, comet_planet_ids, comet_path_lookup,
                       initial_planets_map, angular_velocity, player, moves)

    # --- Best-sender assignment ---
    best_sender = {}
    for t in targets:
        best_score = float("inf")
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

    # --- Attack loop ---
    for mine in my_planets:
        if mine.id in departing_this_turn or mine.id in evacuate_this_turn:
            continue

        candidates = []
        for t in targets:
            if best_sender.get(t.id) != mine.id:
                continue
            x_pred, y_pred, safe = helper.predict_target(
                t, mine, initial_planets_map, angular_velocity,
                comet_planet_ids, comet_path_lookup, planets,
            )
            if safe:
                candidates.append((t, x_pred, y_pred))

        if not candidates:
            continue

        roi_scores = [(helper.roi(t, bx, by, mine), t, bx, by) for t, bx, by in candidates]
        max_roi = max(r for r, _, _, _ in roi_scores) or 1.0

        def blended_key(item, _max_roi=max_roi):
            r, t, bx, by = item
            roi_norm = r / _max_roi
            r_est = helper.reward_estimate(t, t.ships + 1)
            return (1.0 - REWARD_ALPHA) * roi_norm + REWARD_ALPHA * r_est

        _, best_target, bx, by = max(roi_scores, key=blended_key)

        enemy_inc = 0
        if best_target.owner == -1:
            enemy_inc = helper.enemy_incoming(bx, by, raw_fleets, player)
        ships_needed = max(best_target.ships + 1, best_target.ships + enemy_inc + 1)

        if mine.ships < ships_needed:
            continue

        moves.append([mine.id, helper.angle_to(mine.x, mine.y, bx, by), ships_needed])

    return moves
