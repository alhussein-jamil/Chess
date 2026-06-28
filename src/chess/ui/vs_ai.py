"""Human vs minimax AI (you play White)."""

from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from copy import deepcopy

import pygame

from chess.ai.minmax import (
    MinMaxAgent,
    Move,
    _choose_move_serial,
    _order_moves,
    _score_root_move,
    shutdown_search_pool,
)
from chess.config import AppSettings
from chess.core.board import Board
from chess.core.board_state import BoardState, Move4
from chess.core.piece import STARTING_PIECES
from chess.core.types import Color, Ending
from chess.layout import vs_ai_window_size
from chess.log import get_logger
from chess.ui.scene import blit_scene, render_vs_ai_scene

logger = get_logger(__name__)


class _BackgroundAi:
    """Runs minimax in a persistent process pool (one future per root move)."""

    def __init__(self, workers: int) -> None:
        pool_size = MinMaxAgent.resolve_pool_workers(workers)
        self._executor = ProcessPoolExecutor(max_workers=pool_size)
        self._workers = workers
        self._pool_size = pool_size
        self._futures: list[Future] = []
        self._instant_move: Move4 | None = None
        self._parallel = False

    @property
    def pool_size(self) -> int:
        return self._pool_size

    @property
    def thinking(self) -> bool:
        if self._instant_move is not None:
            return False
        if not self._futures:
            return False
        return not all(f.done() for f in self._futures)

    def request_move(self, board: Board, agent: MinMaxAgent) -> None:
        if self.thinking or self._instant_move is not None:
            return
        self._futures = []
        self._parallel = False

        state_tuple = board.to_search_state()
        moves = board.state.generate_legal_moves()
        if not moves:
            return
        if len(moves) == 1:
            self._instant_move = moves[0]
            return

        payload = (state_tuple, agent.depth, agent.color.value, agent.max_n_samples)
        parallel_workers = agent._worker_count(len(moves))
        if parallel_workers <= 1:
            self._futures = [self._executor.submit(_choose_move_serial, payload)]
            return

        state = BoardState.from_search_state(state_tuple)
        ordered = _order_moves(state, moves)
        self._parallel = True
        self._futures = [self._executor.submit(_score_root_move, payload, move) for move in ordered]

    def take_move(self) -> Move | None:
        if self._instant_move is not None:
            coords = self._instant_move
            self._instant_move = None
            return MinMaxAgent._coords_to_move(coords)
        if not self._futures or self.thinking:
            return None

        if self._parallel:
            best_move: Move4 | None = None
            best_value = float("-inf")
            for future in self._futures:
                move_coords, value = future.result()
                if value > best_value or best_move is None:
                    best_value = value
                    best_move = move_coords
            coords = best_move
        else:
            coords = self._futures[0].result()

        self._futures = []
        self._parallel = False
        if coords is None:
            return None
        return MinMaxAgent._coords_to_move(coords)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
        shutdown_search_pool()


def _game_over(board: Board) -> bool:
    return (
        board.checkmates[Color.WHITE] != Ending.ONGOING
        or board.checkmates[Color.BLACK] != Ending.ONGOING
    )


def run_vs_ai(settings: AppSettings) -> None:
    display = settings.display
    square_size = display.square_size
    window_w, window_h = vs_ai_window_size(square_size)

    pygame.init()
    pygame.display.set_caption("Chess vs Minimax AI")
    screen = pygame.display.set_mode((window_w, window_h))
    clock = pygame.time.Clock()

    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.promotion = settings.game.promotion
    board.update()

    ai = MinMaxAgent(
        color=settings.ai.color,
        depth=settings.ai.depth,
        max_n_samples=settings.ai.max_n_samples,
        workers=settings.ai.workers,
    )
    bg_ai = _BackgroundAi(workers=settings.ai.workers)
    think_frame = 0

    logger.info(
        "[green]Game started[/green] — depth=%d, workers=%s (pool=%d), you are White",
        settings.ai.depth,
        "auto" if settings.ai.workers <= 0 else str(settings.ai.workers),
        bg_ai.pool_size,
    )

    human_input = board.turn == Color.WHITE and not _game_over(board)

    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif human_input:
                    board.handle_event(event, square_size=square_size)

            human_input = board.turn == Color.WHITE and not _game_over(board)

            if not _game_over(board) and board.turn == settings.ai.color:
                move = bg_ai.take_move()
                if move is not None:
                    if MinMaxAgent.apply_move(board, move):
                        logger.debug("AI played %s", move)
                    else:
                        logger.warning("AI move failed: %s", move)
                elif not bg_ai.thinking:
                    bg_ai.request_move(board, ai)

            if bg_ai.thinking:
                think_frame += 1

            layers, layout = render_vs_ai_scene(
                board,
                square_size,
                ai_thinking=bg_ai.thinking,
                think_frame=think_frame,
                ai_depth=settings.ai.depth,
            )
            blit_scene(screen, layers, layout)
            pygame.display.flip()
            clock.tick(60)
    finally:
        bg_ai.shutdown()

    pygame.quit()
    logger.info("Game closed")
