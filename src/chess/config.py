"""YAML-backed application settings."""

from __future__ import annotations

import dataclasses as dc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from chess.core.types import AI_COLORS, PROMOTION_TYPES, Color, PieceType
from chess.paths import DEFAULT_CONFIG


def _parse_color(value: str) -> Color:
    match value.lower():
        case "white":
            return Color.WHITE
        case "black":
            return Color.BLACK
        case _:
            raise ValueError(f"ai.color must be one of {sorted(AI_COLORS)}, got {value!r}")


def _parse_promotion(value: str) -> PieceType:
    match value.lower():
        case "queen":
            return PieceType.QUEEN
        case "rook":
            return PieceType.ROOK
        case "bishop":
            return PieceType.BISHOP
        case "knight":
            return PieceType.KNIGHT
        case _:
            raise ValueError(
                f"game.promotion must be one of {sorted(PROMOTION_TYPES)}, got {value!r}"
            )


@dataclass(frozen=True)
class DisplaySettings:
    square_size: int = 100
    sandbox_width: int = 1050
    sandbox_height: int = 850
    vs_ai_width: int = 850
    vs_ai_height: int = 900

    def __post_init__(self) -> None:
        if self.square_size < 40 or self.square_size > 200:
            raise ValueError(f"display.square_size must be 40–200, got {self.square_size}")


@dataclass(frozen=True)
class AISettings:
    depth: int = 3
    color: Color = Color.BLACK
    max_n_samples: int | None = None
    workers: int = 0

    def __post_init__(self) -> None:
        if self.depth < 1 or self.depth > 8:
            raise ValueError(f"ai.depth must be 1–8, got {self.depth}")
        if self.max_n_samples is not None and self.max_n_samples < 1:
            raise ValueError(f"ai.max_n_samples must be >= 1, got {self.max_n_samples}")
        if self.workers < 0 or self.workers > 32:
            raise ValueError(f"ai.workers must be 0–32, got {self.workers}")


@dataclass(frozen=True)
class GameSettings:
    promotion: PieceType = PieceType.QUEEN


@dataclass(frozen=True)
class AppSettings:
    display: DisplaySettings = DisplaySettings()
    ai: AISettings = AISettings()
    game: GameSettings = GameSettings()

    def with_updates(self, **kwargs: Any) -> AppSettings:
        return dc.replace(self, **kwargs)

    @classmethod
    def from_yaml(
        cls,
        path: Path | str = DEFAULT_CONFIG,
        overrides: dict[str, Any] | None = None,
    ) -> AppSettings:
        config_path = Path(path)
        data: dict[str, Any] = {}
        if config_path.exists():
            with config_path.open(encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
                if loaded:
                    data = loaded

        if overrides:
            data = _deep_merge(data, dict(overrides))

        display = _display_settings(data)
        ai_raw = _section(data, "ai", {})
        game_raw = _section(data, "game", {})

        ai = AISettings(
            depth=int(ai_raw.get("depth", 3)),
            color=_parse_color(str(ai_raw.get("color", "black"))),
            max_n_samples=ai_raw.get("max_n_samples"),
            workers=int(ai_raw.get("workers", 0)),
        )
        game = GameSettings(
            promotion=_parse_promotion(str(game_raw.get("promotion", "queen"))),
        )

        return cls(display=display, ai=ai, game=game)


def _display_settings(data: dict[str, Any]) -> DisplaySettings:
    raw = data.get("display") or {}
    if not isinstance(raw, dict):
        raise ValueError("display must be a mapping")
    return DisplaySettings(**{**dc.asdict(DisplaySettings()), **raw})


def _section(data: dict[str, Any], key: str, default: Any) -> Any:
    value = data.get(key, default)
    return default if value is None else value


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
