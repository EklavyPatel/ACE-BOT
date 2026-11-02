"""UCI adapter with a responsive reader and one cancellable search worker."""
import sys
import threading
import traceback
import chess
from .search import Limits, Searcher, MATE, MAX_PLY

NAME = "Ekal Chess 1.0"


def parse_go(tokens):
    scalars = {"wtime", "btime", "winc", "binc", "movestogo", "depth", "nodes", "movetime", "mate"}
    flags = {"infinite", "ponder"}
    result = {}
    i = 0
    while i < len(tokens):
        key = tokens[i]
        if key in scalars and i + 1 < len(tokens):
            result[key] = max(0, int(tokens[i + 1]))
            i += 2
        elif key in flags:
            result[key] = True
            i += 1
        elif key == "searchmoves":
            i += 1
            moves = []
            while i < len(tokens) and tokens[i] not in scalars | flags | {"searchmoves"}:
                moves.append(chess.Move.from_uci(tokens[i]))
                i += 1
            result[key] = moves
        else:
            i += 1
    return result


def allocate_time(args, turn, overhead_ms=200):
    depth = max(1, min(64, args.get("depth", 64)))
    nodes = max(1, args["nodes"]) if "nodes" in args else None
    if "movetime" in args:
        requested = args["movetime"] / 1000
        hard = max(0.0, requested - min(overhead_ms / 1000, requested * 0.15))
        return Limits(hard * 0.8, hard, depth, nodes)
    key, increment = ("wtime", "winc") if turn == chess.WHITE else ("btime", "binc")
    if key in args:
        remaining = args[key] / 1000
        inc = args.get(increment, 0) / 1000
        reserve = min(overhead_ms / 1000, remaining * 0.5)
        available = max(0.0, remaining - reserve)
        horizon = max(1, args.get("movestogo", 35))
        soft = min(available * 0.25, available / horizon + inc * 0.65)
        hard = min(available, max(soft, soft * 1.6))
        return Limits(soft, hard, depth, nodes)
    if args.get("infinite") or args.get("ponder") or "depth" in args or "nodes" in args:
        return Limits(None, None, depth, nodes)
    return Limits(0.7, 1.0, depth, nodes)


class UCI:
    def __init__(self):
        self.board = chess.Board()
        self.worker = None
        self.stop = threading.Event()
        self.print_lock = threading.Lock()
        self.overhead_ms = 200

    def emit(self, text):
        with self.print_lock:
            print(text, flush=True)

    def stop_search(self):
        if self.worker is not None:
            self.stop.set()
            self.worker.join()
            self.worker = None

    def set_position(self, tokens):
        # Build a candidate first: malformed input cannot partially corrupt the board.
        if not tokens:
            raise ValueError("Missing position")
        if tokens[0] == "startpos":
            candidate = chess.Board()
            i = 1
        elif tokens[0] == "fen":
            if len(tokens) < 7:
                raise ValueError("A FEN requires six fields")
            candidate = chess.Board(" ".join(tokens[1:7]))
            i = 7
        else:
            raise ValueError("Expected startpos or fen")
        if not candidate.is_valid():
            raise ValueError("Invalid standard-chess position")
        if i < len(tokens):
            if tokens[i] != "moves":
                raise ValueError("Expected moves")
            for text in tokens[i + 1:]:
                move = candidate.parse_uci(text)
                if not move or move not in candidate.legal_moves:
                    raise ValueError("Illegal move in position")
                candidate.push(move)
        self.board = candidate

    def go(self, args):
        self.stop_search()
        self.stop = threading.Event()
        board = self.board.copy(stack=True)
        stop = self.stop
        limits = allocate_time(args, board.turn, self.overhead_ms)
        roots = args.get("searchmoves")

        def report(result):
            if abs(result.score) > MATE - MAX_PLY:
                plies = MATE - abs(result.score)
                mate = (plies + 1) // 2
                score = f"mate {mate if result.score > 0 else -mate}"
            else:
                score = f"cp {result.score}"
            ms = int(result.elapsed * 1000)
            nps = int(result.nodes / max(result.elapsed, 0.001))
            pv = " ".join(m.uci() for m in result.pv)
            self.emit(f"info depth {result.depth} score {score} nodes {result.nodes} time {ms} nps {nps} pv {pv}")

        def work():
            legal = list(board.legal_moves)
            if roots is not None:
                legal = [m for m in legal if m in roots]
            fallback = legal[0] if legal else None
            move = fallback
            try:
                result = Searcher(stop).search(board, limits, report, roots)
                move = result.move
                # UCI "infinite" returns only after stop, even if a mate was found.
                if args.get("infinite") or args.get("ponder"):
                    stop.wait()
            except Exception:
                traceback.print_exc(file=sys.stderr)
            self.emit(f"bestmove {move.uci() if move else '0000'}")

        self.worker = threading.Thread(target=work, name="chess-search", daemon=True)
        self.worker.start()

    def run(self):
        try:
            for line in sys.stdin:
                tokens = line.strip().split()
                if not tokens:
                    continue
                command, args = tokens[0], tokens[1:]
                try:
                    if command == "uci":
                        self.emit(f"id name {NAME}")
                        self.emit("id author Eklavy Patel / AI-assisted project")
                        self.emit("option name Move Overhead type spin default 200 min 0 max 5000")
                        self.emit("uciok")
                    elif command == "isready":
                        self.emit("readyok")
                    elif command == "setoption":
                        if "value" in args:
                            i = args.index("value")
                            name = " ".join(args[1:i]).lower()
                            if name == "move overhead":
                                self.overhead_ms = max(0, min(5000, int(args[i + 1])))
                    elif command == "ucinewgame":
                        self.stop_search()
                        self.board = chess.Board()
                    elif command == "position":
                        self.stop_search()
                        self.set_position(args)
                    elif command == "go":
                        self.go(parse_go(args))
                    elif command == "stop":
                        self.stop_search()
                    elif command == "ponderhit":
                        # Ponder is not advertised: a defensive stop avoids an unbounded search.
                        self.stop_search()
                    elif command == "quit":
                        break
                    # Unknown UCI commands (including debug/register) are ignored.
                except (ValueError, IndexError) as error:
                    print(f"Ignored malformed {command}: {error}", file=sys.stderr, flush=True)
        finally:
            self.stop_search()
