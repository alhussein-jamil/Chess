from enum import Enum


class Ending(Enum):
    CHECKMATE = 1
    STALEMATE = 2
    DRAW = 3
    ONGOING = 4


DIM_X: int = 8
DIM_Y: int = 8
SQUARE_SIZE: int = 100


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
ILLEGAL = [
    MoveState.UNREACHABLE,
    MoveState.OCCUPIED,
    MoveState.CHECKED,
    MoveState.NOTALLOWED,
    MoveState.BLOCKED,
]


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
