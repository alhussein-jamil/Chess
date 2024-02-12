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

    def __post_init__(self):
        try: 
            self.icon = pygame.image.load(
                Path(f"assets/{self.piece_type.name.lower()}_{self.color.name.lower()}.png")
            ).convert_alpha()

        except: 
           pass
    def _is_legal_move(self, *args, **kwargs) -> List[MoveState]:
        return [MoveState.MOVED]

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
        states = []
        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y
        direction = -1 if self.color == Color.WHITE else 1

        if dy == direction and dx == 0 and board.get(new_position) is None:
            states.append(MoveState.MOVED)
        elif (
            dy == 2 * direction
            and dx == 0
            and self.moved == 0
            and board.get(Position(self.position.x, self.position.y + direction)) is None
            and board.get(new_position) is None
        ):
            states.append(MoveState.MOVED)
        elif abs(dx) == 1 and dy == direction:
            piece = board.get(new_position)
            if piece and piece.color != self.color:
                states.append(MoveState.CAPTURED)

        return states or [MoveState.NOTALLOWED]


@dc.dataclass
class Rook(Piece):
    piece_type: PieceType = PieceType.ROOK

    def _is_legal_move(self, new_position, board: "Board"):
        states = []
        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y

        if dx == 0:  # Vertical move
            step = 1 if dy > 0 else -1
            for i in range(1, abs(dy)):
                if board.get(Position(self.position.x, self.position.y + i * step)):
                    states.append(MoveState.NOTALLOWED)
                    return states

        elif dy == 0:  # Horizontal move
            step = 1 if dx > 0 else -1
            for i in range(1, abs(dx)):
                if board.get(Position(self.position.x + i * step, self.position.y)):
                    states.append(MoveState.NOTALLOWED)
                    return states
        else:
            states.append(MoveState.NOTALLOWED)
            return states
        piece = board.get(new_position)
        if piece:
            if piece.color != self.color:
                states.append(MoveState.CAPTURED)
            else:
                states.append(MoveState.NOTALLOWED)

        return states or [MoveState.MOVED]


@dc.dataclass
class Bishop(Piece):
    piece_type: PieceType = PieceType.BISHOP

    def _is_legal_move(self, new_position, board: "Board"):
        states = []
        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y

        if abs(dx) == abs(dy):
            step_x = 1 if dx > 0 else -1
            step_y = 1 if dy > 0 else -1
            for i in range(1, abs(dx)):
                if board.get(
                    Position(self.position.x + i * step_x, self.position.y + i * step_y)
                ):
                    states.append(MoveState.NOTALLOWED)
                    return states
        else:
            states.append(MoveState.NOTALLOWED)
            return states
        piece = board.get(new_position)
        if piece:
            if piece.color != self.color:
                states.append(MoveState.CAPTURED)
            else:
                states.append(MoveState.NOTALLOWED)

        return states or [MoveState.MOVED]


@dc.dataclass
class Knight(Piece):
    piece_type: PieceType = PieceType.KNIGHT

    def _is_legal_move(self, new_position, board: "Board"):
        states = []
        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y

        if abs(dx * dy) == 2:
            piece = board.get(new_position)
            if piece:
                if piece.color != self.color:
                    states.append(MoveState.CAPTURED)
                else:
                    states.append(MoveState.NOTALLOWED)
            else:
                states.append(MoveState.MOVED)
        else:
            states.append(MoveState.NOTALLOWED)

        return states or [MoveState.NOTALLOWED]


@dc.dataclass
class Queen(Piece):
    piece_type: PieceType = PieceType.QUEEN

    def _is_legal_move(self, new_position, board: "Board"):
        states = []
        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y

        if dx == 0:
            step = 1 if dy > 0 else -1
            for i in range(1, abs(dy)):
                if board.get(Position(self.position.x, self.position.y + i * step)):
                    states.append(MoveState.NOTALLOWED)
                    return states
        elif dy == 0:
            step = 1 if dx > 0 else -1
            for i in range(1, abs(dx)):
                if board.get(Position(self.position.x + i * step, self.position.y)):
                    states.append(MoveState.NOTALLOWED)
                    return states
        elif abs(dx) == abs(dy):
            step_x = 1 if dx > 0 else -1
            step_y = 1 if dy > 0 else -1
            for i in range(1, abs(dx)):
                if board.get(
                    Position(self.position.x + i * step_x, self.position.y + i * step_y)
                ):
                    states.append(MoveState.NOTALLOWED)
                    return states
        else:
            states.append(MoveState.NOTALLOWED)
            return states
        piece = board.get(new_position)
        if piece:
            if piece.color != self.color:
                states.append(MoveState.CAPTURED)
            else:
                states.append(MoveState.NOTALLOWED)

        return states or [MoveState.MOVED]


@dc.dataclass
class King(Piece):
    piece_type: PieceType = PieceType.KING

    def _is_legal_move(self, new_position, board: "Board"):
        states = []

        dx = new_position.x - self.position.x
        dy = new_position.y - self.position.y

        if abs(dx) <= 1 and abs(dy) <= 1:
            piece = board.get(new_position)
            if piece:
                if piece.color != self.color:
                    states.append(MoveState.CAPTURED)
                else:
                    states.append(MoveState.NOTALLOWED)
            else:
                states.append(MoveState.MOVED)
        else:
            states.append(MoveState.NOTALLOWED)

        return states or [MoveState.NOTALLOWED]
