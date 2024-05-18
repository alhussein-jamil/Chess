import datetime
import os
from pathlib import Path
import time
from contextlib import contextmanager
import yaml 

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

from src.env.rl.mono_agent_env import ChessEnvMono
from src.env.rl.multi_agent_env import ChessEnvMulti

ray.init(ignore_reinit_error=True, log_to_driver=False)

LOG_DIR = "ray_logs"
CHKPT_DIR = "ray_checkpoints"
EVAL_DIR = "ray_evals"
starting_epoch = 0


def custom_log_creator(custom_path, custom_str, run_config=None):
    if run_config is None:
        run_config = {}
    global starting_epoch
    # Identify the latest checkpoint and its corresponding log directory
    try:
        latest_run = max(
            [int(run.split("_")[1]) for run in os.listdir(CHKPT_DIR)], default=0
        )
        latest_epoch = max(
            [
                int(epoch.split("_")[1])
                for epoch in os.listdir(f"{CHKPT_DIR}/run_{latest_run}")
            ],
            default=-1,
        )
        if latest_epoch >= 0 and not run_config.get("clean_run", False):
            logdir = f"{CHKPT_DIR}/run_{latest_run}/epoch_{latest_epoch}"
            starting_epoch = latest_epoch + 1
        else:
            raise ValueError("No valid latest epoch found.")
    except Exception as e:
        print(f"Exception in finding latest checkpoint directory: {e}")
        timestr = datetime.datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        logdir_prefix = f"{custom_str}_{timestr}"
        logdir = Path(custom_path) / f"{logdir_prefix}_{timestr}"
        logdir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(logdir):
        Path(logdir).mkdir(parents=True, exist_ok=True)
    return lambda config: UnifiedLogger(config, str(logdir), loggers=None)


def env_creator(config, run_config=None):
    if run_config is None:
        run_config = {}
    return (
        ChessEnvMono(**config)
        if run_config.get("multi", False)
        else ChessEnvMulti(**config)
    )


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
    if isinstance(average_dt, list):
        average_dt_f = sum(average_dt) / len(average_dt)
    elif isinstance(average_dt, float):
        average_dt_f = average_dt

    size = frames[0].shape[0], frames[0].shape[1]
    codec_dict = {"avi": "DIVX", "mp4": "MP4V"}
    codec = cv2.VideoWriter.fourcc(*codec_dict[file_type])
    with video_writer(
        name + "." + file_type, codec, 1000.0 / average_dt_f, size
    ) as video:
        for frame in frames:
            video.write(frame)


@timer_wrapper
def add_audio(video_path: str, audio_path: str = "assets/move-self.wav") -> None:
    video = mpy.VideoFileClip(video_path)
    audio = mpy.AudioFileClip(audio_path)
    video: mpy.VideoFileClip = video.set_audio(audio)
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

    audio: mpy.AudioFileClip = mpy.concatenate_audioclips([audio] * n)
    audio.write_audiofile(output_path)


def evaluate(epoch, run, env_creator, algo, rollout_worker, run_config):
    print("Evaluating at epoch", epoch)
    Path("{}/run_{}".format(EVAL_DIR, run)).mkdir(parents=True, exist_ok=True)
    video_path = os.path.join("{}/run_{}/epoch_{}".format(EVAL_DIR, run, epoch))
    rollout_worker.set_weights(algo.get_weights())
    sample = rollout_worker.sample()
    dones_located = np.where(sample["White"]["dones"])[0]
    first_done, second_done = 0, len(sample["White"]["dones"])
    if len(dones_located) > 0:
        if len(dones_located) == 1:
            second_done = dones_located[0] + 1
        else: 
            first_done = dones_located[0] + 1
            second_done = dones_located[1] + 1
    print("Rendering from frame", first_done, "to", second_done)
    frames = []
    fps = run_config.get("fps", 2)
    env = env_creator({})
    for i in tqdm.tqdm(range(first_done, second_done), desc="Rendering", unit="frame"):
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


def main():
    last_render_time = 0.0
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
    starting_epoch = 0
    try:
        latest_run = max([int(run.split("_")[1]) for run in os.listdir(CHKPT_DIR)])
        latest_epoch = max(
            [
                int(epoch.split("_")[1])
                for epoch in os.listdir(f"{CHKPT_DIR}/run_{latest_run}")
            ]
        )
        latest_log_dir = f"{CHKPT_DIR}/run_{latest_run}/epoch_{latest_epoch}"
    except Exception as e:
        latest_log_dir = None
        print(f"Exception in finding latest checkpoint directory: {e}")

    print("Latest log dir:", latest_log_dir)

    debugging_config["logger_creator"] = custom_log_creator(
        custom_path=f"./{LOG_DIR}", custom_str="ppo_chess", run_config=run_config
    )
    burner_env = env_creator({}, run_config=run_config)

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

    if not run_config.get("clean_run", False) and latest_log_dir is not None:
        try:
            algo.restore(checkpoint_path=latest_log_dir)
            print("Restored from checkpoint:", latest_log_dir)
        except Exception:
            print("No checkpoint found, starting from scratch")

    Path(EVAL_DIR).mkdir(parents=True, exist_ok=True)
    runs = os.listdir(EVAL_DIR)
    runs = [int(run.split("_")[1]) for run in runs]
    runs = sorted(runs)
    run = runs[-1] + 1 if runs else 0

    total_epochs = 100000000

    render_freq = int(
        200
        * 16384
        / (training_config["train_batch_size"] * training_config["num_sgd_iter"])
    )
    save_freq = int(
        100
        * 16384
        / (training_config["train_batch_size"] * training_config["num_sgd_iter"])
    )

    print(f"Rendering every {render_freq} iterations")
    print(f"Saving every {save_freq} iterations")

    for epoch in range(starting_epoch, total_epochs):
        if epoch % render_freq == 0 or time.time() - last_render_time > 1800:
            evaluate(
                epoch=epoch,
                run=run,
                env_creator=lambda config: env_creator(config, run_config=run_config),
                algo=algo,
                rollout_worker=rollout_worker,
                run_config=run_config,
            )
            last_render_time = time.time()

        result = algo.train()

        try:    
            # Assuming 'result' contains a 'loss' you want to display
            infos = {
                color: {k:float(v) for k,v in result["info"]["learner"][color]["learner_stats"].items()}
                for color in ["White", "Black"]
            }
        except:
            infos = {}
        # Use the 'progress_bar' object to set description
        print(f"Epoch {epoch}") 
        print(f"Stats: \n{yaml.dump(infos, allow_unicode=True)}")
        if epoch % save_freq == 0 and epoch > 0:
            checkpoint = algo.save(
                checkpoint_dir=f"./{CHKPT_DIR}/run_{run}/epoch_{epoch}/"
            )
            print(f"\nCheckpoint saved at {checkpoint}")

    print("Training complete")


if __name__ == "__main__":
    main()
