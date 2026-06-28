"""Minimax search with alpha-beta pruning, transposition table, and parallel root search."""

from __future__ import annotations

import dataclasses as dc
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from chess.ai.zobrist import ZOBRIST_PIECES, ZOBRIST_TURN, square_index
from chess.core.board import Board
from chess.core.piece import King, NullPiece, Position
from chess.core.types import Color, Ending, PieceType

Move = tuple[Position, Position]
MATE_SCORE = 100_000.0

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2


@dc.dataclass
class TTEntry:
    depth: int
    value: float
    flag: int


@dc.dataclass
class MinMaxAgent:
    """Chess agent using minimax with alpha-beta pruning."""

    color: Color = Color.BLACK
    depth: int = 3
    max_n_samples: int | None = None
    workers: int = 0
    _tt: dict[int, TTEntry] = dc.field(default_factory=dict, repr=False, compare=False)

    def _worker_count(self, move_count: int) -> int:
        if self.workers == 1 or move_count < 2:
            return 1
        cpus = os.cpu_count() or 1
        limit = cpus if self.workers <= 0 else self.workers
        return max(1, min(limit, move_count, 8))

    @staticmethod
    def is_terminal(board: Board) -> bool:
        return (
            board.checkmates[Color.WHITE] != Ending.ONGOING
            or board.checkmates[Color.BLACK] != Ending.ONGOING
        )

    @staticmethod
    def board_hash(board: Board) -> int:
        digest = ZOBRIST_TURN if board.turn == Color.BLACK else 0
        for piece in board.pieces[Color.WHITE] + board.pieces[Color.BLACK]:
            idx = square_index(piece.position.x, piece.position.y)
            digest ^= ZOBRIST_PIECES[idx][piece.color.value - 1][piece.piece_type.value - 1]
        return digest

    @staticmethod
    def generate_possible_moves(board: Board, *, update: bool = True) -> list[Move]:
        if update:
            board.update()
        moves: list[Move] = []
        side = board.turn

        for piece in board.pieces[side]:
            origin = Position(piece.position.x, piece.position.y)
            for target in piece.legal_moves:
                ok, _ = board.try_move(piece, target, move=False)
                if ok:
                    moves.append((origin, Position(target.x, target.y)))

        king = board.kings.get(side)
        if king is not None and king.moved == 0:
            origin = Position(king.position.x, king.position.y)
            for target_x in (6, 2):
                dest = Position(target_x, king.position.y)
                if board.can_castle_to(king, dest):
                    moves.append((origin, dest))
        return moves

    def evaluate(self, board: Board) -> float:
        white = board.checkmates[Color.WHITE]
        black = board.checkmates[Color.BLACK]

        if white == Ending.CHECKMATE:
            score = -MATE_SCORE
        elif black == Ending.CHECKMATE:
            score = MATE_SCORE
        elif white in (Ending.STALEMATE, Ending.DRAW) or black in (
            Ending.STALEMATE,
            Ending.DRAW,
        ):
            score = 0.0
        else:
            score = 0.0
            for piece in board.pieces[Color.WHITE]:
                score += piece.value + 0.05 * len(piece.legal_moves)
            for piece in board.pieces[Color.BLACK]:
                score -= piece.value + 0.05 * len(piece.legal_moves)
            if board.checks[Color.WHITE]:
                score -= 0.5
            if board.checks[Color.BLACK]:
                score += 0.5

        if self.color == Color.BLACK:
            score = -score
        return float(score)

    @staticmethod
    def apply_move(board: Board, move: Move, *, for_search: bool = False) -> bool:
        from_pos, to_pos = move
        board.promotion = PieceType.QUEEN
        piece = board.get(from_pos)
        if isinstance(piece, NullPiece) or piece.color != board.turn:
            return False
        if isinstance(piece, King) and abs(to_pos.x - from_pos.x) == 2:
            ok = board.handle_castling(piece, to_pos)
            if ok and not for_search:
                board.last_move = (from_pos, to_pos)
                opposite = Color.WHITE if piece.color == Color.BLACK else Color.BLACK
                board.turn = opposite
                board.checkmates[opposite] = board.check_end(opposite)
            elif ok:
                board.turn = Color.WHITE if piece.color == Color.BLACK else Color.BLACK
            return ok
        ok, _ = board.move_piece(piece, to_pos, update_result=not for_search)
        if ok and for_search:
            board.last_move = None
        return ok

    @staticmethod
    def _sync_terminal(board: Board) -> None:
        for color in (Color.WHITE, Color.BLACK):
            if board.checkmates[color] == Ending.ONGOING:
                board.checkmates[color] = board.check_end(color)

    @staticmethod
    def _move_coords(move: Move) -> tuple[int, int, int, int]:
        return (move[0].x, move[0].y, move[1].x, move[1].y)

    @staticmethod
    def _coords_to_move(coords: tuple[int, int, int, int]) -> Move:
        fx, fy, tx, ty = coords
        return (Position(fx, fy), Position(tx, ty))

    def choose_move(self, board: Board) -> Move | None:
        self._tt.clear()
        board.update()
        moves = self.generate_possible_moves(board, update=False)
        if not moves:
            return None
        if len(moves) == 1:
            return moves[0]

        workers = self._worker_count(len(moves))
        if workers > 1:
            return self._choose_parallel(board, moves, workers)
        move, _ = self.minimax(board, self.depth, float("-inf"), float("inf"))
        return move

    def _choose_parallel(self, board: Board, moves: list[Move], workers: int) -> Move | None:
        state = board.to_search_state()
        payload = (state, self.depth, self.color.value, self.max_n_samples)
        ordered = _order_moves(board, moves)
        best_move: Move | None = None
        best_value = float("-inf")

        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_score_root_move, payload, self._move_coords(move)): move
                for move in ordered
            }
            for future in as_completed(futures):
                move_coords, value = future.result()
                if value > best_value or best_move is None:
                    best_value = value
                    best_move = self._coords_to_move(move_coords)
        return best_move

    def minimax(
        self, board: Board, depth: int, alpha: float, beta: float
    ) -> tuple[Move | None, float]:
        board_hash = self.board_hash(board)
        cached = self._tt.get(board_hash)
        if cached is not None and cached.depth >= depth:
            if cached.flag == TT_EXACT:
                return None, cached.value
            if cached.flag == TT_LOWER:
                alpha = max(alpha, cached.value)
            elif cached.flag == TT_UPPER:
                beta = min(beta, cached.value)
            if alpha >= beta:
                return None, cached.value

        if depth == 0 or self.is_terminal(board):
            if depth == 0:
                self._sync_terminal(board)
            return None, self.evaluate(board)

        maximizing = board.turn == self.color
        possible_moves = _order_moves(
            board,
            self.generate_possible_moves(board, update=False),
        )

        if (
            self.max_n_samples
            and self.max_n_samples > 0
            and len(possible_moves) > self.max_n_samples
        ):
            import numpy as np

            idx = np.random.choice(len(possible_moves), self.max_n_samples, replace=False)
            possible_moves = [possible_moves[i] for i in idx]

        if not possible_moves:
            board.checkmates[board.turn] = board.check_end(board.turn)
            return None, self.evaluate(board)

        best_move: Move | None = None
        orig_alpha = alpha

        if maximizing:
            value = float("-inf")
            for move in possible_moves:
                trial = board.copy_for_search()
                if not self.apply_move(trial, move, for_search=True):
                    continue
                _, child = self.minimax(trial, depth - 1, alpha, beta)
                if child > value or best_move is None:
                    value = child
                    best_move = move
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            if value <= orig_alpha:
                flag = TT_UPPER
            elif value >= beta:
                flag = TT_LOWER
            else:
                flag = TT_EXACT
            self._tt[board_hash] = TTEntry(depth=depth, value=value, flag=flag)
            return best_move, value

        value = float("inf")
        for move in possible_moves:
            trial = board.copy_for_search()
            if not self.apply_move(trial, move, for_search=True):
                continue
            _, child = self.minimax(trial, depth - 1, alpha, beta)
            if child < value or best_move is None:
                value = child
                best_move = move
            beta = min(beta, value)
            if beta <= alpha:
                break
        if value >= beta:
            flag = TT_UPPER
        elif value <= orig_alpha:
            flag = TT_LOWER
        else:
            flag = TT_EXACT
        self._tt[board_hash] = TTEntry(depth=depth, value=value, flag=flag)
        return best_move, value


