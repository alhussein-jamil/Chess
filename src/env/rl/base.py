from typing import Dict, Tuple

import cv2
import gymnasium
import numpy as np
import pygame
from gymnasium import spaces
from pygame import surfarray
from copy import deepcopy


from ..base.board import Board, Ending
from ..base.piece import (
    Bishop,
    Color,
    King,
    Knight,
    Pawn,
    PieceType,
    Position,
    NullPiece,
    Piece,
    Queen,
    Rook,
    STARTING_PIECES,
)
from ...globals import DIM_X as dim_x, DIM_Y as dim_y, SQUARE_SIZE as square_size

piece_to_index: Dict[type[Piece], int] = {
    NullPiece: 0,
    Pawn: 1,
    Rook: 2,
    Knight: 3,
    Bishop: 4,
    Queen: 5,
    King: 6,
}
index_to_piece = {v: k for k, v in piece_to_index.items()}
color_name_map = {Color.WHITE: "White", Color.BLACK: "Black"}

DEFAULT_REWARD_CONFIG = {
    "move": 0.005,
    "capture": 0.05,
    "checkmate": 30,
    "draw": -15,
}


def pg_to_cv2(cvarray: np.ndarray) -> np.ndarray:
    cvarray = cvarray.swapaxes(0, 1)  # rotate
    cvarray = cv2.cvtColor(cvarray, cv2.COLOR_RGB2BGR)  # RGB to BGR
    return cvarray


class BaseChessEnv(gymnasium.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        render_mode: str = "rgb_array",
        reward_cfg: Dict[str, float] = DEFAULT_REWARD_CONFIG,
        init_display=True,
    ):
        self.reward_cfg = reward_cfg

        super(BaseChessEnv, self).__init__()

        if init_display:
            pygame.init()
            pygame.display.set_caption("Chess Game")
            self.screen = pygame.display.set_mode(
                (dim_x * square_size + 50, dim_y * square_size + 50)
            )

        self.board = Board()
        self.square_size = 64  # Assuming square size of 64 pixels
        self.render_mode = render_mode
        self.n_squares = dim_x * dim_y
        self.observation_space = spaces.Box(
            low=0, high=32, shape=(dim_x * dim_y * 3,), dtype=np.uint8
        )

        self.turn = Color.WHITE
        self.populate_board()

    def _get_observation(self) -> np.ndarray:
        observation = np.zeros((dim_x, dim_y, 3), dtype=np.uint8)

        for piece in self.board.pieces[Color.WHITE] + self.board.pieces[Color.BLACK]:
            value = piece_to_index[type(piece)]
            observation[piece.position.y][piece.position.x][
                0 if piece.color == Color.WHITE else 1
            ] = value
        for position, danger in self.board.danger_level.items():
            assert abs(danger) <= 16
            observation[position.y][position.x][2] = danger + 16

        return observation.reshape(-1)

    def populate_board(self):
        for piece in STARTING_PIECES:
            self.board.add_piece(self.board, deepcopy(piece))
        self.board.update()

    def _step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        reward = 0
        castling_dir = np.argmax(action[:3])
        king = [p for p in self.board.pieces[self.board.turn] if type(p) == King][0]

        castled = False
        if castling_dir == 1:  # king side castle
            if self.board.turn == Color.WHITE:
                castled = self.board.handle_castling(king, new_position=Position(6, 7))
            else:
                castled = self.board.handle_castling(king, new_position=Position(6, 0))
        elif castling_dir == 2:  # queen side castle
            if self.board.turn == Color.WHITE:
                castled = self.board.handle_castling(king, new_position=Position(2, 7))
            else:
                castled = self.board.handle_castling(king, new_position=Position(2, 0))

        self.board.promotion = PieceType(2 + np.argmax(action[3:7]))

        action = action[7:].reshape(-1, 64)
        if not castled:
            # Iterate over each piece and its corresponding action probabilities
            pieces: list[Piece] = self.board.pieces[self.board.turn]
            sorted_idx = np.argsort(action.sum(axis=1))[::-1]
            moved = False
            for idx in sorted_idx:
                if idx >= len(pieces):
                    continue
                piece = pieces[idx]
                a = action[idx]
                if isinstance(Piece, NullPiece) or piece.color != self.board.turn:
                    continue

                # Choose the move with the highest probability
                moves = np.argsort(a)[::-1]
                for move in moves:
                    if move < len(piece.legal_moves):
                        occupying_piece = self.board.board[piece.legal_moves[move]]
                        return_value, capture_value = self.board.move_piece(
                            piece, piece.legal_moves[move]
                        )
                        if return_value:
                            capture_reward = capture_value * self.reward_cfg["capture"]
                            if not isinstance(occupying_piece, NullPiece):
                                capture_reward *= (
                                    len(occupying_piece.legal_moves)
                                    / occupying_piece.max_n_legal_moves
                                )

                            reward += capture_reward
                            reward -= self.reward_cfg["move"]
                            moved = True
                            break

                if moved:
                    break

        done = (
            self.board.checkmates[Color.WHITE] != Ending.ONGOING
            or self.board.checkmates[Color.BLACK] != Ending.ONGOING
        )

        if done and not self.board.checkmates[self.board.turn]:
            reward += self.reward_cfg["draw"]
        elif done:
            reward += self.reward_cfg["checkmate"]

        # Return the new observation, reward, done flag, and additional info (empty for now)
        return self._get_observation(), reward, done, False, {}

    def _reset(self, *, seed=None, options=None) -> None:
        # Reset the board to the initial state
        self.board = Board()
        self.populate_board()

    def render(self, mode=None):
        if mode is None:
            mode = self.render_mode
        self.board.draw(self.screen)
        pygame.display.flip()
        if mode == "rgb_array":
            try:
                pg_frame = surfarray.pixels3d(
                    self.screen
                )  # convert the surface to a np array. Only works with depth 24 or 32, not less
            except Exception:
                pg_frame = surfarray.array3d(
                    self.screen
                )  # convert the surface to a np array. Works with any depth

            cv_frame = pg_to_cv2(
                pg_frame
            )  # then convert the np array so it is compatible with opencv

            return cv_frame

    def board_from_observation(self, observation: np.ndarray) -> Board:
        board = Board()
        observation = observation.reshape(dim_x, dim_y, 3).astype(np.uint8)
        observation = observation[:, :, :2]
        observation = (
            (observation - observation.min())
            / (observation.max() - observation.min())
            * 6
        )

        for i in range(dim_x):
            for j in range(dim_y):
                for r, color in enumerate([Color.WHITE, Color.BLACK]):
                    k = observation[i][j][r]
                    piece = None
                    if k != 0:
                        piece = index_to_piece[k](color=color, position=Position(j, i))
                        board.add_piece(board, piece)
        board.update()
        return board

    def render_from_observation(self, observation: np.ndarray, mode=None):
        board = self.board_from_observation(observation)
        if mode is None:
            mode = self.render_mode
        board.draw(self.screen)
        pygame.display.flip()
        if mode == "rgb_array":
            try:
                pg_frame = surfarray.pixels3d(
                    self.screen
                )  # convert the surface to a np array. Only works with depth 24 or 32, not less
            except Exception:
                pg_frame = surfarray.array3d(self.screen)
            cv_frame = pg_to_cv2(pg_frame)
            return cv_frame

    def close(self):
        pygame.quit()
