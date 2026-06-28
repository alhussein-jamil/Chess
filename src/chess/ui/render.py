"""Board and piece rendering helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from chess.core.piece import NullPiece, Position
from chess.core.types import DIM_X, DIM_Y, Color, Ending
from chess.layout import (
    BOARD_INSET,
    file_label_row_height,
    file_label_row_y,
    rank_label_column_width,
    rank_label_column_x,
)
from chess.ui.colors import (
    BOARD_BORDER,
    BOARD_FRAME,
    DARK_SQUARE,
    GOLD,
    LIGHT_SQUARE,
    MUTED,
    PANEL_2,
    TEXT,
)
from chess.ui.pieces import draw_piece
from chess.ui.theme import ui_font

if TYPE_CHECKING:
    from chess.core.board import Board


def render_board_layer(surface: pygame.Surface, board: Board, square_size: int) -> None:
    """Render the chess board onto a dedicated board-layer surface."""
    board_w = DIM_X * square_size
    board_h = DIM_Y * square_size
    frame_rect = pygame.Rect(0, 0, board_w + BOARD_INSET * 2, board_h + BOARD_INSET * 2)
    pygame.draw.rect(surface, BOARD_FRAME, frame_rect, border_radius=12)
    pygame.draw.rect(surface, BOARD_BORDER, frame_rect, width=1, border_radius=12)

    for x in range(DIM_X):
        for y in range(DIM_Y):
            color = LIGHT_SQUARE if (x + y) % 2 == 0 else DARK_SQUARE
            pygame.draw.rect(
                surface,
                color,
                (
                    BOARD_INSET + x * square_size,
                    BOARD_INSET + y * square_size,
                    square_size,
                    square_size,
                ),
            )

    _draw_last_move_highlight(surface, board, square_size)
    _draw_coordinate_labels(surface, square_size)
    _draw_game_over_banner(surface, board, square_size)
    _draw_pieces(surface, board, square_size)


def _draw_last_move_highlight(surface: pygame.Surface, board: Board, square_size: int) -> None:
    if board.last_move is None:
        return
    overlay = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
    overlay.fill((*GOLD, 90))
    for position in board.last_move:
        if board.in_bounds(position):
            surface.blit(
                overlay,
                (
                    BOARD_INSET + position.x * square_size,
                    BOARD_INSET + position.y * square_size,
                ),
            )


def _draw_coordinate_labels(surface: pygame.Surface, square_size: int) -> None:
    rank_x = rank_label_column_x(square_size)
    rank_w = rank_label_column_width(square_size)
    file_y = file_label_row_y(square_size)
    file_h = file_label_row_height(square_size)
    label_font = ui_font(max(14, min(square_size // 2, rank_w - 10, file_h - 10)), bold=True)

    for index, number in enumerate("87654321"):
        cell = pygame.Rect(rank_x, BOARD_INSET + index * square_size, rank_w, square_size)
        fill = PANEL_2 if index % 2 == 0 else BOARD_FRAME
        pygame.draw.rect(surface, fill, cell, border_radius=4)
        pygame.draw.rect(surface, BOARD_BORDER, cell, width=1, border_radius=4)
        text = label_font.render(number, True, MUTED)
        surface.blit(text, text.get_rect(center=cell.center))

    for index, letter in enumerate("ABCDEFGH"):
        cell = pygame.Rect(BOARD_INSET + index * square_size, file_y, square_size, file_h)
        fill = PANEL_2 if index % 2 == 0 else BOARD_FRAME
        pygame.draw.rect(surface, fill, cell, border_radius=4)
        pygame.draw.rect(surface, BOARD_BORDER, cell, width=1, border_radius=4)
        text = label_font.render(letter, True, MUTED)
        surface.blit(text, text.get_rect(center=cell.center))

    corner = pygame.Rect(rank_x, file_y, rank_w, file_h)
    pygame.draw.rect(surface, BOARD_FRAME, corner, border_radius=4)
    pygame.draw.rect(surface, BOARD_BORDER, corner, width=1, border_radius=4)


def _draw_game_over_banner(
    surface: pygame.Surface,
    board: Board,
    square_size: int,
) -> None:
    message: str | None = None
    if board.checkmates[Color.WHITE] == Ending.CHECKMATE:
        message = "Checkmate — Black wins"
    elif board.checkmates[Color.BLACK] == Ending.CHECKMATE:
        message = "Checkmate — White wins"
    elif board.checkmates[Color.WHITE] in (Ending.STALEMATE, Ending.DRAW) or board.checkmates[
        Color.BLACK
    ] in (Ending.STALEMATE, Ending.DRAW):
        message = "Draw"

    if message is None:
        return

    banner_font = ui_font(max(24, square_size // 3), bold=True)
    text = banner_font.render(message, True, TEXT)
    center_x = BOARD_INSET + DIM_X * square_size // 2
    center_y = BOARD_INSET + DIM_Y * square_size // 2
    padding_x = 24
    padding_y = 14
    banner_rect = pygame.Rect(
        center_x - text.get_width() // 2 - padding_x,
        center_y - text.get_height() // 2 - padding_y,
        text.get_width() + padding_x * 2,
        text.get_height() + padding_y * 2,
    )
    pygame.draw.rect(surface, BOARD_FRAME, banner_rect, border_radius=12)
    pygame.draw.rect(surface, GOLD, banner_rect, width=2, border_radius=12)
    surface.blit(text, text.get_rect(center=banner_rect.center))


def _draw_pieces(surface: pygame.Surface, board: Board, square_size: int) -> None:
    for y in range(DIM_Y):
        for x in range(DIM_X):
            position = Position(x, y)
            piece = board.board[position]
            if isinstance(piece, NullPiece) or piece == board.dragged_piece:
                continue
            draw_piece(
                surface,
                piece,
                BOARD_INSET + x * square_size,
                BOARD_INSET + y * square_size,
                square_size,
            )

    if board.dragged_piece is None:
        return

    hover = board.mouse_to_grid(pygame.mouse.get_pos(), square_size)
    if board.in_bounds(hover):
        draw_x = BOARD_INSET + hover.x * square_size
        draw_y = BOARD_INSET + hover.y * square_size
    elif board.drag_origin is not None:
        draw_x = BOARD_INSET + board.drag_origin.x * square_size
        draw_y = BOARD_INSET + board.drag_origin.y * square_size
    else:
        mouse_pos = pygame.mouse.get_pos()
        draw_x = mouse_pos[0] - square_size // 2
        draw_y = mouse_pos[1] - square_size // 2

    draw_piece(
        surface,
        board.dragged_piece,
        draw_x,
        draw_y,
        square_size,
        alpha=220,
    )


def render_board(surface: pygame.Surface, board: Board, square_size: int) -> None:
    """Backwards-compatible alias for single-surface board rendering."""
    render_board_layer(surface, board, square_size)
