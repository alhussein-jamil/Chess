from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from env import ChessEnv
import gymnasium as gym 

import numpy as np

from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from torch import nn as nn

# class TensorboardCallback(BaseCallback):
#     """
#     Custom callback for plotting additional values in tensorboard.
#     """

#     def __init__(self, verbose=0):
#         super().__init__(verbose)

#     def _on_step(self) -> bool:
#         # Log scalar value (here a random variable)
#         #log the reward
#         reward = np.mean(self.locals["rewards"])
#         self.logger.record("reward", reward)
#         return True


env_maker = lambda: gym.make("Chess-v0", dim_x=8, dim_y=8, render_mode="rgb_array")
envs = make_vec_env(env_maker, n_envs=256)
model = PPO("MlpPolicy", envs, verbose=1, tensorboard_log="./ppo_chess_tensorboard/", n_steps = 10,policy_kwargs=dict(
    net_arch=[256, 256, 256, 256],
    activation_fn = nn.SiLU
)
)
model.learn(total_timesteps=1000000,progress_bar=True)#,callback=TensorboardCallback())
model.save("./rl_model")
model.load("./rl_model")
#evaluate the model 
game = gym.make("Chess-v0", dim_x=8, dim_y=8, render_mode="human")
obs,_  = game.reset()
done = False
while not done:
    action, _ = model.predict(obs)
    obs, _, done, _,_ = game.step(action)
    game.render()
game.close()

