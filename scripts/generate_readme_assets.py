"""Generate deterministic SVG figures for the README."""

from __future__ import annotations

import sys
from pathlib import Path

# ruff: noqa: E501

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chess.core.types import Color  # noqa: E402
from chess.ui.colors import (  # noqa: E402
    BG,
    BLUE,
    BOARD_BORDER,
    BOARD_FRAME,
    CORAL,
    DARK_SQUARE,
    GOLD,
    GREEN,
    LIGHT_SQUARE,
    LINE,
    MUTED,
    PANEL,
    PANEL_2,
    PIECE_COLOR,
    TEAL,
    TEXT,
    VIOLET,
    rgb_hex,
)

ASSET_DIR = ROOT / "docs" / "assets"


def _hex(color: tuple[int, int, int]) -> str:
    return rgb_hex(color)


BG_HEX = _hex(BG)
PANEL_HEX = _hex(PANEL)
PANEL_2_HEX = _hex(PANEL_2)
TEXT_HEX = _hex(TEXT)
MUTED_HEX = _hex(MUTED)
LINE_HEX = _hex(LINE)
TEAL_HEX = _hex(TEAL)
GOLD_HEX = _hex(GOLD)
CORAL_HEX = _hex(CORAL)
GREEN_HEX = _hex(GREEN)
BLUE_HEX = _hex(BLUE)
VIOLET_HEX = _hex(VIOLET)
LIGHT_SQUARE_HEX = _hex(LIGHT_SQUARE)
DARK_SQUARE_HEX = _hex(DARK_SQUARE)
BOARD_FRAME_HEX = _hex(BOARD_FRAME)
BOARD_BORDER_HEX = _hex(BOARD_BORDER)
PIECE_BLACK_HEX = _hex(PIECE_COLOR[Color.BLACK])
PIECE_WHITE_HEX = _hex(PIECE_COLOR[Color.WHITE])


