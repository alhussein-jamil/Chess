import dataclasses as dc
from enum import Enum
from pathlib import Path
from typing import List

import pygame


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


class PieceType(Enum):
    PAWN = 1
    ROOK = 2
    KNIGHT = 3
    BISHOP = 4
    QUEEN = 5
    KING = 6
    UNDEFINED = 7


@dc.dataclass
class Position:
    x: int
    y: int

    def move(self, x, y):
        self.x += x
        self.y += y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __repr__(self):
        # x represented by letters and y represented by numbers
        return f"{chr(97 + self.x)}{8 - self.y}"


@dc.dataclass
class Piece:
    color: Color = Color.WHITE
    piece_type: PieceType = PieceType.UNDEFINED
    position: Position = Position(4, 4)
    name: str = "Piece"
    icon: pygame.Surface = None
    moved: int = 0
    created: bool = False
    legal_moves: List = dc.field(default_factory=list)

    def __post_init__(self):
        try:
            self.icon = pygame.image.load(
                Path(
                    f"assets/{self.piece_type.name.lower()}_{self.color.name.lower()}.png"
                )
            ).convert_alpha()

        except:
            pass

    def __str__(self):
        return f"{self.color.name} {self.piece_type.name} at {self.position}"

    def _is_legal_move(self, new_position, board: "Board"):
        if new_position in self.legal_moves:
            if board.get(new_position) is not None:
                if board.get(new_position).color != self.color:
                    return [MoveState.CAPTURED]
                else:
                    return [MoveState.OCCUPIED]
            return [MoveState.CAPTURED, MoveState.MOVED]
        return [MoveState.NOTALLOWED]

    def update_legal_moves(self, board: "Board"):
        pass

    def move(self, new_position, board: "Board"):

        if self.created == False:
            self.position = new_position
            self.created = True
            return [MoveState.CREATED]

        legality = self._is_legal_move(new_position, board)

        return legality


@dc.dataclass
class Pawn(Piece):
    piece_type: PieceType = PieceType.PAWN

    def _is_legal_move(self, new_position, board: "Board"):
        if new_position in self.legal_moves:

            if board.get(new_position) is not None:
                direction = -1 if self.color == Color.WHITE else 1
                if (
                    board.get(new_position).color != self.color
                    and abs(new_position.x - self.position.x) == 1
                    and  new_position.y - self.position.y == direction
                ):
                    return [MoveState.CAPTURED, MoveState.MOVED]
                else:
                    return [MoveState.NOTALLOWED]
            return [MoveState.MOVED]
        return [MoveState.NOTALLOWED]

    def update_legal_moves(self, board: "Board"):
        moves = []
        direction = -1 if self.color == Color.WHITE else 1
        if board.get(Position(self.position.x, self.position.y + direction)) is None:
            moves.append(Position(self.position.x, self.position.y + direction))
            if (
                self.moved == 0
                and board.get(
                    Position(self.position.x, self.position.y + 2 * direction)
                )
                is None
            ):
                moves.append(Position(self.position.x, self.position.y + 2 * direction))
        if board.get(Position(self.position.x + 1, self.position.y + direction)):
            if board.get(Position(self.position.x + 1, self.position.y + direction)).color != self.color:
                moves.append(Position(self.position.x + 1, self.position.y + direction))
        if board.get(Position(self.position.x - 1, self.position.y + direction)):
            if board.get(Position(self.position.x - 1, self.position.y + direction)).color != self.color:

                moves.append(Position(self.position.x - 1, self.position.y + direction))
        self.legal_moves = moves


