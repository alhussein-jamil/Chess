"""Project path constants."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = ROOT_DIR / "assets"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
RUNS_DIR = ARTIFACTS_DIR / "runs"
CONFIGS_DIR = ROOT_DIR / "configs"
DEFAULT_CONFIG = CONFIGS_DIR / "default.yaml"
