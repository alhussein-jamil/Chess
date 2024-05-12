from src.env.base.board import Board
from typing import Optional, Any
import numpy as np
import dataclasses as dc


@dc.dataclass
class MinMaxAgent:
    """Class to represent a MinMax agent.

    Args:
        max_n_samples (int): The maximum number of samples to consider.
    """

    max_n_samples: Optional[int] = None

    @staticmethod
    def generate_possible_moves(board: Board) -> Any:
        """Method to generate all possible moves for the agent.

        Args:
            board (Board): The board to generate moves for.

        Returns:
            Any: The possible moves.
        """
        ...

    @staticmethod
    def evaluate(board: Board):  # Reward function
        """Method to evaluate the board state.

        Args:
            board (Board): The board to evaluate.

        Returns:
            float: The evaluation of the board state.
        """
        ...

    @staticmethod
    def make_move(board: Board, move: Any):
        """Method to make a move on the board.

        Args:
            board (Board): The board to make the move on.
            move Any: The move to make.
        """
        ...

    def minimax(
        self, board: Board, depth: int, alpha: float, beta: float
    ) -> tuple[Any, float]:
        """Method to perform the minimax algorithm.

        Args:
            board (Board): The board to perform the minimax on.
            depth (int): The depth to perform the minimax to.
            alpha (float): The alpha value.
            beta (float): The beta value.

        Returns:
            tuple[int | None, float]: The best move and its value.
        """

        board.update_draggable_pieces()
        if depth == 0 or board.game_over:
            return None, self.evaluate(board)

        maximizing_player = board.turn == "orange"

        possible_moves = self.generate_possible_moves(board)
        if self.max_n_samples and self.max_n_samples > 0:
            n_samples = min(
                len(possible_moves),
                self.max_n_samples,
            )
            samples_idx = np.random.choice(
                len(possible_moves), n_samples, replace=False
            )
            possible_moves = [possible_moves[i] for i in samples_idx]
        if len(possible_moves) == 0:
            return None, float("-inf") if maximizing_player else float("inf")

        if maximizing_player:
            max_value = float("-inf")
            best_move = None
            for move in possible_moves:
                board_copy = board.ai_copy()
                self.make_move(board_copy, move)
                _, value = self.minimax(board_copy, depth - 1, alpha, beta)
                if value > max_value or best_move is None:
                    max_value = value
                    best_move = move
                alpha = max(alpha, max_value)
                if beta <= alpha:
                    break
            return best_move, max_value
        else:
            min_value = float("inf")
            best_move = None

            for move in possible_moves:
                board_copy = board.ai_copy()
                self.make_move(board_copy, move)
                _, value = self.minimax(board_copy, depth - 1, alpha, beta)
                if value < min_value or best_move is None:
                    min_value = value
                    best_move = move
                beta = min(beta, min_value)
                if beta <= alpha:
                    break
            return best_move, min_value
