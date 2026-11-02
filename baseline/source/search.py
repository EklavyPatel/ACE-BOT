"""Negamax alpha-beta, iterative deepening, quiescence and bounded caching.

Written for this project, without copying an existing engine. Prefer clarity
and correctness over aggressive, hard-to-validate pruning on a short deadline.
"""
from collections import Counter
from dataclasses import dataclass
import threading
import time
import chess
from .evaluation import evaluate, VALUES

MATE = 30000
INF = 32000
MAX_PLY = 96


def position_key(board):
    """Public board fields only; en passant matters only when it is legal."""
    return (board.pawns, board.knights, board.bishops, board.rooks,
            board.queens, board.kings, board.occupied_co[chess.WHITE],
            board.occupied_co[chess.BLACK], board.turn, board.clean_castling_rights(),
            board.ep_square if board.has_legal_en_passant() else None)


class SearchStopped(Exception):
    pass


@dataclass
class Limits:
    soft_time: float | None = 1.0
    hard_time: float | None = 1.5
    depth: int = 64
    nodes: int | None = None


@dataclass
class Result:
    move: chess.Move | None
    score: int = 0
    depth: int = 0
    nodes: int = 0
    elapsed: float = 0.0
    pv: tuple = ()


@dataclass
class Entry:
    depth: int
    score: int
    bound: str
    move: chess.Move | None


