"""Render Vs AI preview frames for layout checks."""

from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chess.config import AppSettings  # noqa: E402
from chess.core.board import Board  # noqa: E402
from chess.core.piece import STARTING_PIECES  # noqa: E402
from chess.core.types import Color  # noqa: E402
from chess.layout import vs_ai_window_size  # noqa: E402
from chess.paths import ARTIFACTS_DIR  # noqa: E402
from chess.ui.scene import blit_scene, render_vs_ai_scene  # noqa: E402


def main() -> None:
    settings = AppSettings()
    square_size = settings.display.square_size
    window_w, window_h = vs_ai_window_size(square_size)

    pygame.init()
    pygame.display.set_mode((window_w, window_h))

    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.update()
    board.turn = Color.BLACK

    layers, layout = render_vs_ai_scene(
        board,
        square_size,
        ai_thinking=True,
        think_frame=1,
        ai_depth=settings.ai.depth,
    )
    screen = pygame.Surface((window_w, window_h))
    blit_scene(screen, layers, layout)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS_DIR / "vs_ai_preview.png"
    board_out = ARTIFACTS_DIR / "vs_ai_board_layer.png"
    overlay_out = ARTIFACTS_DIR / "vs_ai_overlay_layer.png"
    pygame.image.save(screen, out.as_posix())
    pygame.image.save(layers.board, board_out.as_posix())
    pygame.image.save(layers.overlay, overlay_out.as_posix())
    print(out.relative_to(ROOT))
    print(board_out.relative_to(ROOT))
    print(overlay_out.relative_to(ROOT))
    pygame.quit()


if __name__ == "__main__":
    main()
