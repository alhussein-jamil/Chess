from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from env import ChessEnv

# Assuming you've already defined the Chess environment (ChessEnv)

def train_rl_agents(env, n_steps=10000):
    # Create two instances of the Chess environment
    env_black = DummyVecEnv([lambda: env])
    env_white = DummyVecEnv([lambda: env])

    # Initialize RL agents (using PPO for demonstration)
    model_black = PPO("MlpPolicy", env_black, verbose=1)
    model_white = PPO("MlpPolicy", env_white, verbose=1)

    # Train agents
    model_black.learn(total_timesteps=n_steps)
    model_white.learn(total_timesteps=n_steps)

    return model_black, model_white

def evaluate_agents(env, model_black, model_white, n_episodes=10):
    for _ in range(n_episodes):
        obs_black = env.reset()
        obs_white = env.reset()

        done = False
        while not done:
            # Black's turn
            action_black, _ = model_black.predict(obs_black)
            obs_black, _, done, _ = env.step(action_black)

            if done:
                break

            # White's turn
            action_white, _ = model_white.predict(obs_white)
            obs_white, _, done, _ = env.step(action_white)

# Initialize Chess environment
env = ChessEnv(dim_x=8, dim_y=8, render_mode ="rgb_array")

# Train RL agents
model_black, model_white = train_rl_agents(env)

# Evaluate trained agents
evaluate_agents(env, model_black, model_white)
