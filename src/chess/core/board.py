import dataclasses as dc
from typing import Any

import pygame

from chess.core.board_state import KING as STATE_KING
from chess.core.board_state import PAWN as STATE_PAWN
from chess.core.board_state import PIECE_VALUES, BoardState
from chess.core.types import (
    DIM_X as dim_x,
)
from chess.core.types import (
    DIM_Y as dim_y,
)
from chess.core.types import (
    SQUARE_SIZE,
    Color,
    Ending,
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
    _state: BoardState | None = dc.field(default=None, repr=False, compare=False)

    def invalidate_state(self) -> None:
        self._state = None

    @property
    def state(self) -> BoardState:
        if self._state is None:
            self._state = BoardState.from_board(self)
        return self._state

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
        board.invalidate_state()

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
        board.invalidate_state()
        board.update()
        return board

    @staticmethod
    def in_bounds(position: Position) -> bool:
        return 0 <= position.x < dim_x and 0 <= position.y < dim_y

    def update(self) -> None:
        self._sync_grid_from_pieces()
        self._sync_checks_from_state()

    def _find_piece_at(self, x: int, y: int) -> Piece | None:
        target = Position(x, y)
        for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]:
            if piece.position == target:
                return piece
        return None

    def _sync_pieces_from_undo(self, undo) -> int:
        moved = undo.moved_piece
        sign = 1 if moved > 0 else -1
        color = Color.WHITE if sign > 0 else Color.BLACK

        piece = self._find_piece_at(undo.fx, undo.fy)
        if piece is None:
            return 0

        capture_value = 0
        if undo.captured:
            captured = self._find_piece_at(undo.tx, undo.ty)
            if captured is not None:
                self.pieces[captured.color].remove(captured)
                capture_value = PIECE_VALUES.get(abs(undo.captured), 0)

        piece.position = Position(undo.tx, undo.ty)
        piece.moved += 1

        promo_rank = 0 if sign > 0 else 7
        if abs(moved) == STATE_PAWN and undo.ty == promo_rank:
            self.pieces[color].remove(piece)
            promoted = self.promote_to(piece)
            promoted.moved = piece.moved
            promoted.created = True
            self.pieces[color].append(promoted)

        if abs(moved) == STATE_KING and abs(undo.tx - undo.fx) == 2:
            direction = 1 if undo.tx > undo.fx else -1
            rook_from_x = 7 if direction == 1 else 0
            rook_to_x = undo.tx - direction
            rook = self._find_piece_at(rook_from_x, undo.fy)
            if rook is not None:
                rook.position = Position(rook_to_x, undo.fy)
                rook.moved += 1

        return capture_value

    def _sync_checks_from_state(self) -> None:
        snapshot = self.state
        self.checks = {
            Color.WHITE: snapshot.in_check(0),
            Color.BLACK: snapshot.in_check(1),
        }

    def move_piece(
        self, piece: Piece, new_position: Position, *, update_result: bool = True
    ) -> tuple[bool, int]:
        origin = Position(piece.position.x, piece.position.y)
        if not self.in_bounds(new_position):
            return False, 0

        if isinstance(piece, King) and abs(new_position.x - origin.x) == 2:
            if not self.handle_castling(piece, new_position):
                return False, 0
            if update_result:
                opposite = Color.WHITE if piece.color == Color.BLACK else Color.BLACK
                self.checkmates[opposite] = self.check_end(opposite)
            return True, 0

        ok, capture_value = self.try_move(piece, new_position, move=True)
        if ok and update_result:
            self.last_move = (origin, Position(new_position.x, new_position.y))
            opposite = Color.WHITE if piece.color == Color.BLACK else Color.BLACK
            self.checkmates[opposite] = self.check_end(opposite)
        return ok, capture_value

    def try_move(self, piece: Piece, new_position: Position, move: bool = True):
        fx, fy = piece.position.x, piece.position.y
        tx, ty = new_position.x, new_position.y
        if not move:
            return self.state.would_be_legal(fx, fy, tx, ty), 0

        if not self.state.make_move(fx, fy, tx, ty):
            return False, 0

        undo = self.state.peek_undo()
        capture_value = self._sync_pieces_from_undo(undo) if undo is not None else 0
        self.turn = Color.BLACK if self.state.turn == 1 else Color.WHITE
        self.moves_without_capture = self.state.halfmove
        self._sync_grid_from_pieces()
        self._sync_checks_from_state()
        return True, capture_value

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
        self.invalidate_state()

    def is_legal_target(self, piece: Piece, target: Position, origin: Position) -> bool:
        if not self.in_bounds(target):
            return False
        return self.state.would_be_legal(origin.x, origin.y, target.x, target.y)

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
                self.invalidate_state()
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

    def handle_castling(self, king: Piece, new_position: Position):
        if (
            king.piece_type != PieceType.KING
            or king.moved != 0
            or abs(king.position.x - new_position.x) != 2
        ):
            return False

        origin = Position(king.position.x, king.position.y)
        if not self.state.would_be_legal(origin.x, origin.y, new_position.x, new_position.y):
            return False

        if not self.state.make_move(origin.x, origin.y, new_position.x, new_position.y):
            return False

        undo = self.state.peek_undo()
        if undo is not None:
            self._sync_pieces_from_undo(undo)
        self.turn = Color.BLACK if self.state.turn == 1 else Color.WHITE
        self.moves_without_capture = self.state.halfmove
        self._sync_grid_from_pieces()
        self._sync_checks_from_state()
        self.last_move = (origin, Position(new_position.x, new_position.y))
        return True

    def check_end(self, color: Color):
        if self.moves_without_capture >= 80:
            return Ending.DRAW

        if self.state.insufficient_material():
            return Ending.DRAW

        if self.state.has_legal_move():
            return Ending.ONGOING
        if self.checks[color]:
            return Ending.CHECKMATE
        return Ending.STALEMATE

    def draw(self, screen: pygame.Surface, square_size: int = SQUARE_SIZE) -> None:
        render_board(screen, self, square_size)
