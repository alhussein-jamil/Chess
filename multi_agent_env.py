from typing import Any, Dict, Tuple

import numpy as np
from gymnasium import spaces
from ray.rllib.env.multi_agent_env import MultiAgentEnv

from base import DEFAULT_REWARD_CONFIG, BaseChessEnv
from piece import Color


class ChessEnvMulti(BaseChessEnv, MultiAgentEnv):

    def __init__(
        self,
        dim_x: int = 8,
        dim_y: int = 8,
        render_mode: str = "rgb_array",
        square_size: int = 64,
        reward_cfg: Dict[str, float] = DEFAULT_REWARD_CONFIG,
        init_display=True,
    ):
        BaseChessEnv.__init__(
            self, dim_x, dim_y, render_mode, square_size, reward_cfg, init_display
        )
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
        return obs, {self._agent_ids[0]: {}, self._agent_ids[1]: {}}

    def step(
        self, action_dict: Dict[Any, Any]
    ) -> Tuple[Dict[Any, Any], Dict[Any, Any], Dict[Any, Any], Dict[Any, Any]]:

        action_white = action_dict[self._agent_ids[0]]
        action_black = action_dict[self._agent_ids[1]]
        obs, reward, done, truncated, info = self._step(
            action_white if self.turn == Color.WHITE else action_black
        )
        other_color = Color.WHITE if self.turn == Color.BLACK else Color.BLACK

        obs = {self._agent_ids[0]: obs, self._agent_ids[1]: obs}
        rewards = {
            self._agent_ids[0]: reward if self.turn == Color.WHITE else -reward,
            self._agent_ids[1]: reward if self.turn == Color.BLACK else -reward,
        }
        dones = {self._agent_ids[0]: done, self._agent_ids[1]: done, "__all__": done}
        infos = {self._agent_ids[0]: info, self._agent_ids[1]: info}
        truncateds = {
            self._agent_ids[0]: truncated,
            self._agent_ids[1]: truncated,
            "__all__": truncated,
        }
        self.turn = other_color
        return obs, rewards, dones, truncateds, infos