class Searcher:
    def __init__(self, stop=None, table_entries=30000):
        self.stop = stop if stop is not None else threading.Event()
        self.table_entries = table_entries
        self.table = {}
        self.history = Counter()
        self.killers = {}

    def visit(self):
        if self.stop.is_set() or (self.deadline is not None and time.perf_counter() >= self.deadline):
            raise SearchStopped
        if self.limits.nodes is not None and self.nodes >= self.limits.nodes:
            raise SearchStopped
        self.nodes += 1

    def context_key(self, board):
        # Repetition and 50-move state affect values. Include complete repetition
        # counts instead of reusing a cached draw in a different game history.
        return position_key(board), board.halfmove_clock, frozenset(self.repetitions.items())

    def push(self, board, move):
        board.push(move)
        self.repetitions[position_key(board)] += 1

    def pop(self, board):
        key = position_key(board)
        self.repetitions[key] -= 1
        if not self.repetitions[key]:
            del self.repetitions[key]
        board.pop()

    def drawn(self, board):
        return (board.halfmove_clock >= 100 or board.is_insufficient_material()
                or self.repetitions[position_key(board)] >= 3)

    def ordered(self, board, moves, preferred=None, ply=0):
        killers = self.killers.get(ply, ())
        def priority(move):
            if move == preferred:
                return 1000000
            score = 0
            victim = board.piece_type_at(move.to_square)
            if board.is_en_passant(move):
                victim = chess.PAWN
            if victim:
                score += 100000 + 16 * VALUES[victim] - VALUES[board.piece_type_at(move.from_square)]
            if move.promotion:
                score += 90000 + VALUES[move.promotion]
            if move in killers:
                score += 70000
            score += min(50000, self.history[board.turn, move.from_square, move.to_square])
            return score
        return sorted(moves, key=priority, reverse=True)

    def quiescence(self, board, alpha, beta, ply, qdepth=0):
        self.visit()
        moves = list(board.legal_moves)
        checked = board.is_check()
        if not moves:
            return -MATE + ply if checked else 0
        if self.drawn(board):
            return 0
        if ply >= MAX_PLY:
            return evaluate(board)
        if not checked:
            stand = evaluate(board)
            if stand >= beta:
                return stand
            alpha = max(alpha, stand)
            if qdepth >= 12:
                return alpha
            # Include quiet promotions. When in check, search EVERY legal evasion
            # and never use stand-pat as though passing a turn were allowed.
            moves = [m for m in moves if board.is_capture(m) or m.promotion]
        for move in self.ordered(board, moves, ply=ply):
            self.push(board, move)
            try:
                score = -self.quiescence(board, -beta, -alpha, ply + 1, qdepth + 1)
            finally:
                self.pop(board)
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def negamax(self, board, depth, alpha, beta, ply):
        if depth <= 0:
            return self.quiescence(board, alpha, beta, ply)
        self.visit()
        moves = list(board.legal_moves)
        if not moves:
            return -MATE + ply if board.is_check() else 0
        if self.drawn(board):
            return 0
        if ply >= MAX_PLY:
            return evaluate(board)
        key = self.context_key(board)
        entry = self.table.get(key)
        preferred = entry.move if entry else None
        if entry and entry.depth >= depth:
            score = entry.score
            if score > MATE - MAX_PLY:
                score -= ply
            elif score < -MATE + MAX_PLY:
                score += ply
            if entry.bound == "exact":
                return score
            if entry.bound == "lower" and score >= beta:
                return score
            if entry.bound == "upper" and score <= alpha:
                return score
        original_alpha = alpha
        best = -INF
        best_move = None
        for move in self.ordered(board, moves, preferred, ply):
            quiet = not board.is_capture(move) and not move.promotion
            self.push(board, move)
            try:
                score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            finally:
                self.pop(board)
            if score > best:
                best, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                if quiet:
                    old = self.killers.get(ply, ())
                    self.killers[ply] = (move,) + tuple(m for m in old if m != move)[:1]
                    self.history[board.turn, move.from_square, move.to_square] += depth * depth
                break
        bound = "upper" if best <= original_alpha else "lower" if best >= beta else "exact"
        stored_score = best
        if best > MATE - MAX_PLY:
            stored_score += ply
        elif best < -MATE + MAX_PLY:
            stored_score -= ply
        if len(self.table) >= self.table_entries:
            self.table.clear()
        self.table[key] = Entry(depth, stored_score, bound, best_move)
        return best

    def search(self, board, limits=None, report=None, root_moves=None):
        self.limits = limits or Limits()
        self.started = time.perf_counter()
        self.deadline = (None if self.limits.hard_time is None else
                         self.started + max(0.0, self.limits.hard_time))
        self.nodes = 0
        self.table.clear()
        self.history.clear()
        self.killers.clear()
        self.repetitions = Counter()
        past = board.copy(stack=True)
        self.repetitions[position_key(past)] += 1
        # Positions before the most recent irreversible pawn move/capture cannot
        # recur; a castling-right change may leave harmless extra history here.
        for _ in range(min(board.halfmove_clock, len(past.move_stack))):
            past.pop()
            self.repetitions[position_key(past)] += 1
        legal = list(board.legal_moves)
        if root_moves is not None:
            allowed = set(root_moves)
            legal = [m for m in legal if m in allowed]
        if not legal:
            return Result(None, -MATE if board.is_check() else 0)
        legal = self.ordered(board, legal)
        result = Result(legal[0], evaluate(board), pv=(legal[0],))
        if self.drawn(board):
            result.score = 0
            return result
        for depth in range(1, min(64, max(1, self.limits.depth)) + 1):
            alpha, best, best_move = -INF, -INF, legal[0]
            try:
                for move in self.ordered(board, legal, result.move):
                    self.push(board, move)
                    try:
                        score = -self.negamax(board, depth - 1, -INF, -alpha, 1)
                    finally:
                        self.pop(board)
                    if score > best:
                        best, best_move = score, move
                    alpha = max(alpha, score)
            except SearchStopped:
                break
            result = Result(best_move, best, depth, self.nodes,
                            time.perf_counter() - self.started, (best_move,))
            if report:
                report(result)
            # Root values from cut-off searches are bounds; use only the actual
            # best move as ordering information for the next iteration.
            if abs(best) >= MATE - MAX_PLY:
                break
            if (self.limits.soft_time is not None and
                    time.perf_counter() - self.started >= self.limits.soft_time):
                break
        result.nodes = self.nodes
        result.elapsed = time.perf_counter() - self.started
        return result
