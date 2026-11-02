#!/usr/bin/env python3
"""Run real UCI games against reproducible local random/greedy baselines.

No other chess engine is loaded. The baselines are written here for this project.
Saves PGNs and JSON; a move cap is reported as unfinished, never as a win/draw.
"""
import argparse
import json
from pathlib import Path
import random
import sys
import time
import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]


def material(board):
    values = {chess.PAWN: 100, chess.KNIGHT: 305, chess.BISHOP: 325,
              chess.ROOK: 510, chess.QUEEN: 925}
    return sum(value * (len(board.pieces(piece, chess.WHITE)) -
                        len(board.pieces(piece, chess.BLACK)))
               for piece, value in values.items())


def baseline(board, rng, kind):
    moves = list(board.legal_moves)
    rng.shuffle(moves)
    if kind == "random":
        return moves[0]
    best = -float("inf")
    chosen = moves[0]
    side = 1 if board.turn == chess.WHITE else -1
    for move in moves:
        board.push(move)
        if board.is_checkmate():
            score = 30000
        elif board.is_game_over(claim_draw=True):
            score = 0
        else:
            score = side * material(board)
        board.pop()
        if score > best:
            best, chosen = score, move
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=4)
    parser.add_argument("--seconds", type=float, default=0.1, help="Per-move cap; omitted in --official mode")
    parser.add_argument("--max-plies", type=int, default=300)
    parser.add_argument("--official", action="store_true", help="Full 180+2 clock, no per-move cap")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "validation")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for game_index in range(args.games):
        kind = "random" if game_index // 2 % 2 == 0 else "greedy"
        bot_colour = chess.WHITE if game_index % 2 == 0 else chess.BLACK
        board = chess.Board()
        rng = random.Random(4000 + game_index)
        clocks = {chess.WHITE: 180.0, chess.BLACK: 180.0}
        engine = chess.engine.SimpleEngine.popen_uci([sys.executable, str(ROOT / "engine/main.py")], timeout=15)
        game = chess.pgn.Game()
        game.headers.update(Event="Local validation", White="Ekal Chess" if bot_colour else kind,
                            Black=kind if bot_colour else "Ekal Chess", TimeControl="180+2")
        node = game
        max_elapsed = 0.0
        reason = "move_cap"
        result = "*"
        try:
            for _ in range(args.max_plies):
                outcome = board.outcome(claim_draw=True)
                if outcome:
                    result, reason = outcome.result(), outcome.termination.name
                    break
                turn = board.turn
                started = time.perf_counter()
                if turn == bot_colour:
                    limit = chess.engine.Limit(white_clock=clocks[chess.WHITE],
                        black_clock=clocks[chess.BLACK], white_inc=2.0, black_inc=2.0)
                    if not args.official:
                        limit.time = max(0.001, args.seconds)
                    move = engine.play(board, limit, game=game_index).move
                else:
                    move = baseline(board, rng, kind)
                elapsed = time.perf_counter() - started
                max_elapsed = max(max_elapsed, elapsed)
                clocks[turn] -= elapsed
                if clocks[turn] <= 0:
                    result, reason = ("0-1" if turn else "1-0"), "time_forfeit"
                    break
                if move not in board.legal_moves:
                    raise AssertionError(f"Illegal move: {move}")
                board.push(move)
                clocks[turn] += 2.0
                node = node.add_variation(move)
            else:
                outcome = board.outcome(claim_draw=True)
                if outcome:
                    result, reason = outcome.result(), outcome.termination.name
        finally:
            engine.quit()
        game.headers["Result"] = result
        game.headers["Termination"] = reason
        game.headers["Mode"] = "official-clock" if args.official else "accelerated-move-cap"
        (args.output / f"game-{game_index + 1}.pgn").write_text(str(game) + "\n")
        record = dict(game=game_index + 1, baseline=kind, bot_colour="white" if bot_colour else "black",
                      result=result, termination=reason, plies=board.ply(),
                      max_move_seconds=round(max_elapsed, 4),
                      mode="official-clock" if args.official else "accelerated-move-cap")
        records.append(record)
        print(json.dumps(record), flush=True)
    (args.output / "summary.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
