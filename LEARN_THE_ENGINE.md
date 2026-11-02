# Explain your engine in five minutes

Start with these explanations, then read the linked functions in your editor.
Be able to trace a small position yourself; memorising terms is not enough.

## What is the engine's actual intelligence?

`python-chess` supplies legal moves and chess rules. Our own evaluation scores
positions and our own search selects among those legal moves. The library does
not tell the bot which move is strongest.

## What is minimax / negamax?

Imagine checking each of your moves and the opponent's strongest reply. Choose
the move whose worst reply gives you the best outcome. Negamax writes this
symmetrically: a good score for the opponent is a bad score for you, so negate
the score on each turn. All search evaluation scores are from the side to move.

Trace: your move A allows replies scoring +4 and -3 for you. Your move B allows
+1 and +2. A rational opponent chooses -3 after A, or +1 after B. You choose B.

Read: `Searcher.negamax` in `source/search.py`.

## Why alpha-beta?

If another move already guarantees +1, and one opponent reply holds your new
candidate to -3, searching the remaining replies cannot make that candidate
better against a rational opponent. Skip them. Alpha-beta improves efficiency;
it does not deliberately throw away potentially better moves. Move ordering
makes these cutoffs happen earlier.

## What does depth mean?

One ply is one move by one side. Depth 4 ordinarily covers your move, the
opponent's move, your next move, and their next move. Quiescence can continue
beyond that depth in exchanges. Actual completed depth depends on the position
and hardware, so the program reports measured depth instead of promising one.

## What does evaluation measure?

100 centipawns is approximately one pawn. Our score combines material and
positional guesses: central knights, active pieces, healthy pawns, passed pawns,
safe middlegame kings, and active endgame kings. None of these numbers is a
confidence percentage or a proven probability of winning. The values are
untuned heuristics and can be wrong.

Read: `evaluate_white` and `square_bonus` in `source/evaluation.py`.

## Why not stop exactly at the depth limit?

Stopping halfway through a capture exchange can make a losing capture look
profitable. Quiescence searches captures and promotions until the position is
quieter. When in check, it must consider all legal escapes, not pretend the king
can stay put. Bounds prevent unbounded extra search.

## How do we avoid losing on time?

The bot has a legal fallback immediately. Iterative deepening saves only fully
completed iterations. A stop event and hard deadline interrupt recursion, with
`finally` blocks always restoring the board. Clock allocation reserves overhead
and uses the correct side's time and increment. This reduces risk but cannot
guarantee against operating-system stalls, disconnection, or laptop sleep.

Read: `allocate_time` in `source/uci.py` and `Searcher.search`.

## What is UCI?

It is a text protocol, not an API requiring an internet connection. The bridge
sends a position and clock values; the engine returns `bestmove e2e4`, for
example. Only the bridge talks to Lichess. The engine itself stays offline.

## What should we improve after testing?

Change one thing at a time and compare full games with both colours. A bigger
evaluation function can make the bot slower and shallower. More features do
not automatically mean better chess. Keep improvements only when game results
and tactical checks support them. Do not import external engine code, weights,
analysis, opening books, or tablebases.

## Questions to practise answering

1. Why must scores change sign after switching sides?
2. How can alpha-beta skip a branch without changing minimax's result?
3. What happens if the clock expires halfway through depth 5?
4. Why is standing pat forbidden when your king is in check?
5. Why can the same board have a different draw status with different history?
6. Which parts did your team understand, implement, change, and test? Disclose
   the Codex-assisted starting implementation honestly.
