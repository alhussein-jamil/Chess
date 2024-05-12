import pygame

from src.env.base.board import Board
from src.env.base.piece import (
    Bishop,
    Color,
    King,
    Knight,
    Pawn,
    Queen,
    Rook,
    STARTING_PIECES as STARTINGCONFIGURATION,
)
from copy import deepcopy

# Initialize Pygame
pygame.init()

# Set screen dimensions
screen_width = 1050  # Increased width to accommodate buttons
screen_height = 850

chessboard = Board()

# Set window title (optional)
pygame.display.set_caption("Chess Game")

# Set screen size
screen = pygame.display.set_mode((screen_width, screen_height))

# Define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)

# Define button dimensions and positions
button_width = 150
button_height = 50
button_margin = 20
button_x = (
    screen_width - button_width - button_margin
)  # Adjusted position for first button
button_y_add_piece = 50  # Adjusted position for Add Piece button

# Define font
font = pygame.font.Font(None, 30)
# Game loop
running = True
new_piece_color = Color.WHITE
toggle_button_color = GRAY  # Default color for the toggle button


chessboard = Board.from_pieces(deepcopy(STARTINGCONFIGURATION))


# Function to create different types of pieces
def add_piece(piece_type):
    if piece_type == "Pawn":
        new_piece = Pawn(color=new_piece_color)
    elif piece_type == "Rook":
        new_piece = Rook(color=new_piece_color)
    elif piece_type == "Bishop":
        new_piece = Bishop(color=new_piece_color)
    elif piece_type == "Queen":
        new_piece = Queen(color=new_piece_color)
    elif piece_type == "Knight":
        new_piece = Knight(color=new_piece_color)
    elif piece_type == "King":
        new_piece = King(color=new_piece_color)
    # Add more elif statements for other piece types as needed
    else:
        return  # Invalid piece type

    chessboard.dragged_piece = new_piece


# Function to create button text
def draw_text(text, font, color, surface, x, y):
    textobj = font.render(text, 1, color)
    textrect = textobj.get_rect()
    textrect.center = (x, y)
    surface.blit(textobj, textrect)


# Function to draw buttons
def draw_button(surface, color, x, y, width, height, text):
    pygame.draw.rect(surface, color, (x, y, width, height))
    draw_text(text, font, BLACK, surface, x + width // 2, y + height // 2)


chessboard.update()
while running:
    # chessboard.draw(screen=screen, square_size=100)

    # Inside the game loop, draw buttons for each piece type
    piece_types = [
        "Pawn",
        "Bishop",
        "Rook",
        "Queen",
        "Knight",
        "King",
    ]  # Add more piece types as needed
    button_y_offset = button_y_add_piece + button_height + button_margin

    button_y_toggle_color = button_y_offset + len(piece_types) * (
        button_height + button_margin
    )
    # Handle events
    for event in pygame.event.get():
        chessboard.handle_event(event)
        if event.type == pygame.QUIT:
            running = False
        # Inside the main game loop, after handling events
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            # Inside the main game loop, handle mouse click event for each piece type button
            for i, piece_type in enumerate(piece_types):
                if (
                    button_x <= mouse_pos[0] <= button_x + button_width
                    and button_y_offset + i * (button_height + button_margin)
                    <= mouse_pos[1]
                    <= button_y_offset
                    + i * (button_height + button_margin)
                    + button_height
                ):
                    add_piece(piece_type)

            if (
                button_x <= mouse_pos[0] <= button_x + button_width
                and button_y_toggle_color
                <= mouse_pos[1]
                <= button_y_toggle_color + button_height
            ):
                # Toggle the color of the new piece
                new_piece_color = (
                    Color.WHITE if new_piece_color == Color.BLACK else Color.BLACK
                )
                # Change the color of the toggle button when pressed
                toggle_button_color = WHITE if toggle_button_color == BLACK else BLACK
    chessboard.draw(screen=screen)
    for i, piece_type in enumerate(piece_types):
        draw_button(
            screen,
            WHITE,
            button_x,
            button_y_offset + i * (button_height + button_margin),
            button_width,
            button_height,
            f"Add {piece_type}",
        )

    draw_button(
        screen,
        toggle_button_color,  # Use the dynamic color for the toggle button
        button_x,
        button_y_toggle_color,
        button_width,
        button_height,
        "Toggle Color",
    )
    # Update the display
    pygame.display.flip()

# Quit Pygame
pygame.quit()
