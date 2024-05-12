import time

import pygame

from src.env.rl.mono_agent_env import ChessEnvMono
from src.env.rl.multi_agent_env import ChessEnvMulti

env = ChessEnvMulti(render_mode="human")
env.reset()
env.render()
done = False
game_quit = False
while not game_quit:
    if done:
        env.reset()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_quit = True
    action = env.action_space.sample()
    print(sum([len(piece.legal_moves) for piece in env.board.pieces[env.board.turn]]))
    obs, rewards, dones, _, _ = env.step(
        action if isinstance(env, ChessEnvMono) else {"White": action, "Black": action}
    )
    if isinstance(dones, dict):
        done = dones["__all__"]
    time.sleep(0.1)
    if isinstance(obs, dict):
        obs = obs["White"]
    env.render_from_observation(obs)