def _order_moves(board: Board, moves: list[Move]) -> list[Move]:
    def capture_value(move: Move) -> int:
        target = board.get(move[1])
        return 0 if isinstance(target, NullPiece) else target.value

    return sorted(moves, key=capture_value, reverse=True)


def _score_root_move(
    payload: tuple[Any, int, int, int | None],
    move_coords: tuple[int, int, int, int],
) -> tuple[tuple[int, int, int, int], float]:
    state, depth, color_value, max_n_samples = payload
    board = Board.from_search_state(state)
    move = MinMaxAgent._coords_to_move(move_coords)
    agent = MinMaxAgent(
        color=Color(color_value),
        depth=depth,
        max_n_samples=max_n_samples,
        workers=1,
    )
    trial = board.copy_for_search()
    if not MinMaxAgent.apply_move(trial, move, for_search=True):
        return move_coords, float("-inf")
    _, value = agent.minimax(trial, depth - 1, float("-inf"), float("inf"))
    return move_coords, value


def choose_move_in_subprocess(
    state: tuple[Any, ...],
    depth: int,
    color: Color,
    max_n_samples: int | None,
    workers: int,
) -> tuple[int, int, int, int] | None:
    board = Board.from_search_state(state)
    agent = MinMaxAgent(
        color=color,
        depth=depth,
        max_n_samples=max_n_samples,
        workers=workers,
    )
    move = agent.choose_move(board)
    if move is None:
        return None
    return MinMaxAgent._move_coords(move)
