"""
OrbitWarsEnv — gymnasium wrapper over the kaggle orbit_wars trainer API.

Observation space: Box(560,) float32  (see rl/obs.py for layout)
Action space:      MultiDiscrete([40,40,4]*5)  — 5 fleet slots per turn
  action[i*3]   = source planet slot  (0–39)
  action[i*3+1] = target planet slot  (0–39)
  action[i*3+2] = ship fraction index (0=25%, 1=50%, 2=75%, 3=100% of surplus)

Reward: terminal-only (+1 win, -1 loss, 0 draw).
"""

import contextlib
import io
import logging

import numpy as np
import gymnasium as gym
from gymnasium import spaces

# kaggle_environments prints env-registration noise to stdout (failed cabt
# load) and logs INFO/WARNING messages (OpenSpiel, LiteLLM) at import time;
# silence both so training logs stay readable.
with contextlib.redirect_stdout(io.StringIO()):
    logging.disable(logging.WARNING)
    from kaggle_environments import make
logging.disable(logging.NOTSET)

from rl.obs import OBS_SIZE, encode_obs, decode_action
from rl.reward import compute_terminal_reward, compute_dense_reward, DENSE_SCALE


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
        self.action_space = spaces.MultiDiscrete([40, 40, 4] * 5)  # 5 fleet slots, each: src/tgt/frac
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

        # Dense reward: ship-count advantage at the state after actions
        dense = DENSE_SCALE * compute_dense_reward(obs, self._player_id)

        # Terminal reward on episode end
        terminal = 0.0
        if done:
            final_rewards = None
            if hasattr(info, 'rewards') and info.rewards:
                final_rewards = list(info.rewards)
            else:
                final_rewards = [0.0, 0.0]
                if kaggle_reward is not None and kaggle_reward != 0:
                    final_rewards[self._player_id] = float(kaggle_reward)
                    final_rewards[1 - self._player_id] = -float(kaggle_reward)
            terminal = compute_terminal_reward(final_rewards, self._player_id)

        reward = dense + terminal

        self._prev_obs = self._last_obs
        self._last_obs = obs

        vec, _ = encode_obs(obs, self._player_id)
        return vec, reward, done, False, {}

    def close(self):
        self._env = None
        self._trainer = None
