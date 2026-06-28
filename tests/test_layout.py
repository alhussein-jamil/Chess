"""Window layout size checks."""

from chess.layout import vs_ai_panel_x, vs_ai_window_size


def test_vs_ai_window_fits_board_coords_and_panel() -> None:
    width, height = vs_ai_window_size(100)
    assert width >= 800 + 250
    assert height >= 800 + 36
    assert vs_ai_panel_x(100) < width
