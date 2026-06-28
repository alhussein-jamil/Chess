"""Minimax search with alpha-beta pruning, transposition table, and parallel root search."""

from __future__ import annotations

import dataclasses as dc
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from chess.core.board import Board
from chess.core.board_state import MATE_SCORE, PIECE_VALUES, BoardState, Move4
from chess.core.piece import King, NullPiece, Position
from chess.core.types import Color, Ending, PieceType

Move = tuple[Position, Position]

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
        return max(1, min(limit, move_count))

    @staticmethod
    def resolve_pool_workers(workers: int) -> int:
        """Process pool size for parallel root-move search."""
        if workers == 1:
            return 1
        cpus = os.cpu_count() or 1
        return cpus if workers <= 0 else workers

    @staticmethod
    def generate_possible_moves(board: Board, *, update: bool = True) -> list[Move]:
        if update:
            board.update()
        return [MinMaxAgent._coords_to_move(m) for m in board.state.generate_legal_moves()]

    def evaluate_state(self, state: BoardState) -> float:
        agent_color = 0 if self.color == Color.WHITE else 1
        if state.halfmove >= 80 or state.insufficient_material():
            return 0.0

        if not state.has_legal_move():
            side = state.turn
            score = (MATE_SCORE if side == 1 else -MATE_SCORE) if state.in_check(side) else 0.0
            if agent_color == 1:
                score = -score
            return float(score)

        return state.evaluate(agent_color, mobility=True)

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
            return self.evaluate_state(board.state)

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
    def _move_coords(move: Move) -> tuple[int, int, int, int]:
        return (move[0].x, move[0].y, move[1].x, move[1].y)

    @staticmethod
    def _coords_to_move(coords: Move4) -> Move:
        fx, fy, tx, ty = coords
        return (Position(fx, fy), Position(tx, ty))

    def choose_move(self, board: Board) -> Move | None:
        self._tt.clear()
        state = board.state
        moves = state.generate_legal_moves()
        if not moves:
            return None
        if len(moves) == 1:
            return self._coords_to_move(moves[0])

        workers = self._worker_count(len(moves))
        if workers > 1:
            move = self._choose_parallel_from_state(
                board.to_search_state(), moves, workers, executor=_get_search_pool(workers)
            )
            return self._coords_to_move(move) if move is not None else None
        move, _ = self._minimax(state, self.depth, float("-inf"), float("inf"))
        return self._coords_to_move(move) if move is not None else None

    def _choose_parallel_from_state(
        self,
        state_tuple: tuple[Any, ...],
        moves: list[Move4],
        workers: int,
        *,
        executor: ProcessPoolExecutor | None = None,
    ) -> Move4 | None:
        state = BoardState.from_search_state(state_tuple)
        ordered = _order_moves(state, moves)
        best_move: Move4 | None = None
        best_value = float("-inf")
        payload = (state_tuple, self.depth, self.color.value, self.max_n_samples)

        def collect(pool: ProcessPoolExecutor) -> Move4 | None:
            nonlocal best_move, best_value
            futures = {pool.submit(_score_root_move, payload, move): move for move in ordered}
            for future in as_completed(futures):
                move_coords, value = future.result()
                if value > best_value or best_move is None:
                    best_value = value
                    best_move = move_coords
            return best_move

        if executor is not None:
            return collect(executor)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return collect(pool)

    def _minimax(
        self, state: BoardState, depth: int, alpha: float, beta: float
    ) -> tuple[Move4 | None, float]:
        board_hash = state.hash_key()
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

        if depth == 0:
            return None, self.evaluate_state(state)

        possible_moves = _order_moves(state, state.generate_legal_moves())

        if (
            self.max_n_samples
            and self.max_n_samples > 0
            and len(possible_moves) > self.max_n_samples
        ):
            import numpy as np

            idx = np.random.choice(len(possible_moves), self.max_n_samples, replace=False)
            possible_moves = [possible_moves[i] for i in idx]

        if not possible_moves:
            return None, self.evaluate_state(state)

        maximizing = state.turn == (0 if self.color == Color.WHITE else 1)

        best_move: Move4 | None = None
        orig_alpha = alpha

        if maximizing:
            value = float("-inf")
            for move in possible_moves:
                state.make_move(*move)
                _, child = self._minimax(state, depth - 1, alpha, beta)
                state.unmake_move()
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
            state.make_move(*move)
            _, child = self._minimax(state, depth - 1, alpha, beta)
            state.unmake_move()
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


def _order_moves(state: BoardState, moves: list[Move4]) -> list[Move4]:
    def capture_value(move: Move4) -> int:
        tx, ty = move[2], move[3]
        captured = int(state.grid[ty, tx])
        if captured == 0:
            return 0
        return PIECE_VALUES.get(abs(captured), 0)

    return sorted(moves, key=capture_value, reverse=True)


_search_pool: ProcessPoolExecutor | None = None
_search_pool_workers = 0


def _get_search_pool(workers: int) -> ProcessPoolExecutor:
    global _search_pool, _search_pool_workers
    if _search_pool is None or _search_pool_workers != workers:
        if _search_pool is not None:
            _search_pool.shutdown(wait=False, cancel_futures=True)
        _search_pool = ProcessPoolExecutor(max_workers=workers)
        _search_pool_workers = workers
    return _search_pool


def shutdown_search_pool() -> None:
    global _search_pool, _search_pool_workers
    if _search_pool is not None:
        _search_pool.shutdown(wait=False, cancel_futures=True)
        _search_pool = None
        _search_pool_workers = 0


def _choose_move_serial(
    payload: tuple[Any, int, int, int | None],
) -> Move4 | None:
    state_tuple, depth, color_value, max_n_samples = payload
    agent = MinMaxAgent(
        color=Color(color_value),
        depth=depth,
        max_n_samples=max_n_samples,
        workers=1,
    )
    state = BoardState.from_search_state(state_tuple)
    move, _ = agent._minimax(state, depth, float("-inf"), float("inf"))
    return move


def _score_root_move(
    payload: tuple[Any, int, int, int | None],
    move_coords: Move4,
) -> tuple[Move4, float]:
    state_tuple, depth, color_value, max_n_samples = payload
    state = BoardState.from_search_state(state_tuple)
    agent = MinMaxAgent(
        color=Color(color_value),
        depth=depth,
        max_n_samples=max_n_samples,
        workers=1,
    )
    if not state.make_move(*move_coords):
        return move_coords, float("-inf")
    _, value = agent._minimax(state, depth - 1, float("-inf"), float("inf"))
    return move_coords, value


def choose_move_in_subprocess(
    state: tuple[Any, ...],
    depth: int,
    color: Color,
    max_n_samples: int | None,
    workers: int,
) -> tuple[int, int, int, int] | None:
    agent = MinMaxAgent(
        color=color,
        depth=depth,
        max_n_samples=max_n_samples,
        workers=workers,
    )
    search_state = BoardState.from_search_state(state)
    moves = search_state.generate_legal_moves()
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]
    payload = (state, depth, color.value, max_n_samples)
    parallel_workers = agent._worker_count(len(moves))
    if parallel_workers > 1:
        move = agent._choose_parallel_from_state(
            state, moves, parallel_workers, executor=_get_search_pool(parallel_workers)
        )
    else:
        move = _choose_move_serial(payload)
    if move is None:
        return None
    return move
