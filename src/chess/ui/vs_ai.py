"""Human vs minimax AI (you play White)."""

from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from copy import deepcopy

import pygame

from chess.ai.minmax import MinMaxAgent, Move, choose_move_in_subprocess
from chess.config import AppSettings
from chess.core.board import Board
from chess.core.piece import STARTING_PIECES
from chess.core.types import Color, Ending
from chess.layout import vs_ai_window_size
from chess.log import get_logger
from chess.ui.scene import blit_scene, render_vs_ai_scene

logger = get_logger(__name__)


class _BackgroundAi:
    def __init__(self, workers: int) -> None:
        self._executor = ProcessPoolExecutor(max_workers=1)
        self._future: Future | None = None
        self._workers = workers

    @property
    def thinking(self) -> bool:
        return self._future is not None and not self._future.done()

    def request_move(self, board: Board, agent: MinMaxAgent) -> None:
        if self.thinking:
            return
        self._future = self._executor.submit(
            choose_move_in_subprocess,
            board.to_search_state(),
            agent.depth,
            agent.color,
            agent.max_n_samples,
            self._workers,
        )

    def take_move(self) -> Move | None:
        if self._future is None or not self._future.done():
            return None
        coords = self._future.result()
        self._future = None
        if coords is None:
            return None
        return MinMaxAgent._coords_to_move(coords)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


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
        "[green]Game started[/green] — depth=%d, workers=%s, you are White",
        settings.ai.depth,
        "auto" if settings.ai.workers <= 0 else str(settings.ai.workers),
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
