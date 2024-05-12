from typing import Any, Dict, Tuple

import numpy as np
from gymnasium import spaces
from ray.rllib.env.multi_agent_env import MultiAgentEnv

from src.env.rl.base import DEFAULT_REWARD_CONFIG, BaseChessEnv
from ..base.piece import Color
from ray.tune.registry import register_env


class ChessEnvMulti(BaseChessEnv, MultiAgentEnv):
    def __init__(
        self,
        render_mode: str = "rgb_array",
        reward_cfg: Dict[str, float] = DEFAULT_REWARD_CONFIG,
        init_display=True,
        **kwargs,
    ):
        BaseChessEnv.__init__(self, render_mode, reward_cfg, init_display)
        MultiAgentEnv.__init__(self)
        n_pieces = 16
        self.action_space = spaces.Box(
            low=0, high=1, shape=(3 + 4 + n_pieces * 64,), dtype=np.float32
        )
        self._agent_ids = ["White", "Black"]

    def reset(
        self, *, seed=None, options=None
    ) -> Tuple[Dict[Any, Any], Dict[Any, Any]]:
        # Reset the board to the initial state
        self._reset(seed=seed, options=options)
        obs = {
            self._agent_ids[0]: self._get_observation(),
            self._agent_ids[1]: self._get_observation(),
        }
        self.rewards = {
            "Black": 0.0,
            "White": 0.0,
        }
        return obs, {self._agent_ids[0]: {}, self._agent_ids[1]: {}}

    def step(
        self, action_dict: Dict[Any, Any]
    ) -> Tuple[
        Dict[str, np.ndarray],
        Dict[str, float],
        Dict[str, bool],
        Dict[str, bool],
        Dict[str, Any],
    ]:
        action_white = action_dict[self._agent_ids[0]]
        action_black = action_dict[self._agent_ids[1]]
        obs, reward, done, truncated, info = self._step(
            action_white if self.turn == Color.WHITE else action_black
        )

        self.rewards["White" if self.turn == Color.BLACK else "Black"] += reward
        self.rewards["Black" if self.turn == Color.BLACK else "White"] -= reward / 2
        other_color = Color.WHITE if self.turn == Color.BLACK else Color.BLACK

        obs = {self._agent_ids[0]: obs, self._agent_ids[1]: obs}
        rewards = self.rewards
        dones = {self._agent_ids[0]: done, self._agent_ids[1]: done, "__all__": done}
        infos = {self._agent_ids[0]: info, self._agent_ids[1]: info}
        truncateds = {
            self._agent_ids[0]: truncated,
            self._agent_ids[1]: truncated,
            "__all__": truncated,
        }
        self.turn = other_color
        return obs, rewards, dones, truncateds, infos


register_env("ChessMultiAgent-v0", lambda config: ChessEnvMulti(**config))
