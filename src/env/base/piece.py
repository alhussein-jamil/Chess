import dataclasses as dc
from pathlib import Path
from typing import TYPE_CHECKING, List
from ...globals import MoveState, Color, PieceType

if TYPE_CHECKING:
    from .board import Board


@dc.dataclass
class Position:
    x: int
    y: int

    def move(self, x, y):
        self.x += x
        self.y += y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __repr__(self):
        # x represented by letters and y represented by numbers
        return f"{chr(97 + self.x)}{8 - self.y}"

    @classmethod
    def from_repr(cls, repr):
        return Position(ord(repr[0]) - 97, 8 - int(repr[1]))


# a decorator for cleaning legal moves
def update_attacking_squares(func):
    def wrapper(*args, **kwargs):
        piece = args[0]
        result = func(
            *args, **kwargs
        )  # Call the original function and store its result
        piece.attacking_squares = [
            pos for pos in piece.legal_moves if isinstance(pos, Position)
        ]
        return result  # Return the result of the original function call

    return wrapper


@dc.dataclass
class Piece:
    color: Color = Color.WHITE
    piece_type: PieceType = PieceType.UNDEFINED
    position: Position = Position(4, 4)
    name: str = "Piece"
    icon_path: Path = Path.cwd()
    moved: int = 0
    created: bool = False
    legal_moves: List = dc.field(default_factory=list)
    attacking_squares: List = dc.field(default_factory=list)
    max_n_legal_moves: int = 0
    value: int = 0

    def __post_init__(self):
        self.icon_path = Path(
            f"assets/{self.piece_type.name.lower()}_{self.color.name.lower()}.png"
        )

    def __str__(self):
        return f"{self.color.name} {self.piece_type.name} at {self.position}"

    def _is_legal_move(self, new_position, board: "Board"):
        if new_position in self.legal_moves:
            if not isinstance(board.get(new_position), NullPiece):
                if board.get(new_position).color != self.color:
                    return [MoveState.CAPTURED]
                else:
                    return [MoveState.OCCUPIED]
            return [MoveState.CAPTURED, MoveState.MOVED]
        return [MoveState.NOTALLOWED]

    @update_attacking_squares
    def update_legal_moves(self, board: "Board"):
        pass

    def move(self, new_position, board: "Board"):
        if self.created is False:
            self.position = new_position
            self.created = True
            return [MoveState.CREATED]

        legality = self._is_legal_move(new_position, board)

        if isinstance(board.board[new_position], King):
            legality = [MoveState.NOTALLOWED]

        return legality


@dc.dataclass
class NullPiece(Piece):
    piece_type: PieceType = PieceType.UNDEFINED
    value: int = 0
    max_n_legal_moves: int = 0
    color: Color = Color.UNDEFINED

    def update_legal_moves(self, board: "Board"):
        self.legal_moves = []
        self.attacking_squares = []


@dc.dataclass
class OffBoard(NullPiece):
    piece_type: PieceType = PieceType.UNDEFINED
    value: int = 0
    max_n_legal_moves: int = 0

    def update_legal_moves(self, board: "Board"):
        self.legal_moves = []
        self.attacking_squares = []


@dc.dataclass
class Pawn(Piece):
    piece_type: PieceType = PieceType.PAWN
    value: int = 1
    max_n_legal_moves: int = 4

    def _is_legal_move(self, new_position, board: "Board"):
        direction = -1 if self.color == Color.WHITE else 1
        capture_condition = (
            board.get(new_position).color != self.color
            and abs(new_position.x - self.position.x) == 1
            and new_position.y - self.position.y == direction
        )
        if new_position in self.legal_moves:
            if not isinstance(board.get(new_position), NullPiece):
                if capture_condition:
                    return [MoveState.CAPTURED, MoveState.MOVED]
                else:
                    return [MoveState.NOTALLOWED]
            elif new_position.x == self.position.x:
                return [MoveState.MOVED]
        return [MoveState.NOTALLOWED]

    def update_legal_moves(self, board: "Board"):
        moves = []
        attacking_squares = []
        direction = -1 if self.color == Color.WHITE else 1
        if isinstance(
            board.get(Position(self.position.x, self.position.y + direction)), NullPiece
        ):
            moves.append(Position(self.position.x, self.position.y + direction))
            if self.moved == 0 and isinstance(
                board.get(Position(self.position.x, self.position.y + 2 * direction)),
                NullPiece,
            ):
                moves.append(Position(self.position.x, self.position.y + 2 * direction))

        for i in [1, -1]:
            if not isinstance(
                board.get(Position(self.position.x - i, self.position.y + direction)),
                NullPiece,
            ):
                if (
                    board.get(
                        Position(self.position.x - i, self.position.y + direction)
                    ).color
                    != self.color
                ):
                    moves.append(
                        Position(self.position.x - i, self.position.y + direction)
                    )
            attacking_squares.append(
                Position(self.position.x - i, self.position.y + direction)
            )

        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]

        self.attacking_squares = attacking_squares


