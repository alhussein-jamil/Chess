import time

import pygame

from mono_agent_env import ChessEnvMono
from multi_agent_env import ChessEnvMulti

env = ChessEnvMono(render_mode="human")
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
    obs, rewards, dones, _, _ = env.step(action)
    if isinstance(dones, dict):
        done = dones["__all__"]
    env.render()
    time.sleep(0.1)
