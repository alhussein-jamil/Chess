import dataclasses as dc
from typing import Dict, List, Union

import pygame
from enum import Enum

from piece import ILLEGAL, LEGAL, Color, MoveState, Piece, PieceType, Position, Bishop, King, Knight, Pawn, Queen, Rook
class Ending(Enum):
    CHECKMATE = 1
    STALEMATE = 2
    DRAW = 3
    ONGOING = 4
@dc.dataclass
class Board:
    dim_x: int
    dim_y: int
    board: list = None
    pieces: List[Piece] = dc.field(default_factory=list)
    dragged_piece: Union[Piece, None] = None
    checks: Dict[Color, bool] = dc.field(default_factory=dict)
    checkmates: Dict[Color, bool] = dc.field(default_factory=dict)
    turn: Color = Color.WHITE
    promotion: PieceType = PieceType.KNIGHT
    checker: Piece = None
    moves_without_capture: int = 0
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
        self.checks = {Color.WHITE: False, Color.BLACK: False}
        self.checkmates = {Color.WHITE: Ending.ONGOING, Color.BLACK: Ending.ONGOING}

    def update_board(self):
        self.board = [[None for _ in range(self.dim_x)] for _ in range(self.dim_y)]
        for piece in self.pieces:
            self.board[piece.position.y][piece.position.x] = piece

    def update(self):
        self.update_board()
        for piece in self.pieces:
            piece.update_legal_moves(self)
        # self.updateControlledSquares()
        self.update_checks()

    def check_material_insufficient(self):
            # Check if there is insufficient material for checkmate
            if len(self.pieces) == 2:
                return True
            elif len(self.pieces) == 3:
                # Check if the remaining pieces are knights or bishops
                piece_types = [piece.piece_type for piece in self.pieces]
                return all(
                    piece_type in [PieceType.KNIGHT, PieceType.BISHOP]
                    for piece_type in piece_types
                )
            elif len(self.pieces) == 4:
                # Check for specific scenarios where the combination of pieces
                # could lead to a draw due to insufficient material for checkmate
                piece_types = [piece.piece_type for piece in self.pieces]
                # If the remaining pieces are two bishops of opposite colors
                if piece_types.count(PieceType.BISHOP) == 2:
                    piece_colors = [piece.color for piece in self.pieces if piece.piece_type == PieceType.BISHOP]
                    if piece_colors[0] != piece_colors[1]:
                        return True
                # If the remaining pieces are a bishop and a knight
                if PieceType.BISHOP in piece_types and PieceType.KNIGHT in piece_types:
                    return True
            return False


    def check_end(self, color: Color):

        if self.moves_without_capture >= 50:
            return Ending.DRAW

        if self.check_material_insufficient():
            return Ending.DRAW

        color_pieces = [p for p in self.pieces if p.color == color]
        for piece in color_pieces:
            for new_position in piece.legal_moves:
                trying,_ = self.try_move(piece, new_position, False)
                if trying:
                    return Ending.ONGOING
        if self.checks[color]:
            return Ending.CHECKMATE
        return Ending.STALEMATE

    def update_checks(self):
        # find the kings
        kings = {Color.WHITE: None, Color.BLACK: None}
        for piece in self.pieces:
            if piece.piece_type == PieceType.KING:
                kings[piece.color] = piece

        self.checks = {Color.WHITE: False, Color.BLACK: False}
        # check if the kings are in check
        for color, king in kings.items():
            if king is not None:
                opposite_color = Color.WHITE if color == Color.BLACK else Color.BLACK
                opposite_color_pieces = [p for p in self.pieces if p.color == opposite_color]
                for piece in opposite_color_pieces:
                    if king.position in piece.legal_moves:
                        self.checks[color] = True
                        break
                else:
                    self.checks[color] = False

    def undo_move(self, piece, old_position, backup_piece):
        piece.position = old_position
        piece.moved -= 1
        if backup_piece is not None:
            if not backup_piece in self.pieces:
                self.pieces.append(backup_piece)


    def try_move(self, piece: Piece, new_position: Position, move: bool = True):
        old_position = Position(piece.position.x, piece.position.y)
        piece.position = new_position
        piece.moved += 1
        backup_piece = self.board[new_position.y][new_position.x]
        capture_value = 0
        try:
            self.pieces.remove(backup_piece)    
        except:
            pass
        self.update()
        return_value = True
        if move: 
            if self.checks[piece.color]:
                self.undo_move(piece, old_position, backup_piece)
                return_value = False
            else: 
                self.moves_without_capture += 1
                if backup_piece is not None:
                    self.moves_without_capture = 0
                    capture_value += backup_piece.value
        else: 
            self.undo_move(piece, old_position, backup_piece)
            return_value = not self.checks[piece.color]
        self.update()
        return return_value, capture_value

    def handle_promotion(self, piece: Piece):
        if piece.piece_type == PieceType.PAWN: 
            if (piece.position.y == 0 and piece.color == Color.WHITE) or (piece.position.y == 7 and piece.color == Color.BLACK):
                self.pieces.remove(piece)
                self.add_piece(self.promote_to(piece))
                
    def print_active_pieces(self):
        for piece in self.pieces:
            if piece.moved > 0:
                print(piece)

    def move_piece(self, piece, new_position: Position):     
        return_value = False     
        capture_value = 0     
        if self.in_bounds(new_position):
            move_state = piece.move(new_position, self)
            return_value =  self.handle_castling(piece, new_position)
            
            if not return_value:
                if any(state in move_state for state in LEGAL):
                    return_value, capture_value = self.try_move(piece, new_position)
            #Handle Dragging new piece
            if MoveState.CREATED in move_state:
                self.pieces.append(piece)

            # Handle promotion
            self.handle_promotion(piece)
            self.update()
            return_value = return_value and not self.checks[piece.color]

            if return_value:
                opposite_color = (
                            Color.WHITE
                            if piece.color == Color.BLACK
                            else Color.BLACK
                        )
                self.turn = opposite_color
                self.checkmates[opposite_color] = self.check_end(opposite_color)
            
        return return_value, capture_value
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
                rook is not None
                and rook.piece_type == PieceType.ROOK
                and rook.moved == 0
            ):
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
                squares_between_ = [
                    Position(king.position.x + i * direction, king.position.y)
                    for i in range(1, n_squares)
                ]
                controlled_squares = False
                #check that no piece is attacking the squares between the king and the rook
                for position in squares_between_:
                    opposite_color_pieces = [p for p in self.pieces if p.color == opponent_color]
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
                self.move_piece(self.dragged_piece, new_position)
                self.dragged_piece = None
                self.update()



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
        if self.checkmates[Color.WHITE] == Ending.CHECKMATE:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! Black wins!", True, blue)
            text_rect = text.get_rect(
                center=(self.dim_x * square_size // 2, self.dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)
        elif self.checkmates[Color.BLACK] == Ending.CHECKMATE:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("CHECKMATE! White wins!", True, blue)
            text_rect = text.get_rect(
                center=(self.dim_x * square_size // 2, self.dim_y * square_size // 2)
            )
            screen.blit(text, text_rect)
        elif self.checkmates[Color.WHITE] in [Ending.STALEMATE, Ending.DRAW] or self.checkmates[Color.BLACK] in [Ending.STALEMATE, Ending.DRAW]:
            font = pygame.font.Font("freesansbold.ttf", 40)
            text = font.render("STALEMATE! DRAW!", True, blue)
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
        # # Draw controlled squares with a flashy color
        # for color, positions in self.controlled_squares.items():
        #     for position in positions:
        #         # Get the count of pieces controlling this square for the current color
        #         count = positions.count(position)
        #         # Render the count onto the square
        #         font = pygame.font.Font("freesansbold.ttf", 30)
        #         dir = 1 if color == Color.WHITE else -1
        #         letter = "B" if color == Color.BLACK else "W"
        #         # Render white count with a neon glow
        #         text = font.render(
        #             letter + str(count),
        #             True,
        #             (0, 255, 255) if color == Color.WHITE else (255, 0, 255),
        #         )
        #         white_text_rect = text.get_rect(
        #             center=(
        #                 position.x * square_size
        #                 + square_size // 2
        #                 + dir * square_size // 4,
        #                 position.y * square_size + square_size // 2,
        #             )
        #         )
        #         screen.blit(text, white_text_rect)

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
