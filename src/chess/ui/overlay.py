"""Instructions, status, and side-panel rendering on the overlay layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from chess.layout import SIDE_PANEL_WIDTH, WINDOW_PADDING
from chess.ui.colors import GOLD, MUTED, TEAL, TEXT
from chess.ui.text import draw_wrapped_text, measure_wrapped_text
from chess.ui.theme import draw_button, draw_panel, ui_font

if TYPE_CHECKING:
    from chess.core.board import Board
    from chess.core.types import Color

PANEL_PAD = 20
PANEL_GAP = 12

PIECE_TYPES = ("Pawn", "Bishop", "Rook", "Queen", "Knight", "King")


def _panel_content_width() -> int:
    return SIDE_PANEL_WIDTH - WINDOW_PADDING - PANEL_PAD * 2


def _game_over(board: Board) -> bool:
    from chess.core.types import Color, Ending

    return (
        board.checkmates[Color.WHITE] != Ending.ONGOING
        or board.checkmates[Color.BLACK] != Ending.ONGOING
    )


def status_message(board: Board, *, ai_thinking: bool, think_frame: int) -> str:
    from chess.core.types import Color, Ending

    if _game_over(board):
        if board.checkmates[Color.WHITE] == Ending.CHECKMATE:
            return "Checkmate — you lose"
        if board.checkmates[Color.BLACK] == Ending.CHECKMATE:
            return "Checkmate — you win"
        return "Draw"

    if ai_thinking or board.turn != Color.WHITE:
        dots = "." * (think_frame % 3 + 1)
        return f"Black is thinking{dots}"

    if board.checks[Color.WHITE]:
        return "Your move — in check"
    return "Your move"


def detail_message(board: Board, *, ai_thinking: bool, ai_depth: int) -> str:
    if _game_over(board):
        return "Close the window to exit."

    if ai_thinking:
        return f"Minimax search at depth {ai_depth}"

    if board.last_move is not None:
        origin, target = board.last_move
        return f"Last move: {origin} to {target}"

    return "Drag a white piece to play."


def measure_status_panel_height(
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    board: Board,
    *,
    ai_thinking: bool,
    think_frame: int,
    ai_depth: int,
) -> int:
    content_w = _panel_content_width()
    height = PANEL_PAD
    height += font.get_linesize() + PANEL_GAP
    height += measure_wrapped_text(
        font,
        status_message(board, ai_thinking=ai_thinking, think_frame=think_frame),
        content_w,
        line_gap=4,
    )
    height += PANEL_GAP
    height += measure_wrapped_text(
        small_font,
        detail_message(board, ai_thinking=ai_thinking, ai_depth=ai_depth),
        content_w,
    )
    height += PANEL_PAD
    return height


def render_vs_ai_overlay(
    surface: pygame.Surface,
    font: pygame.font.Font,
    small_font: pygame.font.Font,
    board: Board,
    *,
    panel_top: int = WINDOW_PADDING,
    ai_thinking: bool = False,
    think_frame: int = 0,
    ai_depth: int = 3,
) -> None:
    """Draw Vs AI status onto the overlay layer at local coordinates."""
    surface.fill((0, 0, 0, 0))
    panel_w = SIDE_PANEL_WIDTH - WINDOW_PADDING
    content_w = _panel_content_width()
    inner_x = PANEL_PAD
    status_height = measure_status_panel_height(
        font,
        small_font,
        board,
        ai_thinking=ai_thinking,
        think_frame=think_frame,
        ai_depth=ai_depth,
    )
    panel_rect = pygame.Rect(0, panel_top, panel_w, status_height)
    accent = GOLD if _game_over(board) else TEAL
    draw_panel(surface, panel_rect, accent=accent)

    y = panel_rect.y + PANEL_PAD
    headline = status_message(board, ai_thinking=ai_thinking, think_frame=think_frame)
    headline_rect = pygame.Rect(inner_x, y, content_w, font.get_linesize() * 2)
    used = draw_wrapped_text(surface, font, headline, TEXT, headline_rect, line_gap=4)
    y += used + PANEL_GAP

    detail = detail_message(board, ai_thinking=ai_thinking, ai_depth=ai_depth)
    detail_rect = pygame.Rect(inner_x, y, content_w, small_font.get_linesize() * 3)
    draw_wrapped_text(surface, small_font, detail, MUTED, detail_rect)


def render_sandbox_overlay(
    surface: pygame.Surface,
    *,
    panel_top: int = WINDOW_PADDING,
    panel_height: int,
    new_piece_color: Color,
    mouse_pos: tuple[int, int] | None = None,
) -> None:
    """Draw sandbox side panel onto the overlay layer at local coordinates."""
    surface.fill((0, 0, 0, 0))
    panel_w = SIDE_PANEL_WIDTH - WINDOW_PADDING
    panel_rect = pygame.Rect(0, panel_top, panel_w, panel_height)
    title_font = ui_font(28, bold=True)
    body_font = ui_font(20)
    button_font = ui_font(18, bold=True)

    draw_panel(surface, panel_rect, accent=TEAL)
    title = title_font.render("Sandbox", True, TEXT)
    surface.blit(title, (panel_rect.x + 24, panel_rect.y + 24))
    hint = body_font.render("Free board — no turn limits.", True, MUTED)
    surface.blit(hint, (panel_rect.x + 24, panel_rect.y + 58))

    button_width = panel_w - 32
    button_height = 44
    button_x = panel_rect.x + 16
    button_y_offset = panel_rect.y + 96
    local_mouse = mouse_pos

    for index, piece_type in enumerate(PIECE_TYPES):
        top = button_y_offset + index * (button_height + 12)
        button_rect = pygame.Rect(button_x, top, button_width, button_height)
        hovered = local_mouse is not None and button_rect.collidepoint(local_mouse)
        draw_button(
            surface,
            button_rect,
            f"Add {piece_type}",
            button_font,
            accent=TEAL,
            hovered=hovered,
        )

    toggle_y = button_y_offset + len(PIECE_TYPES) * (button_height + 12) + 12
    toggle_rect = pygame.Rect(button_x, toggle_y, button_width, button_height)
    toggle_label = f"Spawn as {new_piece_color.name.title()}"
    toggle_hovered = local_mouse is not None and toggle_rect.collidepoint(local_mouse)
    draw_button(
        surface,
        toggle_rect,
        toggle_label,
        button_font,
        accent=GOLD,
        hovered=toggle_hovered,
    )
