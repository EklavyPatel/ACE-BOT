"""Regression coverage for selective quiescence and static-only caching."""
import unittest
from unittest.mock import patch
import chess
from source.search import Searcher, Limits, position_key, INF
from source.evaluation import evaluate


class ReviewTests(unittest.TestCase):
    def prepare(self, board):
        search = Searcher()
        search.search(chess.Board(), Limits(0, 0))
        search.deadline = None
        search.repetitions.clear()
        search.repetitions[position_key(board)] = 1
        return search

    def test_quiet_promotion_in_quiescence(self):
        board = chess.Board('7k/P7/8/8/8/8/8/4K3 w - - 0 1')
        search = self.prepare(board)
        self.assertGreater(search.quiescence(board, -INF, INF, 0), 700)
        self.assertEqual(len(board.move_stack), 0)

    def test_stalemate_before_static_cache(self):
        board = chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
        search = self.prepare(board)
        search.eval_cache[position_key(board)] = -900
        self.assertEqual(search.quiescence(board, -INF, INF, 0), 0)

    def test_static_cache_reuses_only_formula(self):
        board = chess.Board()
        search = self.prepare(board)
        with patch('source.search.evaluate', wraps=evaluate) as formula:
            self.assertEqual(search.static_eval(board), search.static_eval(board))
            self.assertEqual(formula.call_count, 1)
            board.turn = not board.turn
            self.assertEqual(search.static_eval(board), evaluate(board))
            self.assertEqual(formula.call_count, 2)

    def test_cached_position_does_not_override_draw_history(self):
        board = chess.Board('4k3/8/8/8/8/8/8/R3K3 w - - 0 1')
        search = self.prepare(board)
        self.assertGreater(search.static_eval(board), 100)
        board.halfmove_clock = 100
        self.assertEqual(search.quiescence(board, -INF, INF, 0), 0)

    def test_poisoned_rook_not_taken_by_queen(self):
        board = chess.Board('3rk3/8/8/8/8/8/8/3QK3 w - - 0 1')
        result = Searcher().search(board, Limits(None, None, 2))
        self.assertNotEqual(result.move.uci(), 'd1d8')


if __name__ == '__main__':
    unittest.main()
