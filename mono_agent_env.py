from typing import Any, Dict, Tuple

import cv2
import numpy as np
import pygame
from gymnasium import spaces
from pygame import surfarray

from base import BaseChessEnv
from piece import Bishop, Color, King, Knight, Pawn, Queen, Rook

piece_to_index = {None: 0, Rook: 1, Knight: 2, Bishop: 3, Queen: 4, King: 5, Pawn: 6}

color_name_map = {Color.WHITE: "White", Color.BLACK: "Black"}

DEFAULT_REWARD_CONFIG = {
    "move": 0.002,
    "capture": 0.01,
    "checkmate": 3,
    "draw": -3,
}


def pg_to_cv2(cvarray: np.ndarray) -> np.ndarray:
    cvarray = cvarray.swapaxes(0, 1)  # rotate
    cvarray = cv2.cvtColor(cvarray, cv2.COLOR_RGB2BGR)  # RGB to BGR
    return cvarray


class ChessEnvMono(BaseChessEnv):
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
            self,
            dim_x=dim_x,
            dim_y=dim_y,
            render_mode=render_mode,
            square_size=square_size,
            reward_cfg=reward_cfg,
            init_display=init_display,
        )

        self.action_space = spaces.Box(
            low=0,
            high=1,
            shape=((3 + 4 + 16 * self.n_squares) * 2,),
            dtype=np.float32,
        )

    def step(
        self, action_tuple
    ) -> Tuple[Dict[Any, Any], Dict[Any, Any], Dict[Any, Any], Dict[Any, Any]]:

        action_tuple = action_tuple.reshape(2, -1)
        action_white = action_tuple[0]
        action_black = action_tuple[1]

        if self.turn == Color.WHITE:
            obs, reward, done, truncated, info = self._step(action_white)
        else:
            obs, reward, done, truncated, info = self._step(action_black)

        self.turn = Color.WHITE if self.turn == Color.BLACK else Color.BLACK

        return obs, reward, done, truncated, info

    def reset(
        self, *, seed=None, options=None
    ) -> Tuple[Dict[Any, Any], Dict[Any, Any]]:
        self._reset(seed=seed, options=options)
        return self._get_observation(), {}

    def render(self, mode=None):
        if mode is None:
            mode = self.render_mode
        self.board.draw(self.screen, self.square_size)
        pygame.display.flip()
        if mode == "rgb_array":
            try:
                pg_frame = surfarray.pixels3d(
                    self.screen
                )  # convert the surface to a np array. Only works with depth 24 or 32, not less
            except:
                pg_frame = surfarray.array3d(
                    self.screen
                )  # convert the surface to a np array. Works with any depth

            cv_frame = pg_to_cv2(
                pg_frame
            )  # then convert the np array so it is compatible with opencv

            return cv_frame

    def close(self):
        pygame.quit()
