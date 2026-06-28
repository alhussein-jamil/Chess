"""Two-layer scene rendering: board layer + overlay layer."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from chess.layout import (
    SIDE_PANEL_WIDTH,
    WINDOW_PADDING,
    board_area_size,
    vs_ai_panel_x,
    vs_ai_window_size,
)
from chess.ui.colors import BG


@dataclass(frozen=True)
class SceneLayout:
    board_origin: tuple[int, int]
    overlay_origin: tuple[int, int]


@dataclass
class SceneLayers:
    """Separate surfaces for board state and UI/instructions."""

    board: pygame.Surface
    overlay: pygame.Surface


def board_layer_size(square_size: int) -> tuple[int, int]:
    return board_area_size(square_size)


def overlay_layer_size(window_height: int) -> tuple[int, int]:
    return SIDE_PANEL_WIDTH, window_height


def create_board_layer(square_size: int) -> pygame.Surface:
    width, height = board_layer_size(square_size)
    surface = pygame.Surface((width, height))
    surface.fill(BG)
    return surface


def create_overlay_layer(window_height: int) -> pygame.Surface:
    width, height = overlay_layer_size(window_height)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    return surface


def vs_ai_scene_layout(square_size: int) -> SceneLayout:
    _, window_h = vs_ai_window_size(square_size)
    return SceneLayout(
        board_origin=(0, 0),
        overlay_origin=(vs_ai_panel_x(square_size), 0),
    )


def sandbox_scene_layout(square_size: int, window_width: int) -> SceneLayout:
    board_area_w, window_h = board_area_size(square_size)
    panel_x = max(
        board_area_w + WINDOW_PADDING,
        window_width - SIDE_PANEL_WIDTH - WINDOW_PADDING,
    )
    return SceneLayout(board_origin=(0, 0), overlay_origin=(panel_x, 0))


def compose_layers(
    target: pygame.Surface,
    layers: SceneLayers,
    layout: SceneLayout,
    *,
    background: tuple[int, int, int] = BG,
) -> None:
    target.fill(background)
    target.blit(layers.board, layout.board_origin)
    target.blit(layers.overlay, layout.overlay_origin)
