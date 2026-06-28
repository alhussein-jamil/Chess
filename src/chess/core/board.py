import dataclasses as dc
from typing import Any

import pygame

from chess.core.types import (
    DIM_X as dim_x,
)
from chess.core.types import (
    DIM_Y as dim_y,
)
from chess.core.types import (
    LEGAL,
    SQUARE_SIZE,
    Color,
    Ending,
    MoveState,
    PieceType,
)
from chess.layout import BOARD_INSET
from chess.ui.render import render_board

from .piece import (
    Bishop,
    King,
    Knight,
    NullPiece,
    OffBoard,
    Pawn,
    Piece,
    Position,
    Queen,
    Rook,
)

_PIECE_CLASSES = {
    PieceType.PAWN: Pawn,
    PieceType.ROOK: Rook,
    PieceType.KNIGHT: Knight,
    PieceType.BISHOP: Bishop,
    PieceType.QUEEN: Queen,
    PieceType.KING: King,
}


@dc.dataclass
class Board:
    danger_level: dict[Position, int] = dc.field(default_factory=dict)
    pieces: dict[Color, list[Piece]] = dc.field(default_factory=dict)
    dragged_piece: Piece | None = None
    drag_origin: Position | None = None
    checks: dict[Color, bool] = dc.field(default_factory=dict)
    checkmates: dict[Color, Ending] = dc.field(default_factory=dict)
    turn: Color = Color.WHITE
    promotion: PieceType = PieceType.KNIGHT
    moves_without_capture: int = 0
    board: dict[Position, Piece] = dc.field(default_factory=dict)
    kings: dict[Color, King] = dc.field(default_factory=dict)
    last_move: tuple[Position, Position] | None = None

    def __post_init__(self):
        self.checks = {Color.WHITE: False, Color.BLACK: False}
        self.checkmates = {Color.WHITE: Ending.ONGOING, Color.BLACK: Ending.ONGOING}
        self.board = {Position(x, y): NullPiece() for x in range(dim_x) for y in range(dim_y)}
        self.pieces = {Color.WHITE: [], Color.BLACK: []}

    @classmethod
    def from_pieces(cls, pieces: list[Piece], *args, **kwargs) -> "Board":
        board = cls(*args, **kwargs)
        for piece in pieces:
            cls.add_piece(board, piece)
        return board

    @staticmethod
    def add_piece(board: "Board", piece: Piece):
        if piece.color not in board.pieces:
            board.pieces[piece.color] = []
        board.pieces[piece.color].append(piece)
        piece.created = True
        board.board[piece.position] = piece

    def get(self, position: Position) -> Piece:
        if not self.in_bounds(position):
            return OffBoard()
        return self.board[position]

    def promote_to(self, piece: Piece) -> Piece:
        match self.promotion:
            case PieceType.QUEEN:
                return Queen(color=piece.color, position=piece.position)
            case PieceType.ROOK:
                return Rook(color=piece.color, position=piece.position)
            case PieceType.BISHOP:
                return Bishop(color=piece.color, position=piece.position)
            case PieceType.KNIGHT:
                return Knight(color=piece.color, position=piece.position)
            case _:
                return piece

    def copy_for_search(self) -> "Board":
        trial = Board(
            turn=self.turn,
            promotion=self.promotion,
            moves_without_capture=self.moves_without_capture,
        )
        trial.checks = {
            Color.WHITE: self.checks[Color.WHITE],
            Color.BLACK: self.checks[Color.BLACK],
        }
        trial.checkmates = {
            Color.WHITE: self.checkmates[Color.WHITE],
            Color.BLACK: self.checkmates[Color.BLACK],
        }
        trial.pieces = {
            Color.WHITE: [self._clone_piece(piece) for piece in self.pieces[Color.WHITE]],
            Color.BLACK: [self._clone_piece(piece) for piece in self.pieces[Color.BLACK]],
        }
        trial._sync_grid_from_pieces()
        return trial

    def copy_ai(self) -> "Board":
        return self.copy_for_search()

    @staticmethod
    def _clone_piece(piece: Piece) -> Piece:
        cls = type(piece)
        cloned = cls(
            color=piece.color,
            position=Position(piece.position.x, piece.position.y),
        )
        cloned.moved = piece.moved
        cloned.created = piece.created
        cloned.legal_moves = list(piece.legal_moves)
        cloned.attacking_squares = list(piece.attacking_squares)
        return cloned

    def _sync_grid_from_pieces(self) -> None:
        self.board = {Position(x, y): NullPiece() for x in range(dim_x) for y in range(dim_y)}
        self.kings = {}
        for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]:
            self.board[piece.position] = piece
            if isinstance(piece, King):
                self.kings[piece.color] = piece

    def to_search_state(self) -> tuple[Any, ...]:
        rows = tuple(
            (
                piece.color.value,
                piece.piece_type.value,
                piece.position.x,
                piece.position.y,
                piece.moved,
            )
            for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]
        )
        return (self.turn.value, self.promotion.value, self.moves_without_capture, rows)

    @classmethod
    def from_search_state(cls, state: tuple[Any, ...]) -> "Board":
        turn_val, promotion_val, moves_without_capture, piece_rows = state
        board = cls(
            turn=Color(turn_val),
            promotion=PieceType(promotion_val),
            moves_without_capture=moves_without_capture,
        )
        white: list[Piece] = []
        black: list[Piece] = []
        for color_val, type_val, x, y, moved in piece_rows:
            piece_cls = _PIECE_CLASSES[PieceType(type_val)]
            piece = piece_cls(color=Color(color_val), position=Position(x, y))
            piece.moved = moved
            piece.created = True
            (white if piece.color == Color.WHITE else black).append(piece)
        board.pieces = {Color.WHITE: white, Color.BLACK: black}
        board._sync_grid_from_pieces()
        board.update()
        return board

    def can_castle_to(self, king: King, new_position: Position) -> bool:
        if (
            king.piece_type != PieceType.KING
            or king.moved != 0
            or abs(king.position.x - new_position.x) != 2
        ):
            return False

        direction = 1 if new_position.x > king.position.x else -1
        n_squares = 3 if direction == 1 else 4
        rook_position = Position(7 if direction == 1 else 0, new_position.y)
        rook = self.get(rook_position)
        if isinstance(rook, NullPiece) or rook.piece_type != PieceType.ROOK or rook.moved != 0:
            return False

        empty_squares = all(
            isinstance(
                self.get(Position(king.position.x + step * direction, king.position.y)),
                NullPiece,
            )
            for step in range(1, n_squares)
        )
        if not empty_squares:
            return False

        opponent_color = Color.WHITE if king.color == Color.BLACK else Color.BLACK
        for step in range(1, n_squares):
            square = Position(king.position.x + step * direction, king.position.y)
            for piece in self.pieces[opponent_color]:
                if square in piece.legal_moves:
                    return False
        return True

    @staticmethod
    def in_bounds(position: Position) -> bool:
        return 0 <= position.x < dim_x and 0 <= position.y < dim_y

    def update(self):
        self._update_board()
        self._update_pieces()
        self._update_checks()

    def _update_board(self):
        self.board = {position: NullPiece() for position in self.board}
        for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]:
            self.board[piece.position] = piece

    def _update_pieces(self):
        self.danger_level = {}
        for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]:
            self._update_piece(piece)

    def _update_piece(self, piece: Piece):
        if isinstance(piece, King):
            self.kings[piece.color] = piece
        piece.update_legal_moves(self)
        for position in piece.attacking_squares:
            if self.in_bounds(position):
                self.danger_level[position] = self.danger_level.get(position, 0) + (
                    1 if piece.color == Color.WHITE else -1
                )

    def _update_checks(self):
        self.checks = {Color.WHITE: False, Color.BLACK: False}
        # check if the kings are in check
        for color, king in self.kings.items():
            if king is not None:
                opposite_color = Color.WHITE if color == Color.BLACK else Color.BLACK
                opposite_color_pieces = self.pieces[opposite_color]
                for piece in opposite_color_pieces:
                    if king.position in piece.attacking_squares:
                        self.checks[color] = True
                        break
                else:
                    self.checks[color] = False

    def move_piece(
        self, piece: Piece, new_position: Position, *, update_result: bool = True
    ) -> tuple[bool, int]:
        return_value = False
        capture_value = 0
        origin = Position(piece.position.x, piece.position.y)
        if self.in_bounds(new_position):
            move_state = piece.move(new_position, self)
            return_value = self.handle_castling(piece, new_position)

            if not return_value and any(state in move_state for state in LEGAL):
                return_value, capture_value = self.try_move(piece, new_position)

            # Handle Dragging new piece
            if MoveState.CREATED in move_state:
                self.pieces[piece.color].append(piece)

            # Handle promotion
            self.handle_promotion(piece)
            self.update()
            return_value = return_value and not self.checks[piece.color]

            if return_value:
                if update_result:
                    self.last_move = (origin, Position(new_position.x, new_position.y))
                opposite_color = Color.WHITE if piece.color == Color.BLACK else Color.BLACK
                self.turn = opposite_color
                if update_result:
                    self.checkmates[opposite_color] = self.check_end(opposite_color)

        return return_value, capture_value

    def _undo_move(self, piece, old_position, backup_piece):
        piece.position = old_position
        piece.moved -= 1
        if (
            not isinstance(backup_piece, NullPiece)
            and backup_piece not in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]
        ):
            self.pieces[backup_piece.color].append(backup_piece)

    def try_move(self, piece: Piece, new_position: Position, move: bool = True):
        # Move the piece to the new position
        old_position = Position(piece.position.x, piece.position.y)
        piece.position = new_position
        piece.moved += 1

        backup_piece = self.board[new_position]
        capture_value = 0
        if backup_piece in self.pieces[Color.WHITE]:
            self.pieces[Color.WHITE].remove(backup_piece)
        elif backup_piece in self.pieces[Color.BLACK]:
            self.pieces[Color.BLACK].remove(backup_piece)
        self.update()
        return_value = True
        if move:
            if self.checks[piece.color]:
                self._undo_move(piece, old_position, backup_piece)
                return_value = False
            else:
                self.moves_without_capture += 1
                if not isinstance(backup_piece, NullPiece):
                    self.moves_without_capture = 0
                    capture_value += backup_piece.value
        else:
            self._undo_move(piece, old_position, backup_piece)
            return_value = not self.checks[piece.color]
        self.update()
        return return_value, capture_value

    @staticmethod
    def mouse_to_grid(mouse_pos: tuple[int, int], square_size: int) -> Position:
        return Position(
            (mouse_pos[0] - BOARD_INSET) // square_size,
            (mouse_pos[1] - BOARD_INSET) // square_size,
        )

    def _restore_dragged_piece(self) -> None:
        if self.dragged_piece is None or self.drag_origin is None:
            return
        origin = self.drag_origin
        self.dragged_piece.position = Position(origin.x, origin.y)
        self.board[origin] = self.dragged_piece
        self.dragged_piece = None
        self.drag_origin = None

    def is_legal_target(self, piece: Piece, target: Position, origin: Position) -> bool:
        if not self.in_bounds(target):
            return False

        if isinstance(piece, King) and target.y == origin.y and abs(target.x - origin.x) == 2:
            return self.can_castle_to(piece, target)

        if target not in piece.legal_moves:
            return False
        ok, _ = self.try_move(piece, target, move=False)
        return ok

    def handle_event(self, event, square_size: int = SQUARE_SIZE) -> bool:
        """Handle mouse input. Returns True if a legal move was played."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_position = self.mouse_to_grid(pygame.mouse.get_pos(), square_size)
            if not self.in_bounds(mouse_position):
                return False
            piece = self.board[mouse_position]
            if not isinstance(piece, NullPiece) and piece.color == self.turn:
                self.drag_origin = Position(mouse_position.x, mouse_position.y)
                self.dragged_piece = piece
                self.board[mouse_position] = NullPiece()
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_piece is None or self.drag_origin is None:
                return False

            piece = self.dragged_piece
            origin = self.drag_origin
            target = self.mouse_to_grid(pygame.mouse.get_pos(), square_size)
            moved = False

            if self.is_legal_target(piece, target, origin):
                moved, _ = self.move_piece(piece, target)
                if not moved:
                    self._restore_dragged_piece()
            else:
                self._restore_dragged_piece()

            if moved:
                self.dragged_piece = None
                self.drag_origin = None
            self.update()
            return moved

        return False

    def handle_promotion(self, piece: Piece):
        if piece.piece_type == PieceType.PAWN and (
            (piece.position.y == 0 and piece.color == Color.WHITE)
            or (piece.position.y == 7 and piece.color == Color.BLACK)
        ):
            if piece in self.pieces[Color.WHITE]:
                self.pieces[Color.WHITE].remove(piece)
            else:
                self.pieces[Color.BLACK].remove(piece)
            self.add_piece(self, self.promote_to(piece))

    def handle_castling(self, king: Piece, new_position: Position):
        # Check if the move is a castling move
        if (
            king.piece_type == PieceType.KING
            and king.moved == 0
            and abs(king.position.x - new_position.x) == 2
        ):
            # Determine direction of castling (short or long)
            direction = 1 if new_position.x > king.position.x else -1
            n_squares = 3 if direction == 1 else 4
            # Get the rook position
            rook_position = Position(7 if direction == 1 else 0, new_position.y)
            rook = self.get(rook_position)
            # Check if the rook is present and hasn't moved
            if rook is not NullPiece() and rook.piece_type == PieceType.ROOK and rook.moved == 0:
                # Check if squares between king and rook are empty
                empty_squares = all(
                    isinstance(
                        self.get(Position(king.position.x + i * direction, king.position.y)),
                        NullPiece,
                    )
                    for i in range(1, n_squares)
                )
                opponent_color = Color.WHITE if king.color == Color.BLACK else Color.BLACK
                # Check if squares between king and rook are controlled by the opponent
                squares_between_ = [
                    Position(king.position.x + i * direction, king.position.y)
                    for i in range(1, n_squares)
                ]
                controlled_squares = False
                # check that no piece is attacking the squares between the king and the rook
                for position in squares_between_:
                    opposite_color_pieces = self.pieces[opponent_color]
                    for piece in opposite_color_pieces:
                        if position in piece.legal_moves:
                            controlled_squares = True
                            break
                # Check if castling move is legal
                if empty_squares and not controlled_squares:
                    origin = Position(king.position.x, king.position.y)
                    self.try_move(king, new_position)
                    self.try_move(rook, Position(king.position.x - direction, king.position.y))
                    self.last_move = (origin, Position(new_position.x, new_position.y))
                    return True
        return False

    def check_material_insufficient(self):
        all_pieces = self.pieces[Color.WHITE] + self.pieces[Color.BLACK]
        # Check if there is insufficient material for checkmate
        if len(all_pieces) == 2:
            return True
        elif len(all_pieces) == 3:
            # Check if the remaining pieces are knights or bishops
            piece_types = [
                piece.piece_type for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]
            ]
            return all(
                piece_type in [PieceType.KNIGHT, PieceType.BISHOP] for piece_type in piece_types
            )
        elif len(all_pieces) == 4:
            # Check for specific scenarios where the combination of pieces
            # could lead to a draw due to insufficient material for checkmate
            piece_types = [piece.piece_type for piece in all_pieces]
            # If the remaining pieces are two bishops of opposite colors
            if piece_types.count(PieceType.BISHOP) == 2:
                piece_colors = [
                    piece.color for piece in all_pieces if piece.piece_type == PieceType.BISHOP
                ]
                if piece_colors[0] != piece_colors[1]:
                    return True
            # If the remaining pieces are a bishop and a knight
            if PieceType.BISHOP in piece_types and PieceType.KNIGHT in piece_types:
                return True
        return False

    def check_end(self, color: Color):
        if self.moves_without_capture >= 80:
            return Ending.DRAW

        if self.check_material_insufficient():
            return Ending.DRAW

        color_pieces = self.pieces[color]
        for piece in color_pieces:
            for new_position in piece.legal_moves:
                trying, _ = self.try_move(piece, new_position, False)
                if trying:
                    return Ending.ONGOING
        if self.checks[color]:
            return Ending.CHECKMATE
        return Ending.STALEMATE

    def draw(self, screen: pygame.Surface, square_size: int = SQUARE_SIZE) -> None:
        render_board(screen, self, square_size)
