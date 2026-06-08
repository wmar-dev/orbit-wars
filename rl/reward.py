"""
Hybrid reward: per-turn dense (ship advantage) + terminal win/loss bonus.
"""

import math

TERMINAL_WIN = 1.0
TERMINAL_LOSS = -1.0
TERMINAL_DRAW = 0.0

DENSE_SCALE = 0.05


def compute_dense_reward(obs, player_id):
    """Compute normalized ship-count advantage as dense reward signal.

    Returns value in [-1, 1] representing relative ship advantage
    (planets + fleets). Negative means losing, positive means winning.
    """
    raw_planets = obs.planets
    raw_fleets = getattr(obs, "fleets", [])

    my_ships = sum(p[5] for p in raw_planets if p[1] == player_id)
    enemy_ships = sum(p[5] for p in raw_planets if p[1] not in (player_id, -1))

    my_fleets = sum(f[6] for f in raw_fleets if f[1] == player_id)
    enemy_fleets = sum(f[6] for f in raw_fleets if f[1] not in (player_id, -1))

    my_total = my_ships + my_fleets
    enemy_total = enemy_ships + enemy_fleets
    total = my_total + enemy_total + 1  # avoid division by zero

    return (my_total - enemy_total) / total


def compute_terminal_reward(final_rewards, player):
    """Sparse terminal reward: +1 win, -1 loss, 0 draw."""
    n = len(final_rewards)
    my_r = final_rewards[player]
    if n == 2:
        other = final_rewards[1 - player]
        if my_r > other:
            return TERMINAL_WIN
        if my_r < other:
            return TERMINAL_LOSS
        return TERMINAL_DRAW
    sorted_r = sorted(final_rewards, reverse=True)
    positions = [i + 1 for i, r in enumerate(sorted_r) if r == my_r]
    rank = sum(positions) / len(positions)
    return 1.0 - 2.0 * (rank - 1.0) / (n - 1.0)