def write_svg(name: str, body: str, width: int = 1280, height: int = 640) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSET_DIR / name
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{BG_HEX}"/>
      <stop offset="54%" stop-color="#121b26"/>
      <stop offset="100%" stop-color="#15151e"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#05070a" flood-opacity="0.38"/>
    </filter>
    <marker id="arrow-teal" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{TEAL_HEX}"/>
    </marker>
    <marker id="arrow-gold" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{GOLD_HEX}"/>
    </marker>
    <marker id="arrow-coral" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="{CORAL_HEX}"/>
    </marker>
    <style>
      .title {{ font: 700 34px Inter, ui-sans-serif, system-ui, sans-serif; fill: {TEXT_HEX}; }}
      .subtitle {{ font: 500 17px Inter, ui-sans-serif, system-ui, sans-serif; fill: {MUTED_HEX}; }}
      .label {{ font: 700 18px Inter, ui-sans-serif, system-ui, sans-serif; fill: {TEXT_HEX}; }}
      .small {{ font: 600 14px Inter, ui-sans-serif, system-ui, sans-serif; fill: {MUTED_HEX}; }}
      .tiny {{ font: 600 12px Inter, ui-sans-serif, system-ui, sans-serif; fill: {MUTED_HEX}; }}
      .mono {{ font: 700 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: {TEXT_HEX}; }}
      .panel {{ fill: {PANEL_HEX}; stroke: {LINE_HEX}; stroke-width: 1.2; filter: url(#shadow); }}
      .panel2 {{ fill: {PANEL_2_HEX}; stroke: #3a4b61; stroke-width: 1.1; }}
      .wire {{ fill: none; stroke-linecap: round; stroke-linejoin: round; }}
    </style>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
{body}
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    print(path.relative_to(ROOT))


def card(x: int, y: int, w: int, h: int, title: str, detail: str, color: str) -> str:
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="panel2"/>
  <rect x="{x}" y="{y}" width="8" height="{h}" rx="4" fill="{color}"/>
  <text x="{x + 24}" y="{y + 32}" class="label">{title}</text>
  <text x="{x + 24}" y="{y + 58}" class="small">{detail}</text>"""


def mini_board(x: int, y: int, square: int, *, arrow: bool = False) -> str:
    cells: list[str] = []
    for row in range(8):
        for col in range(8):
            fill = LIGHT_SQUARE_HEX if (row + col) % 2 == 0 else DARK_SQUARE_HEX
            cells.append(
                f'<rect x="{x + col * square}" y="{y + row * square}" '
                f'width="{square}" height="{square}" fill="{fill}"/>'
            )

    pieces = [
        ("R", 0, 0, PIECE_BLACK_HEX),
        ("N", 1, 0, PIECE_BLACK_HEX),
        ("B", 2, 0, PIECE_BLACK_HEX),
        ("Q", 3, 0, PIECE_BLACK_HEX),
        ("K", 4, 0, PIECE_BLACK_HEX),
        ("B", 5, 0, PIECE_BLACK_HEX),
        ("N", 6, 0, PIECE_BLACK_HEX),
        ("R", 7, 0, PIECE_BLACK_HEX),
        ("P", 4, 3, PIECE_BLACK_HEX),
        ("P", 4, 4, PIECE_WHITE_HEX),
        ("B", 2, 5, PIECE_WHITE_HEX),
        ("N", 5, 5, PIECE_WHITE_HEX),
        ("P", 0, 6, PIECE_WHITE_HEX),
        ("P", 1, 6, PIECE_WHITE_HEX),
        ("P", 2, 6, PIECE_WHITE_HEX),
        ("P", 5, 6, PIECE_WHITE_HEX),
        ("P", 6, 6, PIECE_WHITE_HEX),
        ("P", 7, 6, PIECE_WHITE_HEX),
        ("R", 0, 7, PIECE_WHITE_HEX),
        ("N", 1, 7, PIECE_WHITE_HEX),
        ("B", 2, 7, PIECE_WHITE_HEX),
        ("Q", 3, 7, PIECE_WHITE_HEX),
        ("K", 4, 7, PIECE_WHITE_HEX),
        ("B", 5, 7, PIECE_WHITE_HEX),
        ("R", 7, 7, PIECE_WHITE_HEX),
    ]
    marks = []
    piece_size = min(13, max(8, square - 7))
    for label, col, row, fill in pieces:
        cx = x + col * square + square / 2
        cy = y + row * square + square / 2 + piece_size * 0.38
        marks.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'style="fill: {fill}; font: 700 {piece_size}px ui-monospace, '
            'SFMono-Regular, Menlo, Consolas, monospace;">'
            f"{label}</text>"
        )

    overlay = ""
    if arrow:
        start_x = x + 4 * square + square / 2
        start_y = y + 6 * square + square / 2
        end_y = y + 4 * square + square / 2
        overlay = f"""
  <rect x="{x + 4 * square}" y="{y + 4 * square}" width="{square}" height="{square}"
        fill="{GOLD_HEX}" opacity="0.35"/>
  <path d="M {start_x:.1f} {start_y:.1f} L {start_x:.1f} {end_y:.1f}"
        class="wire" stroke="{GOLD_HEX}" stroke-width="5" marker-end="url(#arrow-gold)"/>"""

    board_cells = "\n    ".join(cells)
    piece_marks = "\n    ".join(marks)

    return f"""
  <g>
    <rect x="{x - 8}" y="{y - 8}" width="{square * 8 + 16}" height="{square * 8 + 16}"
          rx="12" fill="{BOARD_FRAME_HEX}" stroke="{BOARD_BORDER_HEX}"/>
    {board_cells}
    {piece_marks}
    {overlay}
  </g>"""


def interface_modes() -> None:
    body = f"""
  <title>Chess project interface modes</title>
  <text x="56" y="66" class="title">Interactive chess modes</text>
  <text x="56" y="98" class="subtitle">The package exposes a free-play sandbox and a human-vs-minimax mode through the same YAML-backed CLI.</text>

  <rect x="58" y="148" width="288" height="344" rx="16" class="panel"/>
  <text x="88" y="190" class="label">CLI entrypoint</text>
  <text x="88" y="222" class="mono">chess play</text>
  <text x="88" y="250" class="mono">chess play-ai --depth 4</text>
  <text x="88" y="298" class="small">Config: configs/default.yaml</text>
  <text x="88" y="322" class="small">Depth flag adjusts search.</text>
  <text x="88" y="370" class="small">Rich logs show runtime state.</text>
  <rect x="86" y="408" width="232" height="40" rx="8" fill="#101923" stroke="{TEAL_HEX}"/>
  <text x="202" y="434" text-anchor="middle" class="mono">src/chess/cli.py</text>

  <path d="M 346 260 L 424 260" class="wire" stroke="{TEAL_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 346 380 L 424 380" class="wire" stroke="{GOLD_HEX}" stroke-width="3" marker-end="url(#arrow-gold)"/>

  <rect x="426" y="134" width="754" height="390" rx="18" class="panel"/>
  {mini_board(458, 170, 36, arrow=True)}

  <rect x="786" y="170" width="354" height="144" rx="14" fill="#111a24" stroke="{TEAL_HEX}"/>
  <text x="814" y="204" class="label">Sandbox</text>
  <text x="814" y="232" class="small">Drag pieces on the board.</text>
  <text x="814" y="256" class="small">Add any piece from the panel.</text>
  <text x="814" y="280" class="small">Toggle new-piece color from the side panel.</text>

  <rect x="786" y="344" width="354" height="132" rx="14" fill="#141a22" stroke="{GOLD_HEX}"/>
  <text x="814" y="378" class="label">Vs AI</text>
  <text x="814" y="406" class="small">You play White; AI is Black.</text>
  <text x="814" y="430" class="small">Search runs in a worker thread.</text>
  <text x="814" y="454" class="small">Layout derives from square_size.</text>

  <rect x="98" y="540" width="1032" height="54" rx="14" fill="#101923" stroke="#34475b"/>
  <text x="128" y="574" class="small">Core constants: 8 x 8 board, committed piece PNGs, configurable square size from 40 to 200 pixels.</text>
"""
    write_svg("interface-modes.svg", body)


def move_flow() -> None:
    steps = [
        (68, 180, 214, 82, "Mouse down", "record drag_origin", TEAL_HEX),
        (332, 180, 214, 82, "Drag piece", "remove from board map", BLUE_HEX),
        (596, 180, 214, 82, "Mouse up", "convert pixels to grid", GOLD_HEX),
        (860, 180, 214, 82, "Legal target?", "simulate if needed", CORAL_HEX),
        (332, 376, 214, 82, "move_piece", "capture, promote, castle", GREEN_HEX),
        (596, 376, 214, 82, "board.update", "moves, checks, danger", VIOLET_HEX),
        (860, 376, 214, 82, "Next state", "turn or restore piece", TEAL_HEX),
    ]
    body = f"""
  <title>Drag-and-drop move handling flow</title>
  <text x="56" y="66" class="title">Drag-and-drop move handling</text>
  <text x="56" y="98" class="subtitle">Mouse input stays lightweight while the board object owns legality, captures, promotion, castling, checks, and turn changes.</text>

  {"".join(card(*step) for step in steps)}
  <path d="M 282 221 L 332 221" class="wire" stroke="{TEAL_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 546 221 L 596 221" class="wire" stroke="{BLUE_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 810 221 L 860 221" class="wire" stroke="{GOLD_HEX}" stroke-width="3" marker-end="url(#arrow-gold)"/>
  <path d="M 967 262 C 967 330, 439 330, 439 376" class="wire" stroke="{GREEN_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 546 417 L 596 417" class="wire" stroke="{GREEN_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 810 417 L 860 417" class="wire" stroke="{VIOLET_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 1074 221 C 1120 221, 1120 468, 1074 468" class="wire" stroke="{CORAL_HEX}" stroke-width="3" stroke-dasharray="9 8" marker-end="url(#arrow-coral)"/>

  <rect x="78" y="324" width="184" height="174" rx="16" class="panel"/>
  {mini_board(112, 354, 15, arrow=True)}
  <text x="170" y="542" text-anchor="middle" class="mono">e2 -&gt; e4</text>

  <rect x="82" y="548" width="1058" height="48" rx="14" fill="#101923" stroke="#34475b"/>
  <text x="112" y="579" class="small">Illegal drops call _restore_dragged_piece; legal moves switch turn and update checkmate, stalemate, and draw state.</text>
"""
    write_svg("move-flow.svg", body)


def search_tree() -> str:
    nodes = [
        (640, 178, 26, TEAL_HEX, "root"),
        (434, 288, 22, GOLD_HEX, "A"),
        (640, 288, 22, GOLD_HEX, "B"),
        (846, 288, 22, GOLD_HEX, "C"),
        (336, 400, 18, GREEN_HEX, "+1.4"),
        (432, 400, 18, GREEN_HEX, "+0.7"),
        (528, 400, 18, CORAL_HEX, "cut"),
        (626, 400, 18, GREEN_HEX, "+2.1"),
        (724, 400, 18, GREEN_HEX, "+1.8"),
        (820, 400, 18, CORAL_HEX, "cut"),
        (916, 400, 18, GREEN_HEX, "-0.2"),
    ]
    links = [
        (640, 204, 434, 266, TEAL_HEX, False),
        (640, 204, 640, 266, TEAL_HEX, False),
        (640, 204, 846, 266, TEAL_HEX, False),
        (434, 310, 336, 382, GOLD_HEX, False),
        (434, 310, 432, 382, GOLD_HEX, False),
        (434, 310, 528, 382, CORAL_HEX, True),
        (640, 310, 626, 382, GOLD_HEX, False),
        (640, 310, 724, 382, GOLD_HEX, False),
        (846, 310, 820, 382, CORAL_HEX, True),
        (846, 310, 916, 382, GOLD_HEX, False),
    ]

    link_svg = []
    for x1, y1, x2, y2, color, dashed in links:
        dash = ' stroke-dasharray="8 8"' if dashed else ""
        link_svg.append(
            f'<path d="M {x1} {y1} L {x2} {y2}" class="wire" '
            f'stroke="{color}" stroke-width="2.6"{dash}/>'
        )

    node_svg = []
    for x, y, r, color, label in nodes:
        node_svg.append(
            f"""
  <circle cx="{x}" cy="{y}" r="{r}" fill="#111a24" stroke="{color}" stroke-width="3"/>
  <text x="{x}" y="{y + 5}" text-anchor="middle" class="tiny">{label}</text>"""
        )
    return "".join(link_svg + node_svg)


def minimax_flow() -> None:
    body = f"""
  <title>Minimax alpha-beta search flow</title>
  <text x="56" y="66" class="title">Minimax with alpha-beta pruning</text>
  <text x="56" y="98" class="subtitle">The AI evaluates legal move trees from a copied board, sorts captures first, and stops exploring branches once alpha and beta cross.</text>

  <rect x="58" y="150" width="288" height="352" rx="16" class="panel"/>
  <text x="88" y="190" class="label">Move generation</text>
  <text x="88" y="222" class="small">board.update()</text>
  <text x="88" y="248" class="small">iterate pieces for board.turn</text>
  <text x="88" y="274" class="small">simulate legal moves</text>
  <text x="88" y="324" class="label">Evaluation</text>
  <text x="88" y="356" class="small">material value</text>
  <text x="88" y="382" class="small">0.05 * legal move count</text>
  <text x="88" y="408" class="small">check and terminal scores</text>
  <rect x="86" y="444" width="232" height="36" rx="8" fill="#101923" stroke="{TEAL_HEX}"/>
  <text x="202" y="467" text-anchor="middle" class="mono">MinMaxAgent</text>

  <rect x="390" y="134" width="566" height="390" rx="18" class="panel"/>
  {search_tree()}
  <text x="640" y="484" text-anchor="middle" class="small">Capture-first ordering improves pruning opportunities.</text>

  <rect x="994" y="150" width="218" height="352" rx="16" class="panel"/>
  <text x="1024" y="190" class="label">Runtime path</text>
  <text x="1024" y="222" class="small">copy_ai snapshot</text>
  <text x="1024" y="248" class="small">background thread</text>
  <text x="1024" y="274" class="small">choose_move()</text>
  <text x="1024" y="300" class="small">apply_move()</text>
  <path d="M 1030 354 L 1180 354" class="wire" stroke="{TEAL_HEX}" stroke-width="6"/>
  <path d="M 1030 392 L 1140 392" class="wire" stroke="{GOLD_HEX}" stroke-width="6"/>
  <path d="M 1030 430 L 1078 430" class="wire" stroke="{CORAL_HEX}" stroke-width="6"/>
  <text x="1024" y="468" class="tiny">Depth is config-driven.</text>
  <text x="1024" y="488" class="tiny">Validation caps range.</text>

  <path d="M 346 326 L 390 326" class="wire" stroke="{TEAL_HEX}" stroke-width="3" marker-end="url(#arrow-teal)"/>
  <path d="M 956 326 L 994 326" class="wire" stroke="{GOLD_HEX}" stroke-width="3" marker-end="url(#arrow-gold)"/>
  <rect x="92" y="548" width="1070" height="48" rx="14" fill="#101923" stroke="#34475b"/>
  <text x="122" y="579" class="small">Terminal boards use +/-100000 checkmate scores; draws and stalemates evaluate to 0.</text>
"""
    write_svg("minimax-search.svg", body)


def main() -> None:
    interface_modes()
    move_flow()
    minimax_flow()


if __name__ == "__main__":
    main()
