"""Original, transparent chess heuristics. No imported engine parameters.

Scores are centipawns. Tables are generated from the formulas below rather
than copied from a published engine. All weights are untuned starting guesses.
"""
import chess

VALUES = {chess.PAWN: 100, chess.KNIGHT: 305, chess.BISHOP: 325,
          chess.ROOK: 510, chess.QUEEN: 925, chess.KING: 0}
PHASE = {chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 1,
         chess.ROOK: 2, chess.QUEEN: 4, chess.KING: 0}
MAX_PHASE = 24


def square_bonus(kind, square, endgame=False):
    """Square is oriented so our home rank is rank zero."""
    f, r = chess.square_file(square), chess.square_rank(square)
    # Integer centrality: 0 in a corner, 6 on one of the four centre squares.
    centre = min(f, 7 - f) + min(r, 7 - r)
    if kind == chess.PAWN:
        return r * (9 if endgame else 6) + min(f, 7 - f) * 3
    if kind == chess.KNIGHT:
        return centre * (6 if endgame else 11) - (15 if r == 0 else 0)
    if kind == chess.BISHOP:
        return centre * 5 + min(r, 4) * 2
    if kind == chess.ROOK:
        return (18 if r == 6 else 0) + min(f, 7 - f) * 2
    if kind == chess.QUEEN:
        return centre * (5 if endgame else 2)
    if endgame:
        return centre * 13
    return -centre * 9 - r * 7 + (30 if r == 0 and f in (1, 2, 6) else 0)


TABLES = {(kind, end): tuple(square_bonus(kind, sq, end) for sq in chess.SQUARES)
          for kind in chess.PIECE_TYPES for end in (False, True)}
PASSED_MASKS = {}
for colour in chess.COLORS:
    for sq in chess.SQUARES:
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ahead = range(r + 1, 8) if colour == chess.WHITE else range(r - 1, -1, -1)
        PASSED_MASKS[colour, sq] = sum(
            chess.BB_SQUARES[chess.square(ff, rr)] for rr in ahead
            for ff in range(max(0, f - 1), min(7, f + 1) + 1))


def evaluate_white(board):
    """Static score from White's perspective; search handles terminal states."""
    mg = eg = phase = 0
    for colour in chess.COLORS:
        sign = 1 if colour == chess.WHITE else -1
        own = board.occupied_co[colour]
        pawns = board.pawns & own
        enemy_pawns = board.pawns & board.occupied_co[not colour]
        counts = [(pawns & mask).bit_count() for mask in chess.BB_FILES]
        side_mg = side_eg = 0
        for sq in chess.scan_forward(own):
            kind = board.piece_type_at(sq)
            oriented = sq if colour == chess.WHITE else chess.square_mirror(sq)
            side_mg += VALUES[kind] + TABLES[kind, False][oriented]
            side_eg += VALUES[kind] + TABLES[kind, True][oriented]
            phase += PHASE[kind]
            if kind in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
                mobility = (board.attacks_mask(sq) & ~own).bit_count()
                weight = 3 if kind in (chess.KNIGHT, chess.BISHOP) else 2
                side_mg += mobility * weight
                side_eg += mobility * weight
            if kind == chess.PAWN:
                f = chess.square_file(sq)
                r = chess.square_rank(oriented)
                if not any(counts[ff] for ff in (f - 1, f + 1) if 0 <= ff < 8):
                    side_mg -= 12
                    side_eg -= 16
                if not (PASSED_MASKS[colour, sq] & enemy_pawns):
                    side_mg += 4 * r * r
                    side_eg += 7 * r * r
            elif kind == chess.ROOK:
                file_mask = chess.BB_FILES[chess.square_file(sq)]
                if not (file_mask & pawns):
                    bonus = 12 if file_mask & enemy_pawns else 24
                    side_mg += bonus
                    side_eg += bonus
        doubled = sum(max(0, n - 1) for n in counts)
        side_mg -= doubled * 14
        side_eg -= doubled * 20
        if (board.bishops & own).bit_count() >= 2:
            side_mg += 34
            side_eg += 45
        king = board.king(colour)
        if king is not None:
            f, r = chess.square_file(king), chess.square_rank(king)
            front = r + (1 if colour == chess.WHITE else -1)
            if 0 <= front < 8:
                side_mg += 11 * sum(bool(pawns & chess.BB_SQUARES[chess.square(ff, front)])
                                    for ff in range(max(0, f - 1), min(7, f + 1) + 1))
            for near in chess.scan_forward(chess.BB_KING_ATTACKS[king]):
                if board.is_attacked_by(not colour, near):
                    side_mg -= 9
        mg += sign * side_mg
        eg += sign * side_eg
    phase = min(MAX_PHASE, phase)
    score = (mg * phase + eg * (MAX_PHASE - phase)) // MAX_PHASE
    return score + (9 if board.turn == chess.WHITE else -9)


def evaluate(board):
    """Score from the side-to-move perspective, as required by negamax."""
    score = evaluate_white(board)
    return score if board.turn == chess.WHITE else -score
