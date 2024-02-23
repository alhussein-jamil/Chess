from env import ChessEnv
import pygame
import time
game = ChessEnv(8,8,"human")
game.reset()
done = False
exit = False 


while not exit: 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit = True
        if event.type == pygame.MOUSEBUTTONDOWN:
            game.reset()
    game.render()
    if not done:
        action = game.action_space.sample()
        _, _, done,_,_ = game.step(action) 
    else:
        #wait for space bar to be pressed
        done = False
        game.reset()    


