"""
BC data collection: run v38 vs opponent, collect (obs, action) pairs.
"""

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from kaggle_environments import make

from rl.obs import encode_obs, _angle_from_center
from agent_v38 import agent as v38_agent

GARRISON_FLOOR_FACTOR = 3


def _get_surplus(planet, player_id):
    pid, owner, x, y, radius, ships, prod = planet
    if owner != player_id:
        return 0
    floor = max(GARRISON_FLOOR_FACTOR * prod, 1)
    return max(ships - floor, 0)


def encode_moves_to_action(moves, obs, player_id):
    """Convert v38 move list to action array (15,)"""
    raw_planets = obs.planets
    sorted_planets = sorted(raw_planets, key=lambda p: _angle_from_center(p[2], p[3]))
    planet_id_to_slot = {p[0]: i for i, p in enumerate(sorted_planets)}

    action = np.zeros(15, dtype=np.int32)
    if not moves:
        return action

    # Sort moves by source surplus descending (most important first)
    def sort_key(m):
        src_id = m[0]
        slot = planet_id_to_slot.get(src_id, 0)
        if slot < len(sorted_planets):
            return -_get_surplus(sorted_planets[slot], player_id)
        return 0

    sorted_moves = sorted(moves, key=sort_key)

    for fleet_idx, (src_id, angle, ships) in enumerate(sorted_moves[:5]):
        offset = fleet_idx * 3

        # Source slot
        src_slot = planet_id_to_slot.get(src_id, 0)
        action[offset] = src_slot

        # Target planet: find closest by angle from source
        src_p = next(p for p in sorted_planets if p[0] == src_id)
        src_x, src_y = src_p[2], src_p[3]

        best_tgt = 0
        best_diff = float('inf')
        for slot, p in enumerate(sorted_planets):
            if p[0] == src_id:
                continue
            tgt_a = math.atan2(p[3] - src_y, p[2] - src_x)
            diff = abs(math.atan2(math.sin(angle - tgt_a), math.cos(angle - tgt_a)))
            if diff < best_diff:
                best_diff = diff
                best_tgt = slot
        action[offset + 1] = best_tgt

        # Fraction
        prod = src_p[6]
        garrison = max(GARRISON_FLOOR_FACTOR * prod, 1)
        surplus = src_p[5] - garrison
        if surplus > 0:
            frac_idx = min(int((ships / surplus) / 0.25), 3)
        else:
            frac_idx = 3
        action[offset + 2] = frac_idx

    return action


def collect(games=1000, opponent="random", seed=0, output="rl/data/demos.npz"):
    print(f"Collecting {games} games of v38 vs {opponent}...")

    all_obs = []
    all_actions = []

    env = make("orbit_wars", configuration={"seed": seed}, debug=False)
    trainer = env.train([None, opponent])

    for game_idx in range(games):
        obs = trainer.reset()
        player_id = obs.player
        done = False
        game_samples = 0

        while not done:
            vec, _ = encode_obs(obs, player_id)
            moves = v38_agent(obs)
            action = encode_moves_to_action(moves, obs, player_id)
            all_obs.append(vec)
            all_actions.append(action)
            game_samples += 1
            obs, reward, done, info = trainer.step(moves)

        if (game_idx + 1) % 100 == 0:
            print(f"  Game {game_idx+1}/{games}, samples={len(all_obs)}, steps={game_samples}")

    try:
        env.close()
    except AttributeError:
        pass

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    obs_arr = np.array(all_obs, dtype=np.float32)
    act_arr = np.array(all_actions, dtype=np.int32)

    print(f"Saving {len(all_obs)} samples -> {out_path}")
    np.savez_compressed(out_path, obs=obs_arr, actions=act_arr)
    print(f"  obs shape: {obs_arr.shape}, actions shape: {act_arr.shape}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--opponent", type=str, default="random")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=str, default="rl/data/demos.npz")
    args = parser.parse_args()
    collect(**vars(args))
