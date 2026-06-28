"""Shared color palette for the app and README figures."""

from __future__ import annotations

from chess.core.types import Color, PieceType

BG = (15, 20, 28)
PANEL = (23, 32, 44)
PANEL_2 = (29, 40, 54)
TEXT = (244, 240, 232)
MUTED = (174, 184, 197)
LINE = (50, 66, 84)
TEAL = (61, 214, 208)
GOLD = (245, 185, 79)
CORAL = (241, 118, 102)
GREEN = (123, 216, 143)
BLUE = (115, 167, 255)
VIOLET = (185, 156, 255)

BOARD_FRAME = (11, 17, 24)
BOARD_BORDER = (61, 77, 96)
LIGHT_SQUARE = (239, 228, 205)
DARK_SQUARE = (73, 97, 115)

PIECE_GLYPH = {
    PieceType.PAWN: "P",
    PieceType.ROOK: "R",
    PieceType.KNIGHT: "N",
    PieceType.BISHOP: "B",
    PieceType.QUEEN: "Q",
    PieceType.KING: "K",
}

PIECE_COLOR = {
    Color.WHITE: (249, 244, 233),
    Color.BLACK: (17, 24, 32),
}

MONO_FONTS = ("dejavusansmono", "liberation mono", "consolas", "courier new", "monospace")
UI_FONTS = ("inter", "dejavusans", "liberation sans", "sans")


def rgb_hex(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
