"""Fast numpy board state for rules, simulation, and AI search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from chess.core.types import Color, PieceType
from chess.core.zobrist import ZOBRIST_PIECES, ZOBRIST_TURN, square_index

if TYPE_CHECKING:
    from chess.core.board import Board

Move4 = tuple[int, int, int, int]

PAWN = PieceType.PAWN.value
ROOK = PieceType.ROOK.value
KNIGHT = PieceType.KNIGHT.value
BISHOP = PieceType.BISHOP.value
QUEEN = PieceType.QUEEN.value
KING = PieceType.KING.value

PIECE_VALUES = {
    PAWN: 1,
    KNIGHT: 3,
    BISHOP: 3,
    ROOK: 5,
    QUEEN: 9,
    KING: 100,
}

WHITE_K_CASTLE = 1
WHITE_Q_CASTLE = 2
BLACK_K_CASTLE = 4
BLACK_Q_CASTLE = 8

KNIGHT_DELTAS = ((2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2))
KING_DELTAS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
ORTHO_DELTAS = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG_DELTAS = ((1, 1), (1, -1), (-1, 1), (-1, -1))

MATE_SCORE = 100_000.0


@dataclass
class _Undo:
    fx: int
    fy: int
    tx: int
    ty: int
    captured: int
    moved_piece: int
    castling: int
    wkx: int
    wky: int
    bkx: int
    bky: int
    halfmove: int
    hash_: int
    turn: int


@dataclass
class _Probe:
    wkx: int
    wky: int
    bkx: int
    bky: int
    rook_fy: int
    rook_from: int
    rook_to: int
    rook_val: int
    had_rook: bool
    moved: int
    captured: int
    fx: int
    fy: int
    tx: int
    ty: int


def _zobrist_piece(x: int, y: int, value: int) -> int:
    if value == 0:
        return 0
    color = Color.WHITE if value > 0 else Color.BLACK
    piece_type = PieceType(abs(value))
    idx = square_index(x, y)
    return ZOBRIST_PIECES[idx][color.value - 1][piece_type.value - 1]


class BoardState:
    """8x8 int8 grid: positive = white, negative = black; magnitude = piece type."""

    __slots__ = (
        "grid",
        "turn",
        "wkx",
        "wky",
        "bkx",
        "bky",
        "castling",
        "halfmove",
        "hash_",
        "_undo_stack",
    )

    def __init__(self) -> None:
        self.grid = np.zeros((8, 8), dtype=np.int8)
        self.turn = 0  # 0 = white, 1 = black
        self.wkx, self.wky = 4, 7
        self.bkx, self.bky = 4, 0
        self.castling = WHITE_K_CASTLE | WHITE_Q_CASTLE | BLACK_K_CASTLE | BLACK_Q_CASTLE
        self.halfmove = 0
        self.hash_ = 0
        self._undo_stack: list[_Undo] = []

    @classmethod
    def from_board(cls, board: Board) -> BoardState:
        state = cls()
        for piece in board.pieces[Color.WHITE] + board.pieces[Color.BLACK]:
            v = piece.piece_type.value
            if piece.color == Color.BLACK:
                v = -v
            state.grid[piece.position.y, piece.position.x] = v
            if abs(v) == KING:
                if v > 0:
                    state.wkx, state.wky = piece.position.x, piece.position.y
                else:
                    state.bkx, state.bky = piece.position.x, piece.position.y

        state.turn = 0 if board.turn == Color.WHITE else 1
        state.halfmove = board.moves_without_capture
        state.castling = 0

        from chess.core.piece import Position

        for color, y in ((Color.WHITE, 7), (Color.BLACK, 0)):
            king = board.kings.get(color)
            if king is not None and king.moved == 0:
                rook_h = board.get(Position(7, y))
                rook_a = board.get(Position(0, y))
                if color == Color.WHITE:
                    if rook_h.piece_type == PieceType.ROOK and rook_h.moved == 0:
                        state.castling |= WHITE_K_CASTLE
                    if rook_a.piece_type == PieceType.ROOK and rook_a.moved == 0:
                        state.castling |= WHITE_Q_CASTLE
                else:
                    if rook_h.piece_type == PieceType.ROOK and rook_h.moved == 0:
                        state.castling |= BLACK_K_CASTLE
                    if rook_a.piece_type == PieceType.ROOK and rook_a.moved == 0:
                        state.castling |= BLACK_Q_CASTLE

        state._recompute_hash()
        return state

    @classmethod
    def from_search_state(cls, state: tuple[Any, ...]) -> BoardState:
        turn_val, _promotion_val, moves_without_capture, piece_rows = state
        sb = cls()
        sb.turn = 0 if turn_val == Color.WHITE.value else 1
        sb.halfmove = moves_without_capture
        sb.castling = 0

        white_king_moved = True
        black_king_moved = True
        white_rook_a_moved = True
        white_rook_h_moved = True
        black_rook_a_moved = True
        black_rook_h_moved = True

        for color_val, type_val, x, y, moved in piece_rows:
            v = type_val if color_val == Color.WHITE.value else -type_val
            sb.grid[y, x] = v
            if abs(v) == KING:
                if v > 0:
                    sb.wkx, sb.wky = x, y
                    white_king_moved = moved != 0
                else:
                    sb.bkx, sb.bky = x, y
                    black_king_moved = moved != 0
            elif abs(v) == ROOK:
                if y == 7 and x == 0:
                    white_rook_a_moved = moved != 0
                elif y == 7 and x == 7:
                    white_rook_h_moved = moved != 0
                elif y == 0 and x == 0:
                    black_rook_a_moved = moved != 0
                elif y == 0 and x == 7:
                    black_rook_h_moved = moved != 0

        if not white_king_moved:
            if not white_rook_h_moved:
                sb.castling |= WHITE_K_CASTLE
            if not white_rook_a_moved:
                sb.castling |= WHITE_Q_CASTLE
        if not black_king_moved:
            if not black_rook_h_moved:
                sb.castling |= BLACK_K_CASTLE
            if not black_rook_a_moved:
                sb.castling |= BLACK_Q_CASTLE

        sb._recompute_hash()
        return sb

    def _recompute_hash(self) -> None:
        h = ZOBRIST_TURN if self.turn == 1 else 0
        for y in range(8):
            for x in range(8):
                v = int(self.grid[y, x])
                if v:
                    h ^= _zobrist_piece(x, y, v)
        self.hash_ = h

    def hash_key(self) -> int:
        return self.hash_

    def _side_sign(self) -> int:
        return 1 if self.turn == 0 else -1

    def _king_pos(self, color: int) -> tuple[int, int]:
        if color == 0:
            return self.wkx, self.wky
        return self.bkx, self.bky

    def is_square_attacked(self, x: int, y: int, by_color: int) -> bool:
        sign = 1 if by_color == 0 else -1

        if by_color == 0:
            for dx in (-1, 1):
                px, py = x + dx, y + 1
                if 0 <= px < 8 and py < 8 and self.grid[py, px] == sign * PAWN:
                    return True
        else:
            for dx in (-1, 1):
                px, py = x + dx, y - 1
                if 0 <= px < 8 and py >= 0 and self.grid[py, px] == sign * PAWN:
                    return True

        for dx, dy in KNIGHT_DELTAS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8 and self.grid[ny, nx] == sign * KNIGHT:
                return True

        for dx, dy in KING_DELTAS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 8 and 0 <= ny < 8 and self.grid[ny, nx] == sign * KING:
                return True

        for dx, dy in ORTHO_DELTAS:
            cx, cy = x + dx, y + dy
            while 0 <= cx < 8 and 0 <= cy < 8:
                v = int(self.grid[cy, cx])
                if v:
                    if v * sign > 0 and abs(v) in (ROOK, QUEEN):
                        return True
                    break
                cx += dx
                cy += dy

        for dx, dy in DIAG_DELTAS:
            cx, cy = x + dx, y + dy
            while 0 <= cx < 8 and 0 <= cy < 8:
                v = int(self.grid[cy, cx])
                if v:
                    if v * sign > 0 and abs(v) in (BISHOP, QUEEN):
                        return True
                    break
                cx += dx
                cy += dy

        return False

    def in_check(self, color: int) -> bool:
        kx, ky = self._king_pos(color)
        attacker = 1 if color == 0 else 0
        return self.is_square_attacked(kx, ky, attacker)

    def _append_pawn_moves(self, moves: list[Move4], x: int, y: int, sign: int) -> None:
        direction = -1 if sign > 0 else 1
        start_rank = 6 if sign > 0 else 1
        promo_rank = 0 if sign > 0 else 7

        ny = y + direction
        if 0 <= ny < 8 and self.grid[ny, x] == 0:
            if ny == promo_rank:
                moves.append((x, y, x, ny))
            else:
                moves.append((x, y, x, ny))
                if y == start_rank and self.grid[y + 2 * direction, x] == 0:
                    moves.append((x, y, x, y + 2 * direction))

        for dx in (-1, 1):
            nx = x + dx
            if 0 <= nx < 8 and 0 <= ny < 8:
                target = int(self.grid[ny, nx])
                if target * sign < 0:
                    moves.append((x, y, nx, ny))

    def _slide_moves(
        self,
        moves: list[Move4],
        x: int,
        y: int,
        sign: int,
        deltas: tuple[tuple[int, int], ...],
        piece_types: frozenset[int],
    ) -> None:
        piece = int(self.grid[y, x])
        if abs(piece) not in piece_types:
            return
        for dx, dy in deltas:
            cx, cy = x + dx, y + dy
            while 0 <= cx < 8 and 0 <= cy < 8:
                target = int(self.grid[cy, cx])
                if target == 0:
                    moves.append((x, y, cx, cy))
                else:
                    if target * sign < 0:
                        moves.append((x, y, cx, cy))
                    break
                cx += dx
                cy += dy

    def _append_piece_moves(self, moves: list[Move4], x: int, y: int, sign: int) -> None:
        piece = int(self.grid[y, x])
        if piece * sign <= 0:
            return
        kind = abs(piece)

        if kind == PAWN:
            self._append_pawn_moves(moves, x, y, sign)
        elif kind == KNIGHT:
            for dx, dy in KNIGHT_DELTAS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 8 and 0 <= ny < 8:
                    target = int(self.grid[ny, nx])
                    if target == 0 or target * sign < 0:
                        moves.append((x, y, nx, ny))
        elif kind == BISHOP:
            self._slide_moves(moves, x, y, sign, DIAG_DELTAS, frozenset({BISHOP}))
        elif kind == ROOK:
            self._slide_moves(moves, x, y, sign, ORTHO_DELTAS, frozenset({ROOK}))
        elif kind == QUEEN:
            self._slide_moves(moves, x, y, sign, ORTHO_DELTAS, frozenset({QUEEN}))
            self._slide_moves(moves, x, y, sign, DIAG_DELTAS, frozenset({QUEEN}))
        elif kind == KING:
            for dx, dy in KING_DELTAS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 8 and 0 <= ny < 8:
                    target = int(self.grid[ny, nx])
                    if target == 0 or target * sign < 0:
                        moves.append((x, y, nx, ny))
            self._append_castling(moves, x, y, sign)

    def _append_castling(self, moves: list[Move4], x: int, y: int, sign: int) -> None:
        if x != 4 or abs(int(self.grid[y, x])) != KING:
            return
        color = 0 if sign > 0 else 1
        if self.in_check(color):
            return

        if sign > 0:
            if (
                self.castling & WHITE_K_CASTLE
                and self.grid[y, 5] == 0
                and self.grid[y, 6] == 0
                and self.grid[y, 7] == ROOK
                and not self.is_square_attacked(5, y, 1)
                and not self.is_square_attacked(6, y, 1)
            ):
                moves.append((4, y, 6, y))
            if (
                self.castling & WHITE_Q_CASTLE
                and self.grid[y, 1] == 0
                and self.grid[y, 2] == 0
                and self.grid[y, 3] == 0
                and self.grid[y, 0] == ROOK
                and not self.is_square_attacked(3, y, 1)
                and not self.is_square_attacked(2, y, 1)
            ):
                moves.append((4, y, 2, y))
        else:
            if (
                self.castling & BLACK_K_CASTLE
                and self.grid[y, 5] == 0
                and self.grid[y, 6] == 0
                and self.grid[y, 7] == -ROOK
                and not self.is_square_attacked(5, y, 0)
                and not self.is_square_attacked(6, y, 0)
            ):
                moves.append((4, y, 6, y))
            if (
                self.castling & BLACK_Q_CASTLE
                and self.grid[y, 1] == 0
                and self.grid[y, 2] == 0
                and self.grid[y, 3] == 0
                and self.grid[y, 0] == -ROOK
                and not self.is_square_attacked(3, y, 0)
                and not self.is_square_attacked(2, y, 0)
            ):
                moves.append((4, y, 2, y))

    def generate_pseudo_legal_moves(self) -> list[Move4]:
        moves: list[Move4] = []
        sign = self._side_sign()
        for y in range(8):
            for x in range(8):
                self._append_piece_moves(moves, x, y, sign)
        return moves

    def generate_legal_moves(self) -> list[Move4]:
        side = self.turn
        legal: list[Move4] = []
        for move in self.generate_pseudo_legal_moves():
            if self._leaves_king_safe(*move, side):
                legal.append(move)
        return legal

    def has_legal_move(self) -> bool:
        side = self.turn
        for move in self.generate_pseudo_legal_moves():
            if self._leaves_king_safe(*move, side):
                return True
        return False

    def would_be_legal(self, fx: int, fy: int, tx: int, ty: int) -> bool:
        moved = int(self.grid[fy, fx])
        if moved == 0 or (1 if moved > 0 else -1) != self._side_sign():
            return False
        pseudo: list[Move4] = []
        self._append_piece_moves(pseudo, fx, fy, self._side_sign())
        if (fx, fy, tx, ty) not in pseudo:
            return False
        return self._leaves_king_safe(fx, fy, tx, ty, self.turn)

    def _leaves_king_safe(self, fx: int, fy: int, tx: int, ty: int, side: int) -> bool:
        probe = self._probe_apply(fx, fy, tx, ty)
        safe = not self.in_check(side)
        self._probe_restore(probe)
        return safe

    def _probe_apply(self, fx: int, fy: int, tx: int, ty: int) -> _Probe:
        moved = int(self.grid[fy, fx])
        captured = int(self.grid[ty, tx])
        sign = 1 if moved > 0 else -1
        wkx, wky, bkx, bky = self.wkx, self.wky, self.bkx, self.bky
        had_rook = False
        rook_fy, rook_from, rook_to, rook_val = 0, 0, 0, 0

        if abs(moved) == KING and abs(tx - fx) == 2:
            had_rook = True
            if tx == 6:
                rook_from, rook_to = 7, 5
            else:
                rook_from, rook_to = 0, 3
            rook_fy = fy
            rook_val = int(self.grid[fy, rook_from])
            self.grid[fy, rook_to] = rook_val
            self.grid[fy, rook_from] = 0

        promo_rank = 0 if sign > 0 else 7
        new_piece = sign * QUEEN if abs(moved) == PAWN and ty == promo_rank else moved
        self.grid[fy, fx] = 0
        self.grid[ty, tx] = new_piece

        if abs(moved) == KING:
            if sign > 0:
                self.wkx, self.wky = tx, ty
            else:
                self.bkx, self.bky = tx, ty

        return _Probe(
            wkx=wkx,
            wky=wky,
            bkx=bkx,
            bky=bky,
            rook_fy=rook_fy,
            rook_from=rook_from,
            rook_to=rook_to,
            rook_val=rook_val,
            had_rook=had_rook,
            moved=moved,
            captured=captured,
            fx=fx,
            fy=fy,
            tx=tx,
            ty=ty,
        )

    def _probe_restore(self, probe: _Probe) -> None:
        self.grid[probe.fy, probe.fx] = probe.moved
        self.grid[probe.ty, probe.tx] = probe.captured
        self.wkx, self.wky = probe.wkx, probe.wky
        self.bkx, self.bky = probe.bkx, probe.bky
        if probe.had_rook:
            self.grid[probe.rook_fy, probe.rook_from] = probe.rook_val
            self.grid[probe.rook_fy, probe.rook_to] = 0

    def make_move(self, fx: int, fy: int, tx: int, ty: int) -> bool:
        moved = int(self.grid[fy, fx])
        if moved == 0:
            return False
        sign = 1 if moved > 0 else -1
        if sign != self._side_sign():
            return False

        captured = int(self.grid[ty, tx])
        old_castling = self.castling
        old_wkx, old_wky = self.wkx, self.wky
        old_bkx, old_bky = self.bkx, self.bky
        old_half = self.halfmove
        old_hash = self.hash_
        old_turn = self.turn

        # Castling: king slides two squares horizontally.
        if abs(moved) == KING and abs(tx - fx) == 2:
            if tx == 6:
                rook_from, rook_to = 7, 5
            else:
                rook_from, rook_to = 0, 3
            rook_val = int(self.grid[fy, rook_from])
            self.hash_ ^= _zobrist_piece(rook_from, fy, rook_val)
            self.grid[fy, rook_to] = rook_val
            self.grid[fy, rook_from] = 0
            self.hash_ ^= _zobrist_piece(rook_to, fy, rook_val)

        self.hash_ ^= _zobrist_piece(fx, fy, moved)
        if captured:
            self.hash_ ^= _zobrist_piece(tx, ty, captured)

        promo_rank = 0 if sign > 0 else 7
        new_piece = moved
        if abs(moved) == PAWN and ty == promo_rank:
            new_piece = sign * QUEEN

        self.grid[ty, tx] = new_piece
        self.grid[fy, fx] = 0
        self.hash_ ^= _zobrist_piece(tx, ty, new_piece)

        if abs(moved) == KING:
            if sign > 0:
                self.wkx, self.wky = tx, ty
                self.castling &= ~(WHITE_K_CASTLE | WHITE_Q_CASTLE)
            else:
                self.bkx, self.bky = tx, ty
                self.castling &= ~(BLACK_K_CASTLE | BLACK_Q_CASTLE)
        if fx == 0:
            if fy == 7:
                self.castling &= ~WHITE_Q_CASTLE
            elif fy == 0:
                self.castling &= ~BLACK_Q_CASTLE
        if fx == 7:
            if fy == 7:
                self.castling &= ~WHITE_K_CASTLE
            elif fy == 0:
                self.castling &= ~BLACK_K_CASTLE
        if tx == 0:
            if ty == 7:
                self.castling &= ~WHITE_Q_CASTLE
            elif ty == 0:
                self.castling &= ~BLACK_Q_CASTLE
        if tx == 7:
            if ty == 7:
                self.castling &= ~WHITE_K_CASTLE
            elif ty == 0:
                self.castling &= ~BLACK_K_CASTLE

        if captured or abs(moved) == PAWN:
            self.halfmove = 0
        else:
            self.halfmove += 1

        self.turn ^= 1
        self.hash_ ^= ZOBRIST_TURN

        self._undo_stack.append(
            _Undo(
                fx=fx,
                fy=fy,
                tx=tx,
                ty=ty,
                captured=captured,
                moved_piece=moved,
                castling=old_castling,
                wkx=old_wkx,
                wky=old_wky,
                bkx=old_bkx,
                bky=old_bky,
                halfmove=old_half,
                hash_=old_hash,
                turn=old_turn,
            )
        )
        return True

    def peek_undo(self) -> _Undo | None:
        return self._undo_stack[-1] if self._undo_stack else None

    def unmake_move(self) -> None:
        undo = self._undo_stack.pop()

        self.turn = undo.turn
        self.hash_ = undo.hash_
        self.castling = undo.castling
        self.wkx, self.wky = undo.wkx, undo.wky
        self.bkx, self.bky = undo.bkx, undo.bky
        self.halfmove = undo.halfmove

        fx, fy, tx, ty = undo.fx, undo.fy, undo.tx, undo.ty
        moved = undo.moved_piece

        if abs(moved) == KING and abs(tx - fx) == 2:
            if tx == 6:
                rook_from, rook_to = 7, 5
            else:
                rook_from, rook_to = 0, 3
            rook_val = int(self.grid[fy, rook_to])
            self.grid[fy, rook_from] = rook_val
            self.grid[fy, rook_to] = 0

        self.grid[fy, fx] = moved
        self.grid[ty, tx] = undo.captured

    def insufficient_material(self) -> bool:
        counts: dict[int, int] = {}
        for y in range(8):
            for x in range(8):
                v = abs(int(self.grid[y, x]))
                if v:
                    counts[v] = counts.get(v, 0) + 1
        n = sum(counts.values())
        if n <= 2:
            return True
        if n == 3:
            return counts.get(KNIGHT, 0) + counts.get(BISHOP, 0) == 1
        if n == 4 and counts.get(BISHOP, 0) == 2:
            bishops: list[int] = []
            for y in range(8):
                for x in range(8):
                    v = int(self.grid[y, x])
                    if abs(v) == BISHOP:
                        bishops.append((x + y) % 2)
            return len(bishops) == 2 and bishops[0] != bishops[1]
        return False

    def _mobility_by_square(self) -> dict[tuple[int, int], int]:
        counts: dict[tuple[int, int], int] = {}
        for y in range(8):
            for x in range(8):
                v = int(self.grid[y, x])
                if v == 0:
                    continue
                sign = 1 if v > 0 else -1
                moves: list[Move4] = []
                self._append_piece_moves(moves, x, y, sign)
                counts[(x, y)] = len(moves)
        return counts

    def evaluate(self, agent_color: int, *, mobility: bool = True) -> float:
        mobility_map = self._mobility_by_square() if mobility else {}
        score = 0.0
        for y in range(8):
            for x in range(8):
                v = int(self.grid[y, x])
                if v == 0:
                    continue
                val = PIECE_VALUES[abs(v)]
                mob = 0.05 * mobility_map.get((x, y), 0.0)
                if v > 0:
                    score += val + mob
                else:
                    score -= val + mob
        if self.in_check(0):
            score -= 0.5
        if self.in_check(1):
            score += 0.5
        if agent_color == 1:
            score = -score
        return float(score)
