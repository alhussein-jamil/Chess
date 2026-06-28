"""Free-play sandbox with drag-and-drop pieces."""

from __future__ import annotations

from copy import deepcopy

import pygame

from chess.config import AppSettings
from chess.core.board import Board
from chess.core.piece import (
    STARTING_PIECES,
    Bishop,
    Color,
    King,
    Knight,
    Pawn,
    Queen,
    Rook,
)
from chess.layout import SIDE_PANEL_WIDTH, WINDOW_PADDING
from chess.log import get_logger
from chess.ui.scene import blit_scene, render_sandbox_scene

logger = get_logger(__name__)

PIECE_TYPES = ("Pawn", "Bishop", "Rook", "Queen", "Knight", "King")
PIECE_FACTORIES = {
    "Pawn": Pawn,
    "Rook": Rook,
    "Bishop": Bishop,
    "Queen": Queen,
    "Knight": Knight,
    "King": King,
}
BUTTON_HEIGHT = 44
BUTTON_GAP = 12


def _sandbox_button_rects() -> tuple[list[pygame.Rect], pygame.Rect]:
    panel_w = SIDE_PANEL_WIDTH - WINDOW_PADDING
    button_width = panel_w - 32
    button_x = 16
    button_y_offset = WINDOW_PADDING + 96
    buttons = [
        pygame.Rect(
            button_x,
            button_y_offset + index * (BUTTON_HEIGHT + BUTTON_GAP),
            button_width,
            BUTTON_HEIGHT,
        )
        for index in range(len(PIECE_TYPES))
    ]
    toggle_y = button_y_offset + len(PIECE_TYPES) * (BUTTON_HEIGHT + BUTTON_GAP) + BUTTON_GAP
    toggle = pygame.Rect(button_x, toggle_y, button_width, BUTTON_HEIGHT)
    return buttons, toggle


def _overlay_local_mouse(
    mouse_pos: tuple[int, int],
    overlay_origin: tuple[int, int],
) -> tuple[int, int]:
    return mouse_pos[0] - overlay_origin[0], mouse_pos[1] - overlay_origin[1]


def run_sandbox(settings: AppSettings) -> None:
    display = settings.display
    pygame.init()
    pygame.display.set_caption("Chess — sandbox")
    screen = pygame.display.set_mode((display.sandbox_width, display.sandbox_height))

    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.update()

    square_size = display.square_size
    new_piece_color = Color.WHITE
    running = True

    logger.info("[green]Sandbox ready[/green] — drag pieces or add from the panel")

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            board.handle_event(event, square_size=square_size)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _, layout = render_sandbox_scene(
                    board,
                    square_size,
                    display.sandbox_width,
                    display.sandbox_height,
                    new_piece_color=new_piece_color,
                )
                local = _overlay_local_mouse(mouse_pos, layout.overlay_origin)
                piece_buttons, toggle_button = _sandbox_button_rects()
                for piece_type, button_rect in zip(PIECE_TYPES, piece_buttons, strict=True):
                    if button_rect.collidepoint(local):
                        board.dragged_piece = PIECE_FACTORIES[piece_type](color=new_piece_color)
                if toggle_button.collidepoint(local):
                    new_piece_color = Color.WHITE if new_piece_color == Color.BLACK else Color.BLACK

        layers, layout = render_sandbox_scene(
            board,
            square_size,
            display.sandbox_width,
            display.sandbox_height,
            new_piece_color=new_piece_color,
            mouse_pos=mouse_pos,
        )
        blit_scene(screen, layers, layout)
        pygame.display.flip()

    pygame.quit()
    logger.info("Sandbox closed")
