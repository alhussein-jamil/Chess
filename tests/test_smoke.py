"""Fast end-to-end checks without opening a game window."""

from __future__ import annotations

from copy import deepcopy

from chess.ai.minmax import MinMaxAgent
from chess.config import AppSettings
from chess.core.board import Board
from chess.core.piece import STARTING_PIECES
from chess.core.types import Color
from chess.paths import CONFIGS_DIR


def test_smoke_config_loads() -> None:
    settings = AppSettings.from_yaml(CONFIGS_DIR / "smoke.yaml")
    assert settings.ai.depth == 1
    assert settings.ai.color == Color.BLACK


def test_smoke_minimax_choose_move() -> None:
    settings = AppSettings.from_yaml(CONFIGS_DIR / "smoke.yaml")
    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.update()
    agent = MinMaxAgent(
        color=settings.ai.color,
        depth=settings.ai.depth,
        workers=settings.ai.workers,
    )
    move = agent.choose_move(board)
    assert move in MinMaxAgent.generate_possible_moves(board)


def test_invalid_ai_color_raises() -> None:
    try:
        AppSettings.from_yaml(overrides={"ai": {"color": "purple"}})
    except ValueError as exc:
        assert "ai.color" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid ai.color")
