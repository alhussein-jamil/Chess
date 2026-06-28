"""Shared visual theme matching the README diagram assets."""

from __future__ import annotations

import pygame

from chess.ui.colors import BG, LINE, MONO_FONTS, PANEL, PANEL_2, TEAL, TEXT, UI_FONTS


def mono_font(size: int) -> pygame.font.Font:
    return pygame.font.SysFont(MONO_FONTS, size, bold=True)


def ui_font(size: int, *, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont(UI_FONTS, size, bold=bold)


def piece_font_size(square_size: int) -> int:
    return max(14, int(square_size * 0.36))


def fill_background(surface: pygame.Surface) -> None:
    surface.fill(BG)


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    accent: tuple[int, int, int] | None = None,
    fill: tuple[int, int, int] = PANEL_2,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, LINE, rect, width=1, border_radius=10)
    if accent is not None:
        pygame.draw.rect(surface, accent, (rect.x, rect.y, 8, rect.height))


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    *,
    accent: tuple[int, int, int] = TEAL,
    hovered: bool = False,
) -> None:
    fill = PANEL if hovered else (16, 25, 35)
    draw_panel(surface, rect, accent=accent, fill=fill)
    text = font.render(label, True, TEXT)
    surface.blit(
        text,
        (
            rect.centerx - text.get_width() // 2,
            rect.centery - text.get_height() // 2,
        ),
    )
