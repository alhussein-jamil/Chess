"""Pygame window layout helpers."""

from __future__ import annotations

from chess.core.types import DIM_X, DIM_Y

SIDE_PANEL_WIDTH = 250
WINDOW_PADDING = 12
BOARD_INSET = 8
GUTTER_GAP = 2


def board_pixel_size(square_size: int) -> tuple[int, int]:
    return DIM_X * square_size, DIM_Y * square_size


def board_frame_size(square_size: int) -> tuple[int, int]:
    board_w, board_h = board_pixel_size(square_size)
    return board_w + BOARD_INSET * 2, board_h + BOARD_INSET * 2


def label_gutter_size(square_size: int) -> int:
    return max(36, square_size // 3)


def rank_label_column_x(square_size: int) -> int:
    frame_w, _ = board_frame_size(square_size)
    return frame_w + GUTTER_GAP


def rank_label_column_width(square_size: int) -> int:
    return label_gutter_size(square_size)


def file_label_row_y(square_size: int) -> int:
    _, frame_h = board_frame_size(square_size)
    return frame_h + GUTTER_GAP


def file_label_row_height(square_size: int) -> int:
    return label_gutter_size(square_size)


def board_area_size(square_size: int) -> tuple[int, int]:
    frame_w, frame_h = board_frame_size(square_size)
    gutter = label_gutter_size(square_size)
    return frame_w + GUTTER_GAP + gutter, frame_h + GUTTER_GAP + gutter


def vs_ai_window_size(square_size: int) -> tuple[int, int]:
    area_w, area_h = board_area_size(square_size)
    width = area_w + SIDE_PANEL_WIDTH + WINDOW_PADDING
    height = area_h + WINDOW_PADDING
    return width, height


def vs_ai_panel_x(square_size: int) -> int:
    area_w, _ = board_area_size(square_size)
    return area_w + 8


# Backwards-compatible aliases used by tests and older call sites.
RANK_LABEL_WIDTH = 36
FILE_LABEL_HEIGHT = 36


def rank_label_x(square_size: int) -> int:
    return rank_label_column_x(square_size)


def file_label_y(square_size: int) -> int:
    return file_label_row_y(square_size)
