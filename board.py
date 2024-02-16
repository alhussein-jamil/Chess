import dataclasses as dc
from typing import Dict, List, Union

import pygame

from piece import ILLEGAL, LEGAL, Color, MoveState, Piece, PieceType, Position, Bishop, King, Knight, Pawn, Queen, Rook


@dc.dataclass
class Board:
    dim_x: int
    dim_y: int
    board: list = None
    pieces: List[Piece] = dc.field(default_factory=list)
    dragged_piece: Union[Piece, None] = None
    controlled_squares: List[Dict[Color, List[Piece]]] = dc.field(default_factory=list)
    checks: Dict[Color, bool] = dc.field(default_factory=dict)
    checkmates: Dict[Color, bool] = dc.field(default_factory=dict)
    turn: Color = Color.WHITE
    promotion: PieceType = PieceType.KNIGHT

    def promote_to(self,piece: Piece): 
        match self.promotion:
            case PieceType.QUEEN:
                return Queen(color=piece.color, position=piece.position)
            case PieceType.ROOK:
                return Rook(color=piece.color, position=piece.position)
            case PieceType.BISHOP:
                return Bishop(color=piece.color, position=piece.position)
            case PieceType.KNIGHT:
                return Knight(color=piece.color, position=piece.position)


    def in_bounds(self, position: Position):
        return 0 <= position.x < self.dim_x and 0 <= position.y < self.dim_y

    def get(self, position: Position):
        if not self.in_bounds(position):
            return False
        return self.board[position.y][position.x]

    def __post_init__(self):
        self.controlled_squares = [{Color.WHITE: [], Color.BLACK: []}]
        self.checks = {Color.WHITE: False, Color.BLACK: False}
        self.checkmates = {Color.WHITE: False, Color.BLACK: False}

    def update(self):

        self.board = [[None for _ in range(self.dim_x)] for _ in range(self.dim_y)]
        for piece in self.pieces:
            self.board[piece.position.y][piece.position.x] = piece
        for piece in self.pieces:
            piece.update_legal_moves(self)
        self.updateControlledSquares()
        self.update_checks()

    def checkmate(self, color: Color):
        for piece in self.pieces:
            if piece.color == color:
                for new_position in piece.legal_moves:
                    trying = self.try_move(piece, new_position, False)
                    self.update()
                    if trying:
                        return False
        return True

    def update_checks(self):
        # find the kings
        kings = {Color.WHITE: None, Color.BLACK: None}
        for piece in self.pieces:
            if piece.piece_type == PieceType.KING:
                kings[piece.color] = piece
        # check if the kings are in check
        for color, king in kings.items():
            if king is not None:
                opposite_color = Color.WHITE if color == Color.BLACK else Color.BLACK
                for pos in self.controlled_squares[opposite_color]:
                    if pos == king.position:
                        self.checks[color] = True
                        break
                else:
                    self.checks[color] = False


    def updateControlledSquares(self):
        self.controlled_squares = {Color.WHITE: [], Color.BLACK: []}
        for piece in self.pieces:
            contolled_squares = piece.legal_moves
            for position in contolled_squares:
                temp_piece = Piece(
                    color=Color.WHITE if piece.color == Color.BLACK else Color.BLACK,
                    position=position,
                )
                original_piece = self.board[position.y][position.x]
                self.board[position.y][position.x] = temp_piece
                state = piece.move(position, self)
                if MoveState.CAPTURED in state:
                    self.controlled_squares[piece.color].append(position)
                self.board[position.y][position.x] = original_piece
    def undo_move(self, piece, old_position, backup_piece):
        piece.position = old_position
        piece.moved -= 1
        if backup_piece is not None:
            self.pieces.append(backup_piece)

    def try_move(self, piece: Piece, new_position: Position, move: bool = True):
        old_position = Position(piece.position.x, piece.position.y)
        piece.position = new_position
        piece.moved += 1
        backup_piece = self.board[new_position.y][new_position.x]

        if self.board[new_position.y][new_position.x] is not None:
            self.pieces.remove(self.board[new_position.y][new_position.x])
        self.update()
        if self.checks[piece.color] or not move:
            self.undo_move(piece, old_position, backup_piece)

        if self.checks[piece.color]:
            return False
        return True

    def handle_event(self, event):
        square_size = self.square_size
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            grid_x = mouse_pos[0] // square_size
            grid_y = mouse_pos[1] // square_size
            if self.in_bounds(Position(grid_x, grid_y)):
                piece = self.board[grid_y][grid_x]
                if piece is not None and piece.color == self.turn:
                    self.dragged_piece = piece
                    self.board[grid_y][grid_x] = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_piece is not None:
                mouse_pos = pygame.mouse.get_pos()

                grid_x = mouse_pos[0] // square_size
                grid_y = mouse_pos[1] // square_size
                new_position = Position(grid_x, grid_y)
                if self.in_bounds(new_position):
                    castled = self.handle_castling(self.dragged_piece, new_position)
                    move_state = self.dragged_piece.move(new_position, self)

                    if not castled:
                        if any(state in move_state for state in LEGAL):
                            if self.try_move(self.dragged_piece, new_position):
                                
                                color = (
                                    Color.WHITE
                                    if self.dragged_piece.color == Color.BLACK
                                    else Color.BLACK
                                )
                                self.turn = color
                                self.checkmates[color] = self.checkmate(color)
                            self.update()
                    if MoveState.CREATED in move_state:
                        self.pieces.append(self.dragged_piece)

                    if self.dragged_piece.piece_type == PieceType.PAWN: 
                        if (self.dragged_piece.position.y == 0 and self.dragged_piece.color == Color.WHITE) or (self.dragged_piece.position.y == 7 and self.dragged_piece.color == Color.BLACK):
                            self.pieces.remove(self.dragged_piece)
                            self.add_piece(self.promote_to(self.dragged_piece))
                            self.update()

                self.dragged_piece = None
                self.update()

    def handle_castling(self, king: Piece, new_position: Position):
        # Check if the move is a castling move
        if (
            king.piece_type == PieceType.KING
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
                rook is not None
                and rook.piece_type == PieceType.ROOK
                and rook.moved == 0
            ):
                print("castling")
                # Check if squares between king and rook are empty
                empty_squares = all(
                    self.get(Position(king.position.x + i * direction, king.position.y))
                    is None
                    for i in range(1, n_squares)
                )
                opponent_color = (
                    Color.WHITE if king.color == Color.BLACK else Color.BLACK
                )
                # Check if squares between king and rook are controlled by the opponent
                controlled_squares = any(
                    pos in self.controlled_squares[opponent_color]
                    for pos in [
                        Position(king.position.x + i * direction, king.position.y)
                        for i in range(n_squares)
                    ]
                )
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

    @classmethod
    def from_pieces(cls, pieces: List[Piece], dim_x: int, dim_y: int):
        board = cls(dim_x, dim_y)
        for piece in pieces:
            board.board[piece.position.y][piece.position.x] = piece
            piece.created = True
        board.pieces = pieces

        return board

    def add_piece(self, piece: Piece):
        self.pieces.append(piece)
        piece.created = True
    def draw(self, screen: pygame.Surface, square_size: int):
        self.square_size = square_size
        # Define colors
        brown = (165, 42, 42)
        beige = (245, 245, 220)
        red = (255, 0, 0)
        green = (0, 255, 0)
        blue = (0, 0, 255)
        black = (0, 0, 0)

        # Draw board background
        screen.fill(beige)

        # Draw grid lines and cells with a funky pattern
        for x in range(self.dim_x):
            for y in range(self.dim_y):
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
        if self.checkmates[Color.WHITE]:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! White wins!", True, blue)
            text_rect = text.get_rect(
                center=(self.dim_x * square_size // 2, self.dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)
        elif self.checkmates[Color.BLACK]:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! Black wins!", True, blue)
            text_rect = text.get_rect(
                center=(self.dim_x * square_size // 2, self.dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)

        # Draw pieces with a funky twist
        for y in range(self.dim_y):
            for x in range(self.dim_x):
                piece = self.board[y][x]
                if piece is not None and piece != self.dragged_piece:
                    # Resize the piece to fit the square size with a groovy effect
                    resized_icon = pygame.transform.scale(
                        piece.icon, (square_size, square_size)
                    )
                    screen.blit(resized_icon, (x * square_size, y * square_size))
        # Draw controlled squares with a flashy color
        for color, positions in self.controlled_squares.items():
            for position in positions:
                # Get the count of pieces controlling this square for the current color
                count = positions.count(position)
                # Render the count onto the square
                font = pygame.font.Font("freesansbold.ttf", 30)
                dir = 1 if color == Color.WHITE else -1
                letter = "B" if color == Color.BLACK else "W"
                # Render white count with a neon glow
                text = font.render(
                    letter + str(count),
                    True,
                    (0, 255, 255) if color == Color.WHITE else (255, 0, 255),
                )
                white_text_rect = text.get_rect(
                    center=(
                        position.x * square_size
                        + square_size // 2
                        + dir * square_size // 4,
                        position.y * square_size + square_size // 2,
                    )
                )
                screen.blit(text, white_text_rect)

        # Draw dragged piece at mouse position with a sparkling animation
        if self.dragged_piece is not None:
            # Resize the piece to fit the square size with a dazzling shine
            resized_icon = pygame.transform.scale(
                self.dragged_piece.icon, (square_size, square_size)
            )
            mouse_pos = pygame.mouse.get_pos()
            screen.blit(
                resized_icon,
                (mouse_pos[0] - square_size // 2, mouse_pos[1] - square_size // 2),
            )
