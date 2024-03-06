from typing import Any, Dict, Tuple

import cv2
import gymnasium
import numpy as np
import pygame
from gymnasium import spaces
from pygame import surfarray

from board import Board, Ending
from piece import (Bishop, Color, King, Knight, Pawn, PieceType, Position,
                   Queen, Rook)

piece_to_index = {None: 0, Rook: 1, Knight: 2, Bishop: 3, Queen: 4, King: 5, Pawn: 6}

color_name_map = {Color.WHITE: "White", Color.BLACK: "Black"}

DEFAULT_REWARD_CONFIG = {
    "move": 0.002,
    "capture": 0.005,
    "checkmate": 3,
    "draw": -3,
}


def pg_to_cv2(cvarray: np.ndarray) -> np.ndarray:
    cvarray = cvarray.swapaxes(0, 1)  # rotate
    cvarray = cv2.cvtColor(cvarray, cv2.COLOR_RGB2BGR)  # RGB to BGR
    return cvarray


class BaseChessEnv(gymnasium.Env):
    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        dim_x: int = 8,
        dim_y: int = 8,
        render_mode: str = "rgb_array",
        square_size: int = 64,
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

        self.board = Board(dim_x, dim_y)
        self.square_size = 64  # Assuming square size of 64 pixels
        self.render_mode = render_mode
        self.n_squares = dim_x * dim_y
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(dim_x * dim_y * 14,), dtype=np.uint8
        )
        self.turn = Color.WHITE
        self.populate_board()

    def _get_observation(self):
        observation = np.zeros((self.board.dim_x, self.board.dim_y, 14), dtype=np.uint8)

        for piece in self.board.pieces:
            value = piece_to_index[type(piece)] + (
                7 if piece.color == Color.WHITE else 0
            )
            observation[piece.position.y][piece.position.x][value] = 1
        return observation.reshape(-1)

    def populate_board(self):
        STARTINGCONFIGURATION = [
            Rook(color=Color.BLACK, position=Position(0, 0)),
            Knight(color=Color.BLACK, position=Position(1, 0)),
            Bishop(color=Color.BLACK, position=Position(2, 0)),
            Queen(color=Color.BLACK, position=Position(3, 0)),
            King(color=Color.BLACK, position=Position(4, 0)),
            Bishop(color=Color.BLACK, position=Position(5, 0)),
            Knight(color=Color.BLACK, position=Position(6, 0)),
            Rook(color=Color.BLACK, position=Position(7, 0)),
            Pawn(color=Color.BLACK, position=Position(0, 1)),
            Pawn(color=Color.BLACK, position=Position(1, 1)),
            Pawn(color=Color.BLACK, position=Position(2, 1)),
            Pawn(color=Color.BLACK, position=Position(3, 1)),
            Pawn(color=Color.BLACK, position=Position(4, 1)),
            Pawn(color=Color.BLACK, position=Position(5, 1)),
            Pawn(color=Color.BLACK, position=Position(6, 1)),
            Pawn(color=Color.BLACK, position=Position(7, 1)),
            Rook(color=Color.WHITE, position=Position(0, 7)),
            Knight(color=Color.WHITE, position=Position(1, 7)),
            Bishop(color=Color.WHITE, position=Position(2, 7)),
            Queen(color=Color.WHITE, position=Position(3, 7)),
            King(color=Color.WHITE, position=Position(4, 7)),
            Bishop(color=Color.WHITE, position=Position(5, 7)),
            Knight(color=Color.WHITE, position=Position(6, 7)),
            Rook(color=Color.WHITE, position=Position(7, 7)),
            Pawn(color=Color.WHITE, position=Position(0, 6)),
            Pawn(color=Color.WHITE, position=Position(1, 6)),
            Pawn(color=Color.WHITE, position=Position(2, 6)),
            Pawn(color=Color.WHITE, position=Position(3, 6)),
            Pawn(color=Color.WHITE, position=Position(4, 6)),
            Pawn(color=Color.WHITE, position=Position(5, 6)),
            Pawn(color=Color.WHITE, position=Position(6, 6)),
            Pawn(color=Color.WHITE, position=Position(7, 6)),
        ]

        for piece in STARTINGCONFIGURATION:
            self.board.add_piece(piece)
        self.board.update()

    def _step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, dict]:
        reward = 0
        castling_dir = np.argmax(action[:3])
        king = [
            p
            for p in self.board.pieces
            if p.color == self.board.turn and type(p) == King
        ][0]

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
            # # Iterate over each piece and its corresponding action probabilities
            pieces = self.board.pieces
            pieces = [p for p in pieces if p.color == self.board.turn]
            sorted_idx = np.argsort(action.sum(axis=1))[::-1]
            moved = False
            for idx in sorted_idx:
                if idx >= len(pieces):
                    continue
                piece = pieces[idx]
                a = action[idx]
                if piece is None or piece.color != self.board.turn:
                    continue

                # Choose the move with the highest probability
                moves = np.argsort(a)[::-1]
                for move in moves:
                    if move < len(piece.legal_moves):
                        return_value, capture_value = self.board.move_piece(
                            piece, piece.legal_moves[move]
                        )
                        if return_value:
                            reward += capture_value * self.reward_cfg["capture"]
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

    def _reset(
        self, *, seed=None, options=None
    ) -> Tuple[Dict[Any, Any], Dict[Any, Any]]:
        # Reset the board to the initial state
        self.board = Board(self.board.dim_x, self.board.dim_y)
        self.populate_board()

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

    def board_from_observation(self, observation: np.ndarray) -> Board:
        board = Board(self.board.dim_x, self.board.dim_y)
        observation = observation.reshape(self.board.dim_x, self.board.dim_y, 14)
        for i in range(self.board.dim_x):
            for j in range(self.board.dim_y):
                for k in range(14):
                    if observation[i, j, k] == 1:
                        color = Color.WHITE if k > 6 else Color.BLACK
                        piece = None
                        if k != 0:
                            piece = list(piece_to_index.keys())[
                                list(piece_to_index.values()).index(k % 7)
                            ]
                        board.add_piece(piece(color=color, position=Position(j, i)))
        board.update()
        return board

    def render_from_observation(self, observation: np.ndarray, mode=None):
        board = self.board_from_observation(observation)
        if mode is None:
            mode = self.render_mode
        board.draw(self.screen, self.square_size)
        pygame.display.flip()
        if mode == "rgb_array":
            try:
                pg_frame = surfarray.pixels3d(
                    self.screen
                )  # convert the surface to a np array. Only works with depth 24 or 32, not less
            except:
                pg_frame = surfarray.array3d(self.screen)
            cv_frame = pg_to_cv2(pg_frame)
            return cv_frame

    def close(self):
        pygame.quit()
