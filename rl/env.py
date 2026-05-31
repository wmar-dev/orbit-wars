"""
T005: OrbitWarsEnv — gymnasium wrapper over the kaggle orbit_wars trainer API.

Observation space: Box(319,) float32  (see rl/obs.py for layout)
Action space:      MultiDiscrete([12, 12, 5])
  action[0] = source planet slot  (0–11)
  action[1] = target planet slot  (0–11)
  action[2] = ship fraction index (0=no-op, 1=25%, 2=50%, 3=75%, 4=100% of surplus)

Reward: per-turn blended signal from inlined reward_signal.py constants.
Terminal reward replaces per-turn reward on the final step.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from kaggle_environments import make

from rl.obs import OBS_SIZE, encode_obs, decode_action

# ---------------------------------------------------------------------------
# Inlined reward constants (from reward_signal.py — Principle VI compliance)
# ---------------------------------------------------------------------------
_W_CAPTURE    = 0.5
_W_PRODUCTION = 0.3
_W_SHIP       = 0.2
_CAPTURE_SCALE  = 10.0
_PROD_SCALE     = 5.0
_SHIP_SCALE     = 20.0


def _owned_ships(planets, fleets, player):
    return (
        sum(p[5] for p in planets if p[1] == player)
        + sum(f[6] for f in fleets if f[1] == player)
    )


def _owned_production(planets, player):
    return sum(p[6] for p in planets if p[1] == player)


def _compute_reward(prev_obs, curr_obs, player, final_rewards=None):
    if prev_obs is None:
        return 0.0

    pp, pf = prev_obs.planets, prev_obs.fleets
    cp, cf = curr_obs.planets, curr_obs.fleets

    # Capture bonus
    prev_map = {p[0]: p for p in pp}
    capture = sum(
        p[6] for p in cp
        if p[1] == player and p[0] in prev_map and prev_map[p[0]][1] != player
    )
    capture_r = max(-1.0, min(1.0, capture / _CAPTURE_SCALE))

    # Production delta
    prod_delta = _owned_production(cp, player) - _owned_production(pp, player)
    prod_r = max(-1.0, min(1.0, prod_delta / _PROD_SCALE))

    # Ship delta
    ship_delta = _owned_ships(cp, cf, player) - _owned_ships(pp, pf, player)
    ship_r = max(-1.0, min(1.0, ship_delta / _SHIP_SCALE))

    if final_rewards is not None:
        n = len(final_rewards)
        my_r = final_rewards[player]
        if n == 2:
            other = final_rewards[1 - player]
            if my_r > other:
                return 1.0
            if my_r < other:
                return -1.0
            return 0.0
        sorted_r = sorted(final_rewards, reverse=True)
        positions = [i + 1 for i, r in enumerate(sorted_r) if r == my_r]
        rank = sum(positions) / len(positions)
        return 1.0 - 2.0 * (rank - 1.0) / (n - 1.0)

    per_turn = (
        _W_CAPTURE * capture_r
        + _W_PRODUCTION * prod_r
        + _W_SHIP * ship_r
    )
    return max(-1.0, min(1.0, per_turn))


class OrbitWarsEnv(gym.Env):
    """
    Gymnasium wrapper for the kaggle orbit_wars environment.

    Usage:
        env = OrbitWarsEnv(opponent="random")
        obs, info = env.reset()
        obs, reward, terminated, truncated, info = env.step(action)
    """

    metadata = {"render_modes": []}

    def __init__(self, opponent="random", seed=None):
        super().__init__()
        self.opponent = opponent
        self._seed = seed
        self.observation_space = spaces.Box(
            low=-2.0, high=2.0, shape=(OBS_SIZE,), dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([12, 12, 4])  # 4 fractions: 25/50/75/100%
        self._env = None
        self._trainer = None
        self._prev_obs = None
        self._player_id = None

    def reset(self, seed=None, options=None):
        cfg = {"seed": seed} if seed is not None else {}
        self._env = make("orbit_wars", configuration=cfg, debug=False)
        self._trainer = self._env.train([None, self.opponent])
        obs = self._trainer.reset()
        self._player_id = obs.player
        self._prev_obs = None
        vec, _ = encode_obs(obs, self._player_id)
        self._last_obs = obs
        return vec, {}

    def step(self, action: np.ndarray):
        action = np.asarray(action)
        fleet_cmds = decode_action(action, self._last_obs, self._player_id)
        obs, kaggle_reward, done, info = self._trainer.step(fleet_cmds)

        final_rewards = None
        if done:
            # kaggle returns the final reward as a scalar for our player
            # Reconstruct the 2-player final_rewards from info if available
            if hasattr(info, 'rewards'):
                final_rewards = list(info.rewards)
            else:
                # Fallback: use kaggle_reward sign to infer win/loss
                final_rewards = [0.0, 0.0]
                if kaggle_reward is not None and kaggle_reward != 0:
                    final_rewards[self._player_id] = float(kaggle_reward)
                    final_rewards[1 - self._player_id] = -float(kaggle_reward)

        reward = _compute_reward(
            self._prev_obs, obs, self._player_id,
            final_rewards=final_rewards if done else None
        )

        self._prev_obs = self._last_obs
        self._last_obs = obs

        vec, _ = encode_obs(obs, self._player_id)
        return vec, reward, done, False, {}

    def close(self):
        self._env = None
        self._trainer = None
