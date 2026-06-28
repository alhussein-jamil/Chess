"""High-level two-layer scene rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from chess.layout import WINDOW_PADDING, vs_ai_window_size
from chess.ui.layers import (
    SceneLayers,
    SceneLayout,
    compose_layers,
    create_board_layer,
    create_overlay_layer,
    sandbox_scene_layout,
    vs_ai_scene_layout,
)
from chess.ui.overlay import render_sandbox_overlay, render_vs_ai_overlay
from chess.ui.render import render_board_layer
from chess.ui.theme import ui_font

if TYPE_CHECKING:
    from chess.core.board import Board
    from chess.core.types import Color


def render_vs_ai_scene(
    board: Board,
    square_size: int,
    *,
    ai_thinking: bool = False,
    think_frame: int = 0,
    ai_depth: int = 3,
) -> tuple[SceneLayers, SceneLayout]:
    _, window_h = vs_ai_window_size(square_size)
    layout = vs_ai_scene_layout(square_size)
    layers = SceneLayers(
        board=create_board_layer(square_size),
        overlay=create_overlay_layer(window_h),
    )
    render_board_layer(layers.board, board, square_size)
    render_vs_ai_overlay(
        layers.overlay,
        ui_font(24, bold=True),
        ui_font(16),
        board,
        ai_thinking=ai_thinking,
        think_frame=think_frame,
        ai_depth=ai_depth,
    )
    return layers, layout


def render_sandbox_scene(
    board: Board,
    square_size: int,
    window_width: int,
    window_height: int,
    *,
    new_piece_color: Color,
    mouse_pos: tuple[int, int] | None = None,
) -> tuple[SceneLayers, SceneLayout]:
    layout = sandbox_scene_layout(square_size, window_width)
    layers = SceneLayers(
        board=create_board_layer(square_size),
        overlay=create_overlay_layer(window_height),
    )
    render_board_layer(layers.board, board, square_size)
    overlay_mouse = None
    if mouse_pos is not None:
        overlay_mouse = (
            mouse_pos[0] - layout.overlay_origin[0],
            mouse_pos[1] - layout.overlay_origin[1],
        )
    render_sandbox_overlay(
        layers.overlay,
        panel_height=window_height - WINDOW_PADDING * 2,
        new_piece_color=new_piece_color,
        mouse_pos=overlay_mouse,
    )
    return layers, layout


def blit_scene(target: pygame.Surface, layers: SceneLayers, layout: SceneLayout) -> None:
    compose_layers(target, layers, layout)
