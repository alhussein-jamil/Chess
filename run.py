import datetime
import os
import tempfile
import time
from contextlib import contextmanager

import cv2
import moviepy.editor as mpy
import numpy as np
import pygame
import ray
import tqdm
import yaml
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.evaluation.rollout_worker import RolloutWorker
from ray.tune.logger import UnifiedLogger
from ray.tune.registry import register_env

from mono_agent_env import ChessEnvMono
from multi_agent_env import ChessEnvMulti

ray.init(ignore_reinit_error=True, log_to_driver=False)

LOG_DIR = "ray_logs"
CHKPT_DIR = "ray_checkpoints"
EVAL_DIR = "ray_evals"
# register the environment
register_env("ChessMultiAgent-v0", lambda config: ChessEnvMulti(**config))
register_env("ChessMonoAgent-v0", lambda config: ChessEnvMono(**config))


def custom_log_creator(custom_path, custom_str):
    timestr = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
    logdir_prefix = "{}_{}".format(custom_str, timestr)

    def logger_creator(config):
        if not os.path.exists(custom_path):
            os.makedirs(custom_path)
        logdir = tempfile.mkdtemp(prefix=logdir_prefix, dir=custom_path)
        return UnifiedLogger(config, logdir, loggers=None)

    return logger_creator


training_config = yaml.safe_load(open("./config.yaml"))["training"]
run_config = training_config["run"]

environment_config = training_config.get("environment", {})
if run_config.get("multi", True):
    environment_config["env"] = "ChessMultiAgent-v0"
else:
    environment_config["env"] = "ChessMonoAgent-v0"
training_config = training_config.get("training", {})
rollout_config = training_config.get("rollout", {})
framework_config = training_config.get("framework", {})
resources_config = training_config.get("resources", {})
debugging_config = training_config.get("debugging", {})
eval_config = training_config.get("evaluation", {})

try:
    latest_run = max([int(run.split("_")[1]) for run in os.listdir(CHKPT_DIR)])
    latest_epoch = max(
        [
            int(epoch.split("_")[1])
            for epoch in os.listdir(f"{CHKPT_DIR}/run_{latest_run}")
        ]
    )
    latest_log_dir = f"{CHKPT_DIR}/run_{latest_run}/epoch_{latest_epoch}"
except:
    latest_log_dir = None

print("Latest log dir:", latest_log_dir)

debugging_config["logger_creator"] = custom_log_creator(f"./{LOG_DIR}", "ppo_chess")
env_creator = lambda config: (
    ChessEnvMono(**config)
    if run_config.get("multi", False)
    else ChessEnvMulti(**config)
)
burner_env = env_creator({})


cfg = (
    PPOConfig()
    .environment(**environment_config)
    .training(**training_config)
    .rollouts(**rollout_config)
    .framework(**framework_config)
    .resources(**resources_config)
    .debugging(**debugging_config)
    .evaluation(**eval_config)
    .multi_agent(
        policies=["White", "Black"],
        policy_mapping_fn=(lambda agent_id, *args, **kwargs: agent_id),
    )
)
cfg["create_env_on_driver"] = True
cfg["create_env_on_local_worker"] = True


algo = cfg.build()

rollout_worker = RolloutWorker(
    env_creator=lambda *args, **kwargs: (
        ChessEnvMono(**kwargs)
        if run_config.get("multi", False)
        else ChessEnvMulti(**kwargs)
    ),
    spaces={
        "White": (burner_env.observation_space, burner_env.action_space),
        "Black": (burner_env.observation_space, burner_env.action_space),
    },
    config=cfg,
    default_policy_class=algo.get_default_policy_class(cfg),
)


if not run_config.get("clean_run", False):
    try:
        checkpoint_path = algo.restore(checkpoint_path=latest_log_dir)
        print("Restored from checkpoint:", latest_log_dir)
    except:
        print("No checkpoint found, starting from scratch")