@dc.dataclass
class Rook(Piece):
    piece_type: PieceType = PieceType.ROOK
    value: int = 5
    max_n_legal_moves: int = 14

    @update_attacking_squares
    def update_legal_moves(self, board: "Board"):
        moves = []

        def check_displacement(x_dis, y_dis):
            new_position = Position(self.position.x + x_dis, self.position.y + y_dis)
            if (
                new_position.x < 8
                and new_position.x >= 0
                and new_position.y < 8
                and new_position.y >= 0
            ):
                if isinstance(board.get(new_position), NullPiece):
                    moves.append(new_position)
                    return False
                else:
                    if board.get(new_position).color != self.color:
                        moves.append(new_position)
                        return True

            return True

        for x_dis in range(1, 8):
            if check_displacement(x_dis, 0):
                break
        for x_dis in range(-1, -8, -1):
            if check_displacement(x_dis, 0):
                break
        for y_dis in range(1, 8):
            if check_displacement(0, y_dis):
                break
        for y_dis in range(-1, -8, -1):
            if check_displacement(0, y_dis):
                break
        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]


@dc.dataclass
class Bishop(Piece):
    piece_type: PieceType = PieceType.BISHOP
    value: int = 3
    max_n_legal_moves: int = 13

    @update_attacking_squares
    def update_legal_moves(self, board: "Board"):
        moves = []
        for i in range(1, 8):
            if self.position.x + i < 8 and self.position.y + i < 8:
                if isinstance(
                    board.get(Position(self.position.x + i, self.position.y + i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x - i, self.position.y - i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x + i, self.position.y - i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x - i, self.position.y + i)),
                    NullPiece,
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
        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]


@dc.dataclass
class Knight(Piece):
    piece_type: PieceType = PieceType.KNIGHT
    value: int = 3
    max_n_legal_moves: int = 8

    @update_attacking_squares
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
            if isinstance(board.get(new_position), NullPiece):
                moves.append(new_position)
            else:
                if (
                    isinstance(board.get(new_position), Piece)
                    and board.get(new_position).color != self.color
                ):
                    moves.append(new_position)
        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]


@dc.dataclass
class Queen(Piece):
    piece_type: PieceType = PieceType.QUEEN
    value: int = 9
    max_n_legal_moves: int = 27

    @update_attacking_squares
    def update_legal_moves(self, board: "Board"):
        moves = []
        for i in range(1, 8):
            if self.position.y + i < 8:
                if isinstance(
                    board.get(Position(self.position.x, self.position.y + i)), NullPiece
                ):
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
                if isinstance(
                    board.get(Position(self.position.x, self.position.y - i)), NullPiece
                ):
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
                if isinstance(
                    board.get(Position(self.position.x + i, self.position.y)), NullPiece
                ):
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
                if isinstance(
                    board.get(Position(self.position.x - i, self.position.y)), NullPiece
                ):
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
                if isinstance(
                    board.get(Position(self.position.x + i, self.position.y + i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x - i, self.position.y - i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x + i, self.position.y - i)),
                    NullPiece,
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
                if isinstance(
                    board.get(Position(self.position.x - i, self.position.y + i)),
                    NullPiece,
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
        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]


@dc.dataclass
class King(Piece):
    piece_type: PieceType = PieceType.KING
    value: int = 100
    max_n_legal_moves: int = 8

    @update_attacking_squares
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
            if isinstance(board.get(new_position), NullPiece):
                moves.append(new_position)
            else:
                if (
                    isinstance(board.get(new_position), Piece)
                    and board.get(new_position).color != self.color
                ):
                    moves.append(new_position)
        self.legal_moves = [
            move for move in moves if not isinstance(board.get(move), OffBoard)
        ]


STARTING_PIECES = [
    Rook(color=Color.BLACK, position=Position(0, 0)),
    Knight(color=Color.BLACK, position=Position(1, 0)),
    Bishop(color=Color.BLACK, position=Position(2, 0)),
    Queen(color=Color.BLACK, position=Position(3, 0)),
    King(color=Color.BLACK, position=Position(4, 0)),
    Bishop(color=Color.BLACK, position=Position(5, 0)),
    Knight(color=Color.BLACK, position=Position(6, 0)),
    Rook(color=Color.BLACK, position=Position(7, 0)),
    Pawn(color=Color.BLACK, position=Position(0, 1)),
    Pawn(color=Color.BLACK, position=Position(1, 1)),
    Pawn(color=Color.BLACK, position=Position(2, 1)),
    Pawn(color=Color.BLACK, position=Position(3, 1)),
    Pawn(color=Color.BLACK, position=Position(4, 1)),
    Pawn(color=Color.BLACK, position=Position(5, 1)),
    Pawn(color=Color.BLACK, position=Position(6, 1)),
    Pawn(color=Color.BLACK, position=Position(7, 1)),
    Rook(color=Color.WHITE, position=Position(0, 7)),
    Knight(color=Color.WHITE, position=Position(1, 7)),
    Bishop(color=Color.WHITE, position=Position(2, 7)),
    Queen(color=Color.WHITE, position=Position(3, 7)),
    King(color=Color.WHITE, position=Position(4, 7)),
    Bishop(color=Color.WHITE, position=Position(5, 7)),
    Knight(color=Color.WHITE, position=Position(6, 7)),
    Rook(color=Color.WHITE, position=Position(7, 7)),
    Pawn(color=Color.WHITE, position=Position(0, 6)),
    Pawn(color=Color.WHITE, position=Position(1, 6)),
    Pawn(color=Color.WHITE, position=Position(2, 6)),
    Pawn(color=Color.WHITE, position=Position(3, 6)),
    Pawn(color=Color.WHITE, position=Position(4, 6)),
    Pawn(color=Color.WHITE, position=Position(5, 6)),
    Pawn(color=Color.WHITE, position=Position(6, 6)),
    Pawn(color=Color.WHITE, position=Position(7, 6)),
]
