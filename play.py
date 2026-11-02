#!/usr/bin/env python3
"""Play locally in a terminal. This is separate from the UCI entry point."""
import argparse
import chess
from source.search import Searcher, Limits, MATE, MAX_PLY


def main():
    parser = argparse.ArgumentParser(description="Play against Ekal Chess on this laptop")
    parser.add_argument("--black", action="store_true", help="Play as Black")
    parser.add_argument("--seconds", type=float, default=1.0, help="Bot thinking time per move")
    args = parser.parse_args()
    human = chess.BLACK if args.black else chess.WHITE
    board = chess.Board()
    print("Ekal Chess | Enter e4, Nf3, O-O, or e2e4. Commands: moves, undo, fen, quit.")
    while not board.is_game_over(claim_draw=True):
        print("\n" + board.unicode(borders=True) + "\n")
        if board.turn == human:
            try:
                text = input("Your move: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGame closed.")
                return
            if text.lower() == "quit":
                return
            if text.lower() == "moves":
                print(", ".join(board.san(move) for move in board.legal_moves))
                continue
            if text.lower() == "fen":
                print(board.fen())
                continue
            if text.lower() == "undo":
                for _ in range(min(2, len(board.move_stack))):
                    board.pop()
                continue
            try:
                move = board.parse_san(text)
            except ValueError:
                try:
                    move = board.parse_uci(text)
                except ValueError:
                    print("That move is not legal. Enter 'moves' for your options.")
                    continue
            if move not in board.legal_moves:
                print("That move is not legal.")
                continue
            board.push(move)
        else:
            seconds = max(0.01, args.seconds)
            result = Searcher().search(board, Limits(seconds * 0.75, seconds))
            if result.move is None:
                break
            if abs(result.score) > MATE - MAX_PLY:
                evaluation = "forced mate found"
            else:
                evaluation = f"{result.score / 100:+.2f} pawns from bot's perspective"
            print(f"Bot: {board.san(result.move)} | depth {result.depth} | {evaluation}")
            board.push(result.move)
    print("\n" + str(board))
    print("Result:", board.result(claim_draw=True), board.outcome(claim_draw=True))


if __name__ == "__main__":
    main()
