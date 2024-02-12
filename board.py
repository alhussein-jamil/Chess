import dataclasses as dc
from typing import List, Union, Dict

import pygame

from piece import ILLEGAL, LEGAL, MoveState, Piece, Position, Color, PieceType
import copy

@dc.dataclass
class Board:
    dim_x: int
    dim_y: int
    board: list = None
    pieces: List[Piece] = dc.field(default_factory=list)
    dragged_piece: Union[Piece, None] = None
    controlled_squares: List[Dict[Color, List[Piece]]] = dc.field(default_factory=list)
    checks: Dict[Color, bool] = dc.field(default_factory=dict)

    def in_bounds(self, position: Position):
        return 0 <= position.x < self.dim_x and 0 <= position.y < self.dim_y

    def get(self, position: Position):
        return self.board[position.y][position.x]
    def __post_init__(self):
        self.controlled_squares = [{Color.WHITE: [], Color.BLACK: []}]

    def update(self):
        self.board = [[None for _ in range(self.dim_x)] for _ in range(self.dim_y)]
        for piece in self.pieces:
            self.board[piece.position.y][piece.position.x] = piece
        self.updateControlledSquares()
        self.update_checks()

    def update_checks(self):    
        #find the kings 
        kings = {Color.WHITE: None, Color.BLACK: None}
        for piece in self.pieces:
            if piece.piece_type == PieceType.KING:
                kings[piece.color] = piece
        #check if the kings are in check
        for color, king in kings.items():
            if king is not None:
                opposite_color = Color.WHITE if color == Color.BLACK else Color.BLACK
                for pos in self.controlled_squares[opposite_color]:
                    if pos == king.position:
                        self.checks[color] = True
                        break
                else:
                    self.checks[color] = False
                    
    def draw(self, screen: pygame.Surface, square_size: int):
        self.square_size = square_size
        # Define colors
        brown = (165, 42, 42)
        beige = (245, 245, 220)

        # Draw board background
        screen.fill(beige)

        # Draw grid lines and cells
        for x in range(self.dim_x):
            for y in range(self.dim_y):
                color = brown if (x + y) % 2 == 0 else beige
                pygame.draw.rect(
                    screen, color,
                    (x * square_size, y * square_size, square_size, square_size)
                )

        # Draw letters for columns (A-H)
        for i, letter in enumerate("ABCDEFGH"):
            font = pygame.font.Font(None, 36)
            text = font.render(letter, True, (0, 0, 0))
            screen.blit(text, (i * square_size + square_size // 2 - text.get_width() // 2, square_size * 8))

        # Draw numbers for rows (1-8)
        for i, number in enumerate("87654321"):
            font = pygame.font.Font(None, 36)
            text = font.render(number, True, (0, 0, 0))
            screen.blit(text, (square_size * 8.1, i * square_size + square_size // 2 - text.get_height() // 2))

        # Draw pieces
        for y in range(self.dim_y):
            for x in range(self.dim_x):
                piece = self.board[y][x]
                if piece is not None and piece != self.dragged_piece:
                    # Resize the piece to fit the square size
                    resized_icon = pygame.transform.scale(
                        piece.icon, (square_size, square_size)
                    )
                    screen.blit(resized_icon, (x * square_size, y * square_size))
        # Draw controlled squares
        for color, positions in self.controlled_squares.items():
            for position in positions:
                # Get the count of pieces controlling this square for the current color
                count = positions.count(position)
                # Render the count onto the square
                font = pygame.font.Font(None, 30)
                dir = 1 if color == Color.WHITE else -1
                letter = "B" if color == Color.BLACK else "W"   
                # Render white count
                text = font.render(letter+str(count), True, (0,0,255) if color == Color.WHITE else (0,0,0))
                white_text_rect = text.get_rect(center=(position.x * square_size + square_size // 2 + dir* square_size // 4, position.y * square_size + square_size // 2))
                screen.blit(text, white_text_rect)
                

        # Draw dragged piece at mouse position
        if self.dragged_piece is not None:
            # Resize the piece to fit the square size
            resized_icon = pygame.transform.scale(
                self.dragged_piece.icon, (square_size, square_size)
            )
            mouse_pos = pygame.mouse.get_pos()
            screen.blit(
                resized_icon,
                (mouse_pos[0] - square_size // 2, mouse_pos[1] - square_size // 2),
            )
    def updateControlledSquares(self):
        self.controlled_squares = {Color.WHITE: [], Color.BLACK: []}
        for piece in self.pieces:
            for pos_x in range(self.dim_x):
                for pos_y in range(self.dim_y):
                    position = Position(pos_x, pos_y)
                    if position == piece.position:
                        continue
                    temp_piece = Piece(color = Color.WHITE if piece.color == Color.BLACK else Color.BLACK, position= position)
                    original_piece = self.board[position.y][position.x]
                    self.board[position.y][position.x] = temp_piece
                    state = piece.move(position, self)

                    if any(s in state for s in LEGAL):
                        self.controlled_squares[piece.color].append(position)
                    self.board[position.y][position.x] = original_piece

    def undo_move(self, piece, old_position, backup_piece):
        piece.position = old_position
        piece.moved -= 1
        if backup_piece is not None:
            self.pieces.append(backup_piece)
        self.update()

    def handle_event(self, event):
        square_size = self.square_size
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            
            grid_x = mouse_pos[0] // square_size
            grid_y = mouse_pos[1] // square_size
            if self.in_bounds(Position(grid_x, grid_y)):
                piece = self.board[grid_y][grid_x]
                if piece is not None:
                    self.dragged_piece = piece
                    self.board[grid_y][grid_x] = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_piece is not None:
                mouse_pos = pygame.mouse.get_pos()

                grid_x = mouse_pos[0] // square_size
                grid_y = mouse_pos[1] // square_size
                old_position = self.dragged_piece.position
                new_position = Position(grid_x, grid_y)
                if self.in_bounds(new_position):
                    move_state = self.dragged_piece.move(new_position, self)

                    if any(state in move_state for state in LEGAL):
                        self.dragged_piece.position = new_position
                        self.dragged_piece.moved += 1
                        backup_piece = self.board[new_position.y][new_position.x]
                        if self.board[new_position.y][new_position.x] is not None:
                            self.pieces.remove(
                                self.board[new_position.y][new_position.x]
                            )
                        self.update()
                        if self.checks[self.dragged_piece.color]:
                            self.undo_move(self.dragged_piece, old_position, backup_piece)
                    if MoveState.CREATED in move_state:
                        self.pieces.append(self.dragged_piece)

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
