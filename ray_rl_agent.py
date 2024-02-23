import ray.rllib
from ray.rllib.algorithms.ppo import PPOConfig
from ray.tune.logger import pretty_print
import yaml
from multienv import ChessEnvMulti
import os 
import numpy as np
from contextlib import contextmanager
import os
import time

import cv2
import numpy as np
from pygame import surfarray
import datetime
import tempfile
from ray.tune.logger import UnifiedLogger
def custom_log_creator(custom_path, custom_str):

    timestr = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
    logdir_prefix = "{}_{}".format(custom_str, timestr)

    def logger_creator(config):

        if not os.path.exists(custom_path):
            os.makedirs(custom_path)
        logdir = tempfile.mkdtemp(prefix=logdir_prefix, dir=custom_path)
        return UnifiedLogger(config, logdir, loggers=None)

    return logger_creator


configs = yaml.safe_load(open("./config.yaml"))["training"]
environment_config = configs.get("environment", {})
training_config = configs.get("training", {})
rollout_config = configs.get("rollout", {})
framework_config = configs.get("framework", {})
resources_config = configs.get("resources", {})
debugging_config = configs.get("debugging", {})

debugging_config["logger_creator"] = custom_log_creator("./ray_logs", "ppo_chess")
 
ray.init(ignore_reinit_error=True, log_to_driver=False)


algo = (
    PPOConfig()
    .environment(**environment_config)
    .training(**training_config)
    .rollouts(**rollout_config)
    .framework(**framework_config)
    .resources(**resources_config)
    .debugging(**debugging_config)
).build()




def pg_to_cv2(cvarray:np.ndarray)->np.ndarray:
    cvarray = cvarray.swapaxes(0,1) #rotate
    cvarray = cv2.cvtColor(cvarray, cv2.COLOR_RGB2BGR) #RGB to BGR
    return cvarray

def timer_wrapper(func):
    def inner(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        #print("Finished:" ,func.__name__ ,end-start)
        return end - start
    return inner

@contextmanager
def video_writer(*args,**kwargs):
    video = cv2.VideoWriter(*args,**kwargs)
    try:
        yield video
    finally:
        video.release()

@timer_wrapper
def save_frames(frames: list, average_dt: float|list, file_type: str = "mp4", name: str = "screen_recording"):
    if type(average_dt) is list: average_dt = sum(average_dt)/len(average_dt) # force average_dt to be a float
    size = frames[0].get_size()
    codec_dict={
        "avi":'DIVX',
        "mp4":'MP4V'
    }
    codec = cv2.VideoWriter_fourcc(*codec_dict[file_type])
    with video_writer(name+"."+file_type, codec, 1000/average_dt, size) as video: # file_name, codec, average_fps, dimensions
        for frame in frames:
            try:
                pg_frame = surfarray.pixels3d(frame) # convert the surface to a np array. Only works with depth 24 or 32, not less
            except:
                pg_frame = surfarray.array3d(frame) # convert the surface to a np array. Works with any depth
            cv_frame = pg_to_cv2(pg_frame)  # then convert the np array so it is compatible with opencv
            video.write(cv_frame)   #write the frame to the video using opencv



def evaluate(trainer, env, epoch, run):
    print("Evaluating at epoch", epoch)
    os.makedirs("test_dir/run_{}".format(run), exist_ok=True)
    # Make a steps counter
    steps = 0
    # Run test
    video_path = os.path.join(
        "test_dir/run_{}/epoch_{}".format(run,epoch)
    )
    filterfn = trainer.workers.local_worker().filters["default_policy"]
    env.reset()
    obs = env.reset()[0]
    done = False
    obs = obs["White"]
    frames = []
    fps = 2
    while not done:
        # Increment steps
        steps += 1
        obs = filterfn(obs)
        action = trainer.compute_single_action(obs)
        obs, _, done, _, _ = env._step(action)
        window_copy  = env.render().copy()
        frames.append(window_copy)   
    frame_num = len(frames)
    dts = [1000/fps]*frame_num
    args = (frames,dts,"mp4",video_path)
    save_frames(*args)
    print("Video saved at", video_path)

os.makedirs("test_dir", exist_ok=True)
runs = os.listdir("test_dir")
runs = [int(run.split("_")[1]) for run in runs]
runs = sorted(runs)
run = runs[-1] + 1 if runs else 0

for epoch in range(100000000):
    result = algo.train()
    print(pretty_print(result))
    if epoch % 1000 == 0:
        print("checkpoint saved at", algo.save())
    if epoch % 200 == 0:
        # # Evaluate the agent
        evaluate(algo, ChessEnvMulti(), epoch, run)       