def timer_wrapper(func):
    def inner(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        return end - start

    return inner


@contextmanager
def video_writer(*args, **kwargs):
    video = cv2.VideoWriter(*args, **kwargs)
    try:
        yield video
    finally:
        video.release()


@timer_wrapper
def save_frames(
    frames: list,
    average_dt: float | list,
    file_type: str = "mp4",
    name: str = "screen_recording",
):
    if type(average_dt) is list:
        average_dt = sum(average_dt) / len(average_dt)
    size = frames[0].shape[0], frames[0].shape[1]
    codec_dict = {"avi": "DIVX", "mp4": "MP4V"}
    codec = cv2.VideoWriter_fourcc(*codec_dict[file_type])
    with video_writer(name + "." + file_type, codec, 1000 / average_dt, size) as video:
        for frame in frames:
            video.write(frame)


@timer_wrapper
def add_audio(video_path: str, audio_path: str = "assets/move-self.wav") -> None:
    video = mpy.VideoFileClip(video_path)
    audio = mpy.AudioFileClip(audio_path)
    video = video.set_audio(audio)
    video.write_videofile(video_path[:-4] + "_evaluation.mp4")
    os.remove(video_path)


def repeat_audio(audio_path: str, n: int, output_path: str, fps: int = 2):
    audio = mpy.AudioFileClip(audio_path)
    if audio.duration < 1 / fps:
        audio = mpy.concatenate_audioclips(
            [audio, mpy.AudioClip(lambda t: 0, duration=1 / fps - audio.duration)]
        )
    else:
        audio = audio.subclip(0, 1 / fps)

    audio = mpy.concatenate_audioclips([audio] * n)
    audio.write_audiofile(output_path)


env_creator = lambda _: (
    ChessEnvMono() if run_config.get("multi", False) else ChessEnvMulti()
)


def evaluate(epoch, run, env_creator):
    print("Evaluating at epoch", epoch)
    os.makedirs("{}/run_{}".format(EVAL_DIR, run), exist_ok=True)
    video_path = os.path.join("{}/run_{}/epoch_{}".format(EVAL_DIR, run, epoch))
    rollout_worker.set_weights(algo.get_weights())
    sample = rollout_worker.sample()
    first_done = np.where(sample["White"]["dones"] == True)[0][0] + 1
    print(np.where(sample["White"]["dones"] == True)[0])
    frames = []
    fps = run_config.get("fps", 2)
    env = env_creator({})
    for i in tqdm.tqdm(range(first_done), desc="Rendering", unit="frame"):
        for pygame_event in pygame.event.get():
            if pygame_event.type == pygame.QUIT:
                pygame.quit()
                exit()
        frames.append(env.render_from_observation(sample["White"]["obs"][i]))
    frame_num = len(frames)
    dts = [1000 / fps] * frame_num
    args = (frames, dts, "mp4", video_path)
    repeat_audio("assets/move-self.wav", frame_num, video_path + ".wav", fps)
    save_frames(*args)
    add_audio(video_path + ".mp4", video_path + ".wav")
    os.remove(video_path + ".wav")
    print("Video saved at", video_path)
    pygame.quit()


os.makedirs(EVAL_DIR, exist_ok=True)
runs = os.listdir(EVAL_DIR)
runs = [int(run.split("_")[1]) for run in runs]
runs = sorted(runs)
run = runs[-1] + 1 if runs else 0

total_epochs = 100000000

progress_bar = tqdm.tqdm(range(total_epochs), desc="Training Progress", unit="epoch")
for epoch in progress_bar:
    result = algo.train()

    # Assuming 'result' contains a 'loss' you want to display
    loss = result.get("loss", 0)

    # Use the 'progress_bar' object to set description
    progress_bar.set_description(f"Epoch {epoch} Loss: {loss:.4f}")

    if epoch % 200 == 0:
        evaluate(epoch, run, env_creator)

    if epoch % 100 == 0 and epoch > 0:
        checkpoint = algo.save(checkpoint_dir=f"./{CHKPT_DIR}/run_{run}/epoch_{epoch}/")
        print(f"\nCheckpoint saved at {checkpoint}")