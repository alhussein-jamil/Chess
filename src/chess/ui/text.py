"""Text layout helpers for Pygame panels."""

from __future__ import annotations

import pygame


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def measure_wrapped_text(
    font: pygame.font.Font,
    text: str,
    max_width: int,
    *,
    line_gap: int = 6,
) -> int:
    lines = wrap_text(font, text, max_width)
    if not lines:
        return 0

    total = 0
    for index, line in enumerate(lines):
        total += font.render(line, True, (255, 255, 255)).get_height()
        if index < len(lines) - 1:
            total += line_gap
    return total


def draw_wrapped_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    *,
    line_gap: int = 6,
) -> int:
    """Draw wrapped text inside rect. Returns total height used."""
    y = rect.y
    lines = wrap_text(font, text, rect.width)
    for index, line in enumerate(lines):
        rendered = font.render(line, True, color)
        surface.blit(rendered, (rect.x, y))
        y += rendered.get_height()
        if index < len(lines) - 1:
            y += line_gap
    return y - rect.y
