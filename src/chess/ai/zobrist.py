"""Zobrist hashing for transposition tables."""

from __future__ import annotations

import random

from chess.core.types import Color, PieceType

random.seed(0xC055000)

_PIECE_TYPES = len(PieceType)

ZOBRIST_TURN = random.getrandbits(64)
ZOBRIST_PIECES: list[list[list[int]]] = [
    [[random.getrandbits(64) for _ in range(_PIECE_TYPES)] for _ in Color] for _ in range(64)
]


def square_index(x: int, y: int) -> int:
    return y * 8 + x
