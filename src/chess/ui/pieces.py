"""Cached piece sprite loading for the Pygame board."""

from __future__ import annotations

import pygame

from chess.core.piece import Piece
from chess.core.types import Color, PieceType
from chess.paths import ASSETS_DIR

_BASE_CACHE: dict[tuple[PieceType, Color], pygame.Surface] = {}
_SCALED_CACHE: dict[tuple[PieceType, Color, int], pygame.Surface] = {}


def _load_base(piece_type: PieceType, color: Color) -> pygame.Surface:
    key = (piece_type, color)
    cached = _BASE_CACHE.get(key)
    if cached is not None:
        return cached

    path = ASSETS_DIR / f"{piece_type.name.lower()}_{color.name.lower()}.png"
    if not path.exists():
        raise FileNotFoundError(f"Missing piece asset: {path}")

    image = pygame.image.load(path.as_posix()).convert_alpha()
    _BASE_CACHE[key] = image
    return image


def piece_surface(piece: Piece, square_size: int) -> pygame.Surface:
    return piece_surface_for(piece.piece_type, piece.color, square_size)


def piece_surface_for(piece_type: PieceType, color: Color, square_size: int) -> pygame.Surface:
    key = (piece_type, color, square_size)
    cached = _SCALED_CACHE.get(key)
    if cached is not None:
        return cached

    base = _load_base(piece_type, color)
    scaled = pygame.transform.scale(base, (square_size, square_size))
    _SCALED_CACHE[key] = scaled
    return scaled


def draw_piece(
    surface: pygame.Surface,
    piece: Piece,
    x: int,
    y: int,
    square_size: int,
    *,
    alpha: int = 255,
) -> None:
    sprite = piece_surface(piece, square_size)
    if alpha < 255:
        sprite = sprite.copy()
        sprite.set_alpha(alpha)
    surface.blit(sprite, (x, y))
