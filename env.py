import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pygame
from typing import Tuple
from board import Board, Ending
from piece import Bishop, Color, King, Knight, Pawn, Position, Queen, Rook, LEGAL, MoveState, PieceType
piece_to_index = {
    None: 0,
    Rook: 1,
    Knight: 2,
    Bishop: 3,
    Queen: 4,
    King: 5,
    Pawn: 6
}
class ChessEnv(gym.Env):
    metadata = {'render.modes': ['human', 'rgb_array']}
    def __init__(self, dim_x: int, dim_y: int, render_mode: str = 'human'):
        super(ChessEnv, self).__init__()
        self.board = Board(dim_x, dim_y)
        self.square_size = 64  # Assuming square size of 64 pixels
        if render_mode == 'human':
            pygame.init()
            pygame.display.set_caption("Chess Game")
            self.screen = pygame.display.set_mode((dim_x * self.square_size+100, dim_y * self.square_size+100))
        else: 
            ...
        self.render_mode = render_mode

        self.observation_space = spaces.Box(low=0, high=1, shape=(dim_x, dim_y, 7), dtype=np.uint8)  # Assuming 6 channels for each piece
        self.populate_board()
        # The action space has at most 16 piece to be picked and 64 squares to move to but sometimes squares are not legal
        # However, our implementation of the game allows access to legal moves for each piece
        # We can receive 16 probabilities for choosing a piece and 64 probabilities for choosing a square to move to. From that we can choose the piece and the move to make
        #count pieces
        n_pieces = 0
        for piece in self.board.pieces:
            if piece.color == Color.WHITE:
                n_pieces += 1
        # self.action_space = spaces.Tuple((spaces.Box(low=0, high=1, shape=(n_pieces, 64), dtype=np.float32), spaces.Discrete(4), spaces.Discrete(3))) # the first part of the action space is the probability of choosing a piece and the second part is the promotion type, the third being castling direction
        self.action_space = spaces.Box(low=0, high=1, shape=(3 + 4 + n_pieces*64,), dtype=np.float32) #flatten the action space
    def get_observation(self):
        observation = np.zeros((self.board.dim_x, self.board.dim_y, 7), dtype=np.uint8)
        for piece in self.board.pieces:
            observation[piece.position.y][piece.position.x][piece_to_index[type(piece)]] = 1
        return observation

    def populate_board(self):
        STARTINGCONFIGURATION = [
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

        for piece in STARTINGCONFIGURATION:
            self.board.add_piece(piece)
        self.board.update()

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, dict]:
        castling_dir = np.argmax(action[:3])
        king = [p for p in self.board.pieces if p.color == self.board.turn and type(p) == King][0]

        castled = False
        if castling_dir == 1: #king side castle
            if self.board.turn == Color.WHITE:
                castled = self.board.handle_castling(king, new_position=Position(6, 7))
            else:
                castled =  self.board.handle_castling(king, new_position=Position(6, 0))
        elif castling_dir == 2: #queen side castle
            if self.board.turn == Color.WHITE:
                castled = self.board.handle_castling(king, new_position=Position(2, 7))
            else:
                castled = self.board.handle_castling(king, new_position=Position(2, 0))

        self.board.promotion = PieceType(2 + np.argmax(action[3:7]))
        action = action[7:].reshape(-1, 64)
        # Reset the reward to zero
        reward = 0
        # Boolean flag to indicate whether the episode is done
        done = False
        current_color = self.board.turn
        if not castled:
            # Iterate over each piece and its corresponding action probabilities
            current_pieces = [p for p in self.board.pieces if p.color==self.board.turn]
            proba_sum = np.sum(action, axis=1)
            moved = False
            #sort white pieces by the action probabilities
            sorted_white_pieces = [x for _,x in sorted(zip(proba_sum, current_pieces), key=lambda pair: pair[0])]
            for i,piece in enumerate(sorted_white_pieces):
                # Choose the move with the highest probability
                moves = np.argsort(action[i])[::-1]
                for move in moves:
                    if move < len(piece.legal_moves):
                        return_value, capture_value = self.board.move_piece(piece, piece.legal_moves[move])
                        if return_value:
                            reward += capture_value / 10.0
                            reward -= 0.01
                            moved = True
                            break
                if moved:
                    break
        done = self.board.checkmates[Color.WHITE] != Ending.ONGOING or self.board.checkmates[Color.BLACK] != Ending.ONGOING
        if done:
            if self.board.checkmates[current_color] == Ending.CHECKMATE:
                reward -= 2
            elif self.board.checkmates[self.board.turn] == Ending.CHECKMATE:
                reward += 2
            elif self.board.checkmates[current_color] in [Ending.STALEMATE, Ending.DRAW]:
                reward += 1
            elif self.board.checkmates[self.board.turn] in [Ending.STALEMATE, Ending.DRAW]:
                reward += 1
        # Return the new observation, reward, done flag, and additional info (empty for now)
        return self.get_observation(), reward, done, False, {}

    def reset(self, **kwargs):
        # Reset the board to the initial state
        self.board = Board(self.board.dim_x, self.board.dim_y)
        self.populate_board()
        return self.get_observation(), {}

    def render(self, mode='human'):
            self.board.draw(self.screen, self.square_size)
            pygame.display.flip()

    def close(self):
        pygame.quit()