@dc.dataclass
class Rook(Piece):
    piece_type: PieceType = PieceType.ROOK

    def update_legal_moves(self, board: "Board"):
        moves = []
        for i in range(1, 8):
            if self.position.y + i < 8:
                if board.get(Position(self.position.x, self.position.y + i)) is None:
                    moves.append(Position(self.position.x, self.position.y + i))
                else:
                    if (
                        board.get(Position(self.position.x, self.position.y + i)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x, self.position.y + i))
                    break
        for i in range(1, 8):
            if self.position.y - i >= 0:
                if board.get(Position(self.position.x, self.position.y - i)) is None:
                    moves.append(Position(self.position.x, self.position.y - i))
                else:
                    if (
                        board.get(Position(self.position.x, self.position.y - i)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x + i < 8:
                if board.get(Position(self.position.x + i, self.position.y)) is None:
                    moves.append(Position(self.position.x + i, self.position.y))
                else:
                    if (
                        board.get(Position(self.position.x + i, self.position.y)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0:
                if board.get(Position(self.position.x - i, self.position.y)) is None:
                    moves.append(Position(self.position.x - i, self.position.y))
                else:
                    if (
                        board.get(Position(self.position.x - i, self.position.y)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y))
                    break
        self.legal_moves = moves


@dc.dataclass
class Bishop(Piece):
    piece_type: PieceType = PieceType.BISHOP

    def update_legal_moves(self, board: "Board"):
        moves = []
        for i in range(1, 8):
            if self.position.x + i < 8 and self.position.y + i < 8:
                if (
                    board.get(Position(self.position.x + i, self.position.y + i))
                    is None
                ):
                    moves.append(Position(self.position.x + i, self.position.y + i))
                else:
                    if (
                        board.get(
                            Position(self.position.x + i, self.position.y + i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y + i))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0 and self.position.y - i >= 0:
                if (
                    board.get(Position(self.position.x - i, self.position.y - i))
                    is None
                ):
                    moves.append(Position(self.position.x - i, self.position.y - i))
                else:
                    if (
                        board.get(
                            Position(self.position.x - i, self.position.y - i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x + i < 8 and self.position.y - i >= 0:
                if (
                    board.get(Position(self.position.x + i, self.position.y - i))
                    is None
                ):
                    moves.append(Position(self.position.x + i, self.position.y - i))
                else:
                    if (
                        board.get(
                            Position(self.position.x + i, self.position.y - i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0 and self.position.y + i < 8:
                if (
                    board.get(Position(self.position.x - i, self.position.y + i))
                    is None
                ):
                    moves.append(Position(self.position.x - i, self.position.y + i))
                else:
                    if (
                        board.get(
                            Position(self.position.x - i, self.position.y + i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y + i))
                    break
        self.legal_moves = moves


@dc.dataclass
class Knight(Piece):
    piece_type: PieceType = PieceType.KNIGHT

    def update_legal_moves(self, board: "Board"):
        moves = []
        for dx, dy in [
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (1, -2),
            (-1, 2),
            (-1, -2),
        ]:
            new_position = Position(self.position.x + dx, self.position.y + dy)
            if board.get(new_position) is None:
                moves.append(new_position)
            else:
                if (
                    isinstance(board.get(new_position), Piece)
                    and board.get(new_position).color != self.color
                ):
                    moves.append(new_position)
        self.legal_moves = moves


@dc.dataclass
class Queen(Piece):
    piece_type: PieceType = PieceType.QUEEN

    def update_legal_moves(self, board: "Board"):
        moves = []
        for i in range(1, 8):
            if self.position.y + i < 8:
                if board.get(Position(self.position.x, self.position.y + i)) is None:
                    moves.append(Position(self.position.x, self.position.y + i))
                else:
                    if (
                        board.get(Position(self.position.x, self.position.y + i)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x, self.position.y + i))
                    break
        for i in range(1, 8):
            if self.position.y - i >= 0:
                if board.get(Position(self.position.x, self.position.y - i)) is None:
                    moves.append(Position(self.position.x, self.position.y - i))
                else:
                    if (
                        board.get(Position(self.position.x, self.position.y - i)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x + i < 8:
                if board.get(Position(self.position.x + i, self.position.y)) is None:
                    moves.append(Position(self.position.x + i, self.position.y))
                else:
                    if (
                        board.get(Position(self.position.x + i, self.position.y)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0:
                if board.get(Position(self.position.x - i, self.position.y)) is None:
                    moves.append(Position(self.position.x - i, self.position.y))
                else:
                    if (
                        board.get(Position(self.position.x - i, self.position.y)).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y))
                    break
        for i in range(1, 8):
            if self.position.x + i < 8 and self.position.y + i < 8:
                if (
                    board.get(Position(self.position.x + i, self.position.y + i))
                    is None
                ):
                    moves.append(Position(self.position.x + i, self.position.y + i))
                else:
                    if (
                        board.get(
                            Position(self.position.x + i, self.position.y + i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y + i))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0 and self.position.y - i >= 0:
                if (
                    board.get(Position(self.position.x - i, self.position.y - i))
                    is None
                ):
                    moves.append(Position(self.position.x - i, self.position.y - i))
                else:
                    if (
                        board.get(
                            Position(self.position.x - i, self.position.y - i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x + i < 8 and self.position.y - i >= 0:
                if (
                    board.get(Position(self.position.x + i, self.position.y - i))
                    is None
                ):
                    moves.append(Position(self.position.x + i, self.position.y - i))
                else:
                    if (
                        board.get(
                            Position(self.position.x + i, self.position.y - i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x + i, self.position.y - i))
                    break
        for i in range(1, 8):
            if self.position.x - i >= 0 and self.position.y + i < 8:
                if (
                    board.get(Position(self.position.x - i, self.position.y + i))
                    is None
                ):
                    moves.append(Position(self.position.x - i, self.position.y + i))
                else:
                    if (
                        board.get(
                            Position(self.position.x - i, self.position.y + i)
                        ).color
                        != self.color
                    ):
                        moves.append(Position(self.position.x - i, self.position.y + i))
                    break
        self.legal_moves = moves


@dc.dataclass
class King(Piece):
    piece_type: PieceType = PieceType.KING

    def update_legal_moves(self, board: "Board"):
        moves = []
        for dx, dy in [
            (1, 0),
            (1, 1),
            (0, 1),
            (-1, 1),
            (-1, 0),
            (-1, -1),
            (0, -1),
            (1, -1),
        ]:
            new_position = Position(self.position.x + dx, self.position.y + dy)
            if board.get(new_position) is None:
                moves.append(new_position)
            else:
                if (
                    isinstance(board.get(new_position), Piece)
                    and board.get(new_position).color != self.color
                ):
                    moves.append(new_position)
        self.legal_moves = moves
