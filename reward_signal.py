"""
Orbit Wars - Per-Turn Reward Signal Module

Computes a scalar reward in [-1, 1] for a specified player at each game turn,
suitable for offline RL dataset collection and reward-guided agent scoring.

Reward components (all normalized, all weighted):
  - capture_bonus:     planet captures this turn (scaled by production value)
  - production_delta:  change in total owned production capacity
  - ship_delta:        change in total owned ships (on planets + in flight)
  - terminal:          rank-based terminal signal on the final turn only

Usage:
  from reward_signal import compute_reward, zero_reward, RewardConfig
"""

import math

from kaggle_environments.envs.orbit_wars.orbit_wars import Fleet, Planet

# ---------------------------------------------------------------------------
# RewardConfig — single source of truth for all tunable weights/scales
# ---------------------------------------------------------------------------

W_CAPTURE = 0.5       # weight for planet-capture bonus component
W_PRODUCTION = 0.3    # weight for production-delta component
W_SHIP = 0.2          # weight for ship-delta component

CAPTURE_SCALE = 10.0  # normalises capture bonus to ~[-1, 1]
PROD_SCALE = 5.0      # normalises production delta to ~[-1, 1]
SHIP_SCALE = 20.0     # normalises ship delta to ~[-1, 1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def zero_reward() -> dict:
    """Return a zeroed TurnReward dict (used on turn 0 when no prev_obs exists)."""
    return {
        "capture_bonus": 0.0,
        "production_delta": 0.0,
        "ship_delta": 0.0,
        "terminal": None,
        "total": 0.0,
    }


def _parse_obs(obs) -> tuple[list, list]:
    """Extract (planets, fleets) from a raw obs dict or observation object.

    Raises ValueError with a descriptive message if required fields are missing.
    """
    if isinstance(obs, dict):
        missing = [f for f in ("planets", "fleets", "player", "step") if f not in obs]
        if missing:
            step = obs.get("step", "?")
            raise ValueError(
                f"reward_signal: observation at step {step} is missing required fields: {missing}"
            )
        raw_planets = obs["planets"]
        raw_fleets = obs["fleets"]
    else:
        for field in ("planets", "fleets", "player", "step"):
            if not hasattr(obs, field):
                raise ValueError(
                    f"reward_signal: observation object missing attribute '{field}'"
                )
        raw_planets = obs.planets
        raw_fleets = obs.fleets

    planets = [Planet(*p) for p in raw_planets]
    fleets = [Fleet(*f) for f in raw_fleets]
    return planets, fleets


def _owned_ships(planets: list, fleets: list, player: int) -> float:
    """Total ships owned by player: on planets + in-flight fleets."""
    return (
        sum(p.ships for p in planets if p.owner == player)
        + sum(f.ships for f in fleets if f.owner == player)
    )


def _owned_production(planets: list, player: int) -> float:
    return sum(p.production for p in planets if p.owner == player)


# ---------------------------------------------------------------------------
# Reward components
# ---------------------------------------------------------------------------

def _capture_bonus(planets_prev: list, planets_now: list, player: int) -> float:
    """Normalised bonus for planets captured this turn."""
    prev_map = {p.id: p for p in planets_prev}
    bonus = sum(
        p.production
        for p in planets_now
        if p.owner == player and prev_map.get(p.id) is not None
        and prev_map[p.id].owner != player
    )
    return max(-1.0, min(1.0, bonus / CAPTURE_SCALE))


def _production_delta(
    planets_prev: list, planets_now: list, player: int
) -> float:
    """Normalised change in owned production rate."""
    delta = _owned_production(planets_now, player) - _owned_production(planets_prev, player)
    return max(-1.0, min(1.0, delta / PROD_SCALE))


def _ship_delta(
    planets_prev: list, fleets_prev: list,
    planets_now: list, fleets_now: list,
    player: int,
) -> float:
    """Normalised change in total owned ships (on planets + in flight)."""
    delta = (
        _owned_ships(planets_now, fleets_now, player)
        - _owned_ships(planets_prev, fleets_prev, player)
    )
    return max(-1.0, min(1.0, delta / SHIP_SCALE))


def _terminal_reward(final_rewards: list[float], player: int) -> float:
    """Rank-based terminal reward: 1 - 2*(rank-1)/(N-1).

    Rank 1 = highest final_reward → +1.0.
    Rank N = lowest → -1.0.
    Ties receive the same rank (average rank of tied positions).
    """
    n = len(final_rewards)
    if n == 1:
        return 1.0
    if n == 2:
        # Simple win/loss with tie at 0
        r0, r1 = final_rewards
        my_r = final_rewards[player]
        other_r = final_rewards[1 - player] if player == 0 else final_rewards[0]
        if my_r > other_r:
            return 1.0
        if my_r < other_r:
            return -1.0
        return 0.0

    # General N-player: assign ranks with tie handling
    sorted_rewards = sorted(final_rewards, reverse=True)
    my_r = final_rewards[player]

    # Find rank positions of all players with same reward
    positions = [i + 1 for i, r in enumerate(sorted_rewards) if r == my_r]
    rank = sum(positions) / len(positions)  # average rank for ties

    return 1.0 - 2.0 * (rank - 1.0) / (n - 1.0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_reward(
    prev_obs,
    curr_obs,
    player: int,
    final_rewards: list[float] | None = None,
    num_players: int = 2,
) -> dict:
    """Compute a TurnReward dict for `player` at the current turn.

    Args:
        prev_obs:       Observation from the previous turn (None on turn 0).
        curr_obs:       Observation from the current turn.
        player:         Player index to compute reward for.
        final_rewards:  List of final game rewards (non-None on terminal turn only).
        num_players:    Total number of players in the game.

    Returns:
        dict with keys: capture_bonus, production_delta, ship_delta, terminal, total.
        All values in [-1, 1]. terminal is None on non-terminal turns.
        On the terminal turn, total == terminal (per-turn components are not added).

    Raises:
        ValueError if curr_obs is missing required fields.
    """
    if prev_obs is None:
        return zero_reward()

    planets_prev, fleets_prev = _parse_obs(prev_obs)
    planets_now, fleets_now = _parse_obs(curr_obs)

    capture = _capture_bonus(planets_prev, planets_now, player)
    production = _production_delta(planets_prev, planets_now, player)
    ship = _ship_delta(planets_prev, fleets_prev, planets_now, fleets_now, player)

    per_turn = (
        W_CAPTURE * capture
        + W_PRODUCTION * production
        + W_SHIP * ship
    )
    per_turn = max(-1.0, min(1.0, per_turn))

    terminal = None
    if final_rewards is not None:
        terminal = _terminal_reward(final_rewards, player)
        return {
            "capture_bonus": capture,
            "production_delta": production,
            "ship_delta": ship,
            "terminal": terminal,
            "total": terminal,
        }

    return {
        "capture_bonus": capture,
        "production_delta": production,
        "ship_delta": ship,
        "terminal": None,
        "total": per_turn,
    }

