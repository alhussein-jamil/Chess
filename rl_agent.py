from env import ChessEnv
import time
import pygame

game = ChessEnv(8, 8)
game.reset()
done = False
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
    if not done:
        # keyboard.wait("space")
        action = game.action_space.sample()
        obs, reward, done, info = game.step(action)
    else: 
        breakpoint()
        
    game.render()
    time.sleep(0.01)
