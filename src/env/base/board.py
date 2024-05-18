from copy import deepcopy
import dataclasses as dc
from typing import Dict, List, Union

import pygame
from ...globals import (
    Color,
    Ending,
    MoveState,
    PieceType,
    DIM_X as dim_x,
    DIM_Y as dim_y,
    SQUARE_SIZE as square_size,
    LEGAL,
)
from .piece import (
    Bishop,
    Knight,
    King,
    Piece,
    Position,
    Queen,
    Rook,
    OffBoard,
    NullPiece,
)


@dc.dataclass
class Board:
    danger_level: Dict[Position, int] = dc.field(default_factory=dict)
    pieces: Dict[Color, List[Piece]] = dc.field(default_factory=dict)
    dragged_piece: Union[Piece, None] = None
    checks: Dict[Color, bool] = dc.field(default_factory=dict)
    checkmates: Dict[Color, Ending] = dc.field(default_factory=dict)
    turn: Color = Color.WHITE
    promotion: PieceType = PieceType.KNIGHT
    moves_without_capture: int = 0
    board: Dict[Position, Piece] = dc.field(default_factory=dict)
    kings: Dict[Color, King] = dc.field(default_factory=dict)

    def __post_init__(self):
        self.checks = {Color.WHITE: False, Color.BLACK: False}
        self.checkmates = {Color.WHITE: Ending.ONGOING, Color.BLACK: Ending.ONGOING}
        self.board = {
            Position(x, y): NullPiece() for x in range(dim_x) for y in range(dim_y)
        }
        self.pieces = {Color.WHITE: [], Color.BLACK: []}

    @classmethod
    def from_pieces(cls, pieces: List[Piece], *args, **kwargs) -> "Board":
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

    def copy_ai(self):
        return deepcopy(self)

    @staticmethod
    def in_bounds(position: Position) -> bool:
        return 0 <= position.x < dim_x and 0 <= position.y < dim_y

    def update(self):
        self._update_board()
        self._update_pieces()
        self._update_checks()

    def _update_board(self):
        self.board = {position: NullPiece() for position in self.board.keys()}
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

    def move_piece(self, piece: Piece, new_position: Position) -> tuple[bool, int]:
        return_value = False
        capture_value = 0
        if self.in_bounds(new_position):
            move_state = piece.move(new_position, self)
            return_value = self.handle_castling(piece, new_position)

            if not return_value:
                if any(state in move_state for state in LEGAL):
                    return_value, capture_value = self.try_move(piece, new_position)

            # Handle Dragging new piece
            if MoveState.CREATED in move_state:
                self.pieces[piece.color].append(piece)

            # Handle promotion
            self.handle_promotion(piece)
            self.update()
            return_value = return_value and not self.checks[piece.color]

            if return_value:
                opposite_color = (
                    Color.WHITE if piece.color == Color.BLACK else Color.BLACK
                )
                self.turn = opposite_color
                self.checkmates[opposite_color] = self.check_end(opposite_color)

        return return_value, capture_value

    def _undo_move(self, piece, old_position, backup_piece):
        piece.position = old_position
        piece.moved -= 1
        if not isinstance(backup_piece, NullPiece):
            if backup_piece not in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]:
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

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            grid_x = mouse_pos[0] // square_size
            grid_y = mouse_pos[1] // square_size
            mouse_position = Position(grid_x, grid_y)
            if self.in_bounds(Position(grid_x, grid_y)):
                piece = self.board[mouse_position]
                if not isinstance(piece, NullPiece) and piece.color == self.turn:
                    self.dragged_piece = piece
                    self.board[mouse_position] = NullPiece()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_piece is not None:
                mouse_pos = pygame.mouse.get_pos()
                grid_x = mouse_pos[0] // square_size
                grid_y = mouse_pos[1] // square_size
                new_position = Position(grid_x, grid_y)
                self.move_piece(self.dragged_piece, new_position)
                self.dragged_piece = None
                self.update()

    def handle_promotion(self, piece: Piece):
        if piece.piece_type == PieceType.PAWN:
            if (piece.position.y == 0 and piece.color == Color.WHITE) or (
                piece.position.y == 7 and piece.color == Color.BLACK
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
            if (
                rook is not NullPiece()
                and rook.piece_type == PieceType.ROOK
                and rook.moved == 0
            ):
                # Check if squares between king and rook are empty
                empty_squares = all(
                    isinstance(
                        self.get(
                            Position(king.position.x + i * direction, king.position.y)
                        ),
                        NullPiece,
                    )
                    for i in range(1, n_squares)
                )
                opponent_color = (
                    Color.WHITE if king.color == Color.BLACK else Color.BLACK
                )
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
                    # Move the king
                    self.try_move(king, new_position)
                    # Move the rook
                    self.try_move(
                        rook, Position(king.position.x - direction, king.position.y)
                    )
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
                piece.piece_type
                for piece in self.pieces[Color.WHITE] + self.pieces[Color.BLACK]
            ]
            return all(
                piece_type in [PieceType.KNIGHT, PieceType.BISHOP]
                for piece_type in piece_types
            )
        elif len(all_pieces) == 4:
            # Check for specific scenarios where the combination of pieces
            # could lead to a draw due to insufficient material for checkmate
            piece_types = [piece.piece_type for piece in all_pieces]
            # If the remaining pieces are two bishops of opposite colors
            if piece_types.count(PieceType.BISHOP) == 2:
                piece_colors = [
                    piece.color
                    for piece in all_pieces
                    if piece.piece_type == PieceType.BISHOP
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

    def draw(self, screen: pygame.Surface):
        # Define colors
        brown = (165, 42, 42)
        beige = (245, 245, 220)
        blue = (0, 0, 255)
        black = (0, 0, 0)

        # Draw board background
        screen.fill(beige)

        # Draw grid lines and cells with a funky pattern
        for x in range(dim_x):
            for y in range(dim_y):
                color = brown if (x + y) % 2 == 0 else beige
                pygame.draw.rect(
                    screen,
                    color,
                    (x * square_size, y * square_size, square_size, square_size),
                )

        # Draw letters for columns (A-H) with a cool font
        for i, letter in enumerate("ABCDEFGH"):
            font = pygame.font.Font("freesansbold.ttf", 36)
            text = font.render(letter, True, black)
            screen.blit(
                text,
                (
                    i * square_size + square_size // 2 - text.get_width() // 2,
                    square_size * 8,
                ),
            )

        # Draw numbers for rows (1-8) with a vibrant color
        for i, number in enumerate("87654321"):
            font = pygame.font.Font("freesansbold.ttf", 36)
            text = font.render(number, True, black)
            screen.blit(
                text,
                (
                    square_size * 8.1,
                    i * square_size + square_size // 2 - text.get_height() // 2,
                ),
            )

        # Draw checkmate indicator with excitement
        if self.checkmates[Color.WHITE] == Ending.CHECKMATE:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! Black wins!", True, blue)
            text_rect = text.get_rect(
                center=(dim_x * square_size // 2, dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)
        elif self.checkmates[Color.BLACK] == Ending.CHECKMATE:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! White wins!", True, blue)
            text_rect = text.get_rect(
                center=(dim_x * square_size // 2, dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)
        elif self.checkmates[Color.WHITE] in [
            Ending.STALEMATE,
            Ending.DRAW,
        ] or self.checkmates[Color.BLACK] in [Ending.STALEMATE, Ending.DRAW]:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("STALEMATE! DRAW!", True, blue)
            text_rect = text.get_rect(
                center=(dim_x * square_size // 2, dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)

        # Draw pieces with a funky twist
        for y in range(dim_y):
            for x in range(dim_x):
                position = Position(x, y)
                piece = self.board[position]
                if not isinstance(piece, NullPiece) and piece != self.dragged_piece:
                    if piece.icon_path.exists():
                        # Resize the piece to fit the square size with a groovy effect
                        icon = pygame.image.load(piece.icon_path).convert_alpha()
                        resized_icon = pygame.transform.scale(
                            icon, (square_size, square_size)
                        )
                        screen.blit(resized_icon, (x * square_size, y * square_size))
        # Draw controlled squares with a flashy color
        # for position, danger in self.danger_level.items():
        #     # Get the count of pieces controlling this square for the current color
        #     # count = positions.count(position)
        #     # Render the count onto the square
        #     font = pygame.font.Font("freesansbold.ttf", 30)
        #     # letter = "B" if color == Color.BLACK else "W"
        #     # Render white count with a neon glow
        #     text = font.render(
        #         str(danger),
        #         True,
        #         (0, 255, 255) if color == Color.WHITE else (255, 0, 255),
        #     )
        #     text_rect = text.get_rect(
        #         center=(
        #             position.x * square_size + square_size // 2,
        #             position.y * square_size + square_size // 2,
        #         )
        #     )
        #     screen.blit(text, text_rect)

        # Draw dragged piece at mouse position with a sparkling animation
        if self.dragged_piece is not None:
            # Resize the piece to fit the square size with a dazzling shine
            icon = pygame.image.load(self.dragged_piece.icon_path).convert_alpha()
            resized_icon = pygame.transform.scale(icon, (square_size, square_size))
            mouse_pos = pygame.mouse.get_pos()
            screen.blit(
                resized_icon,
                (mouse_pos[0] - square_size // 2, mouse_pos[1] - square_size // 2),
            )
