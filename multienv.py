from gymnasium import spaces
import numpy as np
import pygame
from typing import Any, Dict, Tuple
from board import Board, Ending
from piece import Bishop, Color, King, Knight, Pawn, Position, Queen, Rook, PieceType
from ray.tune.registry import register_env
from ray.rllib.env.multi_agent_env import MultiAgentEnv

piece_to_index = {
    None: 0,
    Rook: 1,
    Knight: 2,
    Bishop: 3,
    Queen: 4,
    King: 5,
    Pawn: 6
}

color_name_map = {
    Color.WHITE: "White",
    Color.BLACK: "Black"
}

class ChessEnvMulti(MultiAgentEnv):
    metadata = {'render_modes': ['human', 'rgb_array']}
    def __init__(self, dim_x: int = 8, dim_y: int = 8, render_mode: str = 'rgb_array'):
        super(ChessEnvMulti, self).__init__()
        self.board = Board(dim_x, dim_y)
        self.square_size = 64  # Assuming square size of 64 pixels
        pygame.init()
        pygame.display.set_caption("Chess Game")
        self.screen = pygame.display.set_mode((dim_x * self.square_size + 50, dim_y * self.square_size + 50))
        self.render_mode = render_mode
        self.observation_space = spaces.Box(low=0, high=2, shape=(dim_x*dim_y*7,), dtype=np.uint8)
        self.turn = Color.WHITE
        self.populate_board()
        n_pieces = 0
        for piece in self.board.pieces:
            if piece.color == Color.WHITE:
                n_pieces += 1
        self.action_space = spaces.Box(low=0, high=1, shape=(3 + 4 + n_pieces * 64,), dtype=np.float32)
        self.agents_ids = ["White", "Black"]

    def _get_observation(self):
        observation = np.zeros((self.board.dim_x, self.board.dim_y, 7), dtype=np.uint8)

        for piece in self.board.pieces:
            observation[piece.position.y][piece.position.x][piece_to_index[type(piece)]] = 1 if piece.color == Color.WHITE else 2
        return observation.reshape(-1)
    
    def get_observation(self):
        return {"White": self._get_observation(), "Black": self._get_observation()}
    
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

    def _step(self, action: np.ndarray, done: bool = False) -> Tuple[np.ndarray, float, bool, dict]:
        reward = 0  
        if not done:
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
                                reward += capture_value / 100.0
                                reward -= 0.02
                                moved = True
                                break
                    if moved:
                        break

            done = self.board.checkmates[Color.WHITE] != Ending.ONGOING or self.board.checkmates[Color.BLACK] != Ending.ONGOING

        # Return the new observation, reward, done flag, and additional info (empty for now)
        return self._get_observation(), reward, done, False, {}
    

    def step(self, action_dict: Dict[Any,Any]) -> Tuple[Dict[Any,Any], Dict[Any,Any], Dict[Any,Any], Dict[Any,Any]]:
        
        action_white = action_dict[self.agents_ids[0]]
        action_black = action_dict[self.agents_ids[1]]


        reward_white = 0
        reward_black = 0
        if self.turn == Color.WHITE:
            obs, reward, done, truncated, info = self._step(action_white)
            reward_white += reward
        else:
            obs, reward, done, truncated, info = self._step(action_black)
            reward_black += reward

        other_color = Color.WHITE if self.turn == Color.BLACK else Color.BLACK

        # Modify the rewards in function of who won
        if done:
            if self.board.checkmates[Color.WHITE] == Ending.CHECKMATE:
                reward_white -= 1
                reward_black += 1
            elif self.board.checkmates[Color.BLACK] == Ending.CHECKMATE:
                reward_white += 1
                reward_black -= 1
            # else:
            #     reward_white += 1.0
            #     reward_black += 1.0

        obs = {
            self.agents_ids[0]: obs,
            self.agents_ids[1]: obs
        }
        rewards = {
            self.agents_ids[0]: reward_white,
            self.agents_ids[1]: reward_black
        }
        dones = {
            self.agents_ids[0]: done,
            self.agents_ids[1]: done,
            "__all__": done
        }
        infos = {
            self.agents_ids[0]: info,
            self.agents_ids[1]: info
        }
        truncateds = {
            self.agents_ids[0]: truncated,
            self.agents_ids[1]: truncated,
            "__all__": truncated
        }
        self.turn = other_color
        return obs, rewards, dones, truncateds, infos

    def reset(self, **kwargs):
        # Reset the board to the initial state
        self.board = Board(self.board.dim_x, self.board.dim_y)
        self.populate_board()
        return self.get_observation(), {self.agents_ids[0]: {}, self.agents_ids[1]: {}}

    def render(self, mode=None):
        if mode is None:
            mode = self.render_mode
        self.board.draw(self.screen, self.square_size)
        pygame.display.flip()
        if mode == 'rgb_array':
            return self.screen

    def close(self):
        pygame.quit()

#register the environment
register_env("ChessMulti-v0", lambda config: ChessEnvMulti(**config))