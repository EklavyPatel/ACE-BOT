import queue
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
import chess
import chess.engine
from source.evaluation import evaluate, evaluate_white
from source.search import Searcher, Limits, MATE, INF, position_key
from source.uci import UCI, allocate_time, parse_go

ROOT = Path(__file__).resolve().parents[1]
CMD = [sys.executable, str(ROOT / "engine/main.py")]


class EvaluationTests(unittest.TestCase):
    def test_colour_mirror(self):
        board = chess.Board("r3k2r/pp1n1ppp/2p1b3/3pP3/3P4/2NB4/PPP2PPP/R3K2R w KQkq - 0 12")
        self.assertAlmostEqual(evaluate_white(board), -evaluate_white(board.mirror()), delta=1)
        self.assertAlmostEqual(evaluate(board), evaluate(board.mirror()), delta=1)

    def test_starting_position_is_balanced(self):
        self.assertEqual(evaluate_white(chess.Board()), 9)


class SearchTests(unittest.TestCase):
    def search(self, board, depth=3, seconds=3.0):
        return Searcher().search(board, Limits(seconds, seconds, depth))

    def test_mates_for_both_colours(self):
        white = chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
        for board in (white, white.mirror()):
            with self.subTest(fen=board.fen()):
                result = self.search(board)
                self.assertGreaterEqual(result.score, MATE - 2)
                board.push(result.move)
                self.assertTrue(board.is_checkmate())

    def test_free_queen_capture_for_both_colours(self):
        white = chess.Board("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
        for board in (white, white.mirror()):
            result = self.search(board, 2)
            self.assertEqual(board.piece_type_at(result.move.to_square), chess.QUEEN)

    def test_abort_preserves_entire_board(self):
        board = chess.Board()
        for move in ("e2e4", "e7e5", "g1f3", "b8c6"):
            board.push_uci(move)
        before = board.fen(), tuple(board.move_stack)
        result = Searcher().search(board, Limits(None, None, 20, 75))
        self.assertEqual((board.fen(), tuple(board.move_stack)), before)
        self.assertIn(result.move, board.legal_moves)
        self.assertEqual(result.nodes, 75)

    def test_zero_budget_and_cancelled_fallback(self):
        board = chess.Board()
        event = threading.Event()
        event.set()
        for engine in (Searcher(), Searcher(event)):
            result = engine.search(board, Limits(0, 0))
            self.assertIn(result.move, board.legal_moves)
            self.assertEqual(result.depth, 0)

    def test_terminal_and_mate_precedes_fifty_move_draw(self):
        mate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 100 1")
        result = self.search(mate)
        self.assertIsNone(result.move)
        self.assertEqual(result.score, -MATE)
        stale = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertIsNone(self.search(stale).move)
        self.assertEqual(self.search(stale).score, 0)

    def test_threefold_history_and_fifty_move(self):
        board = chess.Board()
        for move in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
            board.push_uci(move)
        result = self.search(board)
        self.assertEqual(result.score, 0)
        self.assertIn(result.move, board.legal_moves)
        board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 100 51")
        self.assertEqual(self.search(board).score, 0)

    def test_quiescence_searches_quiet_check_evasions(self):
        board = chess.Board("4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
        original = evaluate
        def checked_eval(board):
            self.assertFalse(board.is_check(), "Stand-pat is forbidden in check")
            return original(board)
        engine = Searcher()
        engine.search(chess.Board(), Limits(0, 0))
        engine.deadline = None
        engine.limits.nodes = 10000
        engine.repetitions.clear()
        engine.repetitions[position_key(board)] = 1
        before = board.fen()
        with patch("source.search.evaluate", checked_eval):
            engine.quiescence(board, -INF, INF, 0)
        self.assertEqual(board.fen(), before)
        self.assertGreater(engine.nodes, 1)

    def test_alpha_beta_agrees_with_exhaustive_search(self):
        board = chess.Board("4k3/3p4/8/4n3/3P4/4N3/8/4K3 w - - 0 1")
        engine = Searcher()
        expected = engine.search(board, Limits(None, None, 2))
        engine.nodes = 0
        def reference(depth, ply):
            moves = list(board.legal_moves)
            if not moves:
                return -MATE + ply if board.is_check() else 0
            if engine.drawn(board):
                return 0
            if not depth:
                return engine.quiescence(board, -INF, INF, ply)
            best = -INF
            for move in moves:
                engine.push(board, move)
                try:
                    best = max(best, -reference(depth - 1, ply + 1))
                finally:
                    engine.pop(board)
            return best
        self.assertEqual(expected.score, reference(2, 0))


class TimeTests(unittest.TestCase):
    def test_clock_budget_uses_correct_side_and_increment(self):
        args = parse_go("wtime 180000 btime 100 winc 2000 binc 0".split())
        white = allocate_time(args, chess.WHITE)
        black = allocate_time(args, chess.BLACK)
        self.assertGreater(white.hard_time, black.hard_time)
        self.assertLessEqual(black.hard_time, 0.05)
        self.assertGreater(white.soft_time, 1)

    def test_small_clocks_and_explicit_movetime(self):
        for ms in (0, 1, 10, 100, 1000):
            limit = allocate_time({"wtime": ms}, chess.WHITE)
            self.assertLessEqual(limit.hard_time, ms / 1000)
            self.assertLessEqual(limit.soft_time, limit.hard_time)
        self.assertLessEqual(allocate_time({"movetime": 50}, chess.WHITE).hard_time, 0.05)


class UCITests(unittest.TestCase):
    def test_real_client_legal_special_moves_and_newgame(self):
        with chess.engine.SimpleEngine.popen_uci(CMD, timeout=5) as engine:
            engine.configure({"Move Overhead": 20})
            boards = [
                (chess.Board(), None),
                (chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1"), "a7a8q"),
                (chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"), "e5d6"),
                (chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"), "e1g1"),
            ]
            for index, (board, restricted) in enumerate(boards):
                with self.subTest(index=index):
                    roots = [chess.Move.from_uci(restricted)] if restricted else None
                    result = engine.play(board, chess.engine.Limit(time=0.08),
                                         game=index, root_moves=roots)
                    self.assertIn(result.move, board.legal_moves)
                    if restricted:
                        self.assertEqual(result.move.uci(), restricted)
            board = chess.Board()
            board.push_san("e4")
            result = engine.play(board, chess.engine.Limit(white_clock=180, black_clock=0.1,
                                white_inc=2, black_inc=0), game="black-clock")
            self.assertIn(result.move, board.legal_moves)
            engine.ping()

    def test_position_parser_is_atomic(self):
        uci = UCI()
        uci.set_position("startpos moves e2e4 e7e5".split())
        before = uci.board.fen()
        with self.assertRaises(ValueError):
            uci.set_position("startpos moves e2e4 e7e6 e4e6".split())
        self.assertEqual(uci.board.fen(), before)
        uci.set_position(("fen 4k3/8/8/8/8/8/4P3/4K3 w - - 0 1 moves e2e4").split())
        self.assertEqual(uci.board.turn, chess.BLACK)

    def test_raw_protocol_stop_readiness_terminal_and_stdout(self):
        proc = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(line.strip()) for line in proc.stdout], daemon=True).start()
        observed = []
        def send(text):
            proc.stdin.write(text + "\n")
            proc.stdin.flush()
        def until(prefix, timeout=4):
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                try:
                    line = lines.get(timeout=max(0.01, end - time.monotonic()))
                except queue.Empty:
                    break
                observed.append(line)
                if line.startswith(prefix):
                    return line
            self.fail(f"No {prefix!r}; received {observed}")
        try:
            send("uci")
            until("uciok")
            send("position startpos")
            send("go infinite")
            send("isready")
            until("readyok", 1)
            send("stop")
            line = until("bestmove", 1)
            self.assertIn(chess.Move.from_uci(line.split()[1]), chess.Board().legal_moves)
            # A terminal board must produce the UCI null move, not crash.
            send("position fen 7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
            send("go depth 2")
            self.assertEqual(until("bestmove"), "bestmove 0000")
            send("position startpos moves e2e5")
            send("isready")
            until("readyok")
            send("ucinewgame")
            send("position startpos moves d2d4")
            send("go nodes 30")
            line = until("bestmove")
            board = chess.Board()
            board.push_uci("d2d4")
            self.assertIn(chess.Move.from_uci(line.split()[1]), board.legal_moves)
            self.assertTrue(all(line.split()[0] in {"id", "option", "uciok", "readyok", "info", "bestmove"}
                                for line in observed))
        finally:
            if proc.poll() is None:
                send("quit")
            proc.wait(timeout=4)
            proc.stdin.close()
            proc.stdout.close()
            stderr = proc.stderr.read()
            proc.stderr.close()
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
