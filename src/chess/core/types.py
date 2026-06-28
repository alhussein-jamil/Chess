"""Shared chess enums and board constants."""

from enum import Enum

DIM_X = 8
DIM_Y = 8
SQUARE_SIZE = 100


class Ending(Enum):
    CHECKMATE = 1
    STALEMATE = 2
    DRAW = 3
    ONGOING = 4


class MoveState(Enum):
    MOVED = 1
    CAPTURED = 2
    UNREACHABLE = 3
    OCCUPIED = 4
    CHECKED = 5
    CREATED = 6
    BLOCKED = 7
    NOTALLOWED = 8


LEGAL = [MoveState.MOVED, MoveState.CAPTURED, MoveState.CREATED]


class Color(Enum):
    WHITE = 1
    BLACK = 2
    UNDEFINED = 3


class PieceType(Enum):
    PAWN = 1
    ROOK = 2
    KNIGHT = 3
    BISHOP = 4
    QUEEN = 5
    KING = 6
    UNDEFINED = 7


PROMOTION_TYPES = frozenset({"queen", "rook", "bishop", "knight"})
AI_COLORS = frozenset({"white", "black"})
