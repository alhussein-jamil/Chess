"""Side panel layout checks."""

import os

import pygame

from chess.core.board import Board
from chess.core.piece import STARTING_PIECES
from chess.core.types import Color
from chess.ui.overlay import PANEL_PAD, detail_message, measure_status_panel_height, status_message
from chess.ui.text import measure_wrapped_text
from chess.ui.theme import ui_font


def _panel_content_width() -> int:
    from chess.layout import SIDE_PANEL_WIDTH, WINDOW_PADDING

    return SIDE_PANEL_WIDTH - WINDOW_PADDING - PANEL_PAD * 2


def test_status_panel_fits_thinking_copy() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    pygame.display.set_mode((1, 1))

    font = ui_font(24, bold=True)
    small_font = ui_font(16)
    board = Board.from_pieces(list(STARTING_PIECES))
    board.turn = Color.BLACK

    height = measure_status_panel_height(
        font,
        small_font,
        board,
        ai_thinking=True,
        think_frame=1,
        ai_depth=3,
    )
    content_w = _panel_content_width()
    required = PANEL_PAD
    required += font.get_linesize() + 12
    headline = status_message(board, ai_thinking=True, think_frame=1)
    required += measure_wrapped_text(font, headline, content_w, line_gap=4)
    required += 12
    required += measure_wrapped_text(
        small_font,
        detail_message(board, ai_thinking=True, ai_depth=3),
        content_w,
    )
    required += PANEL_PAD

    assert height >= required


def test_status_panel_fits_player_turn_copy() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    pygame.display.set_mode((1, 1))

    font = ui_font(24, bold=True)
    small_font = ui_font(16)
    board = Board.from_pieces(list(STARTING_PIECES))

    height = measure_status_panel_height(
        font,
        small_font,
        board,
        ai_thinking=False,
        think_frame=0,
        ai_depth=4,
    )
    content_w = _panel_content_width()
    required = PANEL_PAD
    required += font.get_linesize() + 12
    headline = status_message(board, ai_thinking=False, think_frame=0)
    required += measure_wrapped_text(font, headline, content_w, line_gap=4)
    required += 12
    required += measure_wrapped_text(
        small_font,
        detail_message(board, ai_thinking=False, ai_depth=4),
        content_w,
    )
    required += PANEL_PAD

    assert height >= required
