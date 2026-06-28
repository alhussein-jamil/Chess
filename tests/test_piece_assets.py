"""Piece asset presence checks."""

from chess.core.types import Color, PieceType
from chess.paths import ASSETS_DIR


def test_piece_png_assets_exist() -> None:
    for piece_type in PieceType:
        if piece_type.name == "UNDEFINED":
            continue
        for color in (Color.WHITE, Color.BLACK):
            path = ASSETS_DIR / f"{piece_type.name.lower()}_{color.name.lower()}.png"
            assert path.is_file(), f"missing piece asset: {path}"
