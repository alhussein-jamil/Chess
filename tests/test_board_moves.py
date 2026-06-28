"""Board drag-and-drop move validation."""

from __future__ import annotations

from copy import deepcopy

import pytest

from chess.core.board import Board
from chess.core.piece import STARTING_PIECES, Position


@pytest.fixture
def starting_board() -> Board:
    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.update()
    return board


def test_is_legal_target_accepts_pawn_advance(starting_board: Board) -> None:
    pawn = starting_board.board[Position(4, 6)]
    origin = Position(4, 6)
    target = Position(4, 5)
    assert starting_board.is_legal_target(pawn, target, origin)


def test_is_legal_target_rejects_random_square(starting_board: Board) -> None:
    pawn = starting_board.board[Position(4, 6)]
    origin = Position(4, 6)
    target = Position(4, 3)
    assert not starting_board.is_legal_target(pawn, target, origin)


def test_move_piece_records_last_move(starting_board: Board) -> None:
    pawn = starting_board.board[Position(4, 6)]
    origin = Position(4, 6)
    target = Position(4, 4)
    assert starting_board.move_piece(pawn, target)[0]
    assert starting_board.last_move == (origin, target)


def test_restore_dragged_piece_returns_piece_to_origin(starting_board: Board) -> None:
    from chess.core.piece import NullPiece

    pawn = starting_board.board[Position(4, 6)]
    origin = Position(4, 6)
    starting_board.drag_origin = origin
    starting_board.dragged_piece = pawn
    starting_board.board[origin] = NullPiece()
    starting_board._restore_dragged_piece()

    assert starting_board.dragged_piece is None
    assert starting_board.board[origin] is pawn
    assert pawn.position == origin
