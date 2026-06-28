from __future__ import annotations

from copy import deepcopy

import pytest

from chess.ai.minmax import MinMaxAgent, choose_move_in_subprocess
from chess.core.board import Board
from chess.core.piece import (
    STARTING_PIECES,
    King,
    Position,
    Queen,
    Rook,
)
from chess.core.types import Color, Ending
from chess.ui.vs_ai import _BackgroundAi


@pytest.fixture
def starting_board() -> Board:
    board = Board.from_pieces(deepcopy(STARTING_PIECES))
    board.update()
    return board


def test_starting_position_has_twenty_white_moves(starting_board: Board) -> None:
    moves = MinMaxAgent.generate_possible_moves(starting_board)
    assert starting_board.turn == Color.WHITE
    assert len(moves) == 20


def test_apply_move_switches_turn(starting_board: Board) -> None:
    move = MinMaxAgent.generate_possible_moves(starting_board)[0]
    assert MinMaxAgent.apply_move(starting_board, move)
    assert starting_board.turn == Color.BLACK


def test_choose_move_is_legal(starting_board: Board) -> None:
    agent = MinMaxAgent(color=Color.WHITE, depth=2, workers=1)
    legal = MinMaxAgent.generate_possible_moves(starting_board)
    move = agent.choose_move(starting_board)
    assert move is not None
    assert move in legal


def test_evaluate_favors_white_material() -> None:
    board = Board.from_pieces(
        [
            King(color=Color.WHITE, position=Position(4, 7)),
            King(color=Color.BLACK, position=Position(4, 0)),
            Queen(color=Color.WHITE, position=Position(3, 3)),
        ]
    )
    board.update()
    agent = MinMaxAgent(color=Color.WHITE, depth=1)
    assert agent.evaluate(board) > 0


def test_minimax_prefers_hanging_queen_capture() -> None:
    board = Board.from_pieces(
        [
            King(color=Color.WHITE, position=Position(4, 7)),
            King(color=Color.BLACK, position=Position(4, 0)),
            Queen(color=Color.WHITE, position=Position(3, 4)),
            Rook(color=Color.BLACK, position=Position(3, 0)),
        ]
    )
    board.turn = Color.BLACK
    board.update()

    agent = MinMaxAgent(color=Color.BLACK, depth=2, workers=1)
    move = agent.choose_move(board)
    assert move is not None
    assert move[1] == Position(3, 4)


def test_terminal_checkmate_score() -> None:
    board = Board.from_pieces(
        [
            King(color=Color.WHITE, position=Position(4, 7)),
            King(color=Color.BLACK, position=Position(4, 0)),
            Queen(color=Color.WHITE, position=Position(3, 0)),
            Rook(color=Color.WHITE, position=Position(0, 0)),
        ]
    )
    board.turn = Color.BLACK
    board.update()
    board.checkmates[Color.BLACK] = Ending.CHECKMATE

    white_agent = MinMaxAgent(color=Color.WHITE, depth=1)
    black_agent = MinMaxAgent(color=Color.BLACK, depth=1)
    assert white_agent.evaluate(board) > 50_000
    assert black_agent.evaluate(board) < -50_000


def test_choose_move_in_subprocess_parallel(starting_board: Board) -> None:
    state = starting_board.to_search_state()
    coords = choose_move_in_subprocess(state, 3, Color.WHITE, None, 0)
    assert coords is not None
    move = MinMaxAgent._coords_to_move(coords)
    assert move in MinMaxAgent.generate_possible_moves(starting_board)


def test_background_ai_parallel_path(starting_board: Board) -> None:
    white_move = MinMaxAgent.generate_possible_moves(starting_board)[0]
    assert MinMaxAgent.apply_move(starting_board, white_move)
    assert starting_board.turn == Color.BLACK

    agent = MinMaxAgent(color=Color.BLACK, depth=3, workers=0)
    bg = _BackgroundAi(workers=0)
    try:
        assert bg.pool_size >= 2
        bg.request_move(starting_board, agent)
        while bg.thinking:
            pass
        move = bg.take_move()
        assert move is not None
        legal = MinMaxAgent.generate_possible_moves(starting_board)
        assert move in legal
        assert MinMaxAgent.apply_move(starting_board, move)
    finally:
        bg.shutdown()
