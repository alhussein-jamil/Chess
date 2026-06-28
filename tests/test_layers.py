"""Layered scene rendering checks."""

import os
from copy import deepcopy

import pygame

from chess.core.board import Board
from chess.core.piece import STARTING_PIECES
from chess.core.types import Color
from chess.layout import board_area_size, vs_ai_window_size
from chess.ui.layers import board_layer_size, overlay_layer_size
from chess.ui.scene import blit_scene, render_vs_ai_scene


def test_vs_ai_scene_layers_have_expected_sizes() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    pygame.display.set_mode((1, 1))

    square_size = 100
    _, window_h = vs_ai_window_size(square_size)
    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.turn = Color.BLACK

    layers, layout = render_vs_ai_scene(
        board,
        square_size,
        ai_thinking=True,
        think_frame=1,
    )

    assert layers.board.get_size() == board_layer_size(square_size)
    assert layers.board.get_size() == board_area_size(square_size)
    assert layers.overlay.get_size() == overlay_layer_size(window_h)
    assert layout.board_origin == (0, 0)
    assert layout.overlay_origin[0] > layers.board.get_width()


def test_compose_layers_writes_board_and_overlay_pixels() -> None:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    pygame.init()
    pygame.display.set_mode((1, 1))

    square_size = 100
    window_w, window_h = vs_ai_window_size(square_size)
    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    layers, layout = render_vs_ai_scene(board, square_size, ai_thinking=True, think_frame=1)

    target = pygame.Surface((window_w, window_h))
    blit_scene(target, layers, layout)

    board_pixel = target.get_at(layout.board_origin)
    overlay_pixel = target.get_at(layout.overlay_origin)
    assert board_pixel.a == 255
    assert overlay_pixel.a == 255
