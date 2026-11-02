# Ekal Chess

A small, CPU-only classical chess bot for learning and preparation for the
uploaded Chess Agent Competition. Working implementation of **Way 3 + Way 4**:
alpha-beta search with an explainable, hand-crafted evaluation.

**Status:** locally tested prototype. No Lichess account has been created,
upgraded, or connected. There is no measured Elo or tournament-strength claim.

## Start on Ubuntu

Extract this project, open a terminal inside `ekal-chess`, then run:

```bash
bash setup.sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python play.py
```

You play White by default. Enter moves like `e4`, `Nf3`, `O-O`, or `e2e4`.
Enter `moves` to list legal moves, `undo` to undo a move pair, or `quit` to exit.
Pawn promotions can be entered as `e7e8q` (queen), `e7e8n` (knight), etc.

To play Black or give the bot more thinking time:

```bash
.venv/bin/python play.py --black --seconds 2
```

The terminal game is a practice interface, not the tournament clock or UCI
entry point. It does not need an API key, database, GPU, or network during play.

If venv creation reports that `ensurepip` is unavailable, install the matching
Ubuntu venv package (usually `sudo apt install python3-venv`; for a separately
installed Python 3.14, use its corresponding `python3.14-venv` package).

## Exact tournament launch command

From the project root, after setup:

```bash
./engine/run.sh
```

Or run directly with an environment containing the requirements installed:

```bash
python3 engine/main.py
```

The wrapper always uses this project's `.venv`, irrespective of which other
environment lichess-bot uses. Paths resolve relative to the script, so the
engine can be launched with another working directory.

**Python:** tested with CPython 3.12.14 on Linux. Source requires Python 3.10+.
Other versions, including the team's Python 3.14, must be tested on the actual
laptop. Runtime dependency: `chess==1.11.2`; tools optionally use PyYAML.

## How the bot decides

1. `python-chess` provides board rules, attacks, legal moves, and make/unmake.
2. Negamax expresses the two sides' minimax choices using a consistent
   side-to-move score. Alpha-beta skips branches that cannot improve the choice.
3. Iterative deepening completes depth 1, then depth 2, and so on. Only a fully
   completed iteration replaces the selected move. A legal fallback exists
   before any search begins.
4. Ordering tries the previous root choice, cached moves, captures/promotions,
   killer moves, and history-scored quiet moves first.
5. Quiescence continues captures and promotions at leaf positions. In check it
   searches every legal evasion and does not use stand-pat. Quiet quiescence is
   capped at 12 extra plies; the absolute search safety bound is 96 plies.
6. Evaluation blends middlegame and endgame scores. Features include material,
   generated square bonuses, attack-based mobility, doubled/isolated/passed
   pawns, bishop pair, open rook files, king shelter, and attacked king neighbours.
7. A bounded transposition cache stores depth, score bounds, and moves. Cache
   keys include halfmove and repetition history, deliberately trading cache hit
   rate for avoiding history-dependent draw errors.
8. Clock allocation uses the correct side's remaining time and increment. A
   soft deadline ends iterative deepening; a hard deadline interrupts search.
   `Move Overhead` reserves time for handling the move; lichess-bot also has a
   separate network overhead setting. The right values depend on the laptop
   and connection and require a real practice game.

Checkmate scores dominate ordinary material; shorter mates are preferred.
Search values current threefold repetitions and 100-halfmove positions as draws
(after checking for checkmate). The bridge/server handles actual draw claims and
game termination. A root position with legal moves still returns a legal move,
even when a draw is available. UCI `0000` is returned when there is no legal move.

There is no neural network, training dataset, opening book, tablebase, external
engine, online move source, or external API in move selection. The square
tables are chess heuristics, not a stored opening move lookup.

## UCI support

Implemented: `uci`, `isready`, `ucinewgame`, `position startpos`, `position fen`
with move history, `go` with clocks/increments, `movestogo`, `movetime`, `depth`,
`nodes`, `searchmoves`, `infinite`, `stop`, `setoption` for `Move Overhead`, and
`quit`. Search runs in a worker so readiness and stop commands remain responsive.
Only UCI responses go to stdout; malformed-input diagnostics go to stderr.
Pondering is not advertised and must stay disabled in lichess-bot.
`go mate` is parsed but does not implement a separate mate-limited search mode.
The info PV currently reports only the selected root move, not the entire line.

For an interactive protocol check, start `./engine/run.sh`, then enter these
commands one at a time, waiting for `bestmove` after `go`:

```text
uci
isready
position startpos moves e2e4 e7e5
go movetime 1000
quit
```

## Local validation

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/validate.py --games 4 --seconds 0.1
```

The game runner uses this project's own random and greedy baselines, not an
external engine. It launches the bot through a real UCI client, validates every
move, tracks clocks, and saves PGNs and JSON under `output/validation`.
That command accelerates testing by imposing a 100 ms move cap; it is **not** a
full tournament timing test. To use actual 180+2 clock allocation instead:

```bash
.venv/bin/python tools/validate.py --official --games 2 --output output/official-clock
```

A game reaching the configured move cap is recorded as unfinished (`*`), not
counted as a win or a draw. Check `VALIDATION.md` and the bundled game records
for the results actually obtained in this build environment.

## Connect through lichess-bot

See `LICHESS_SETUP.md` for account and token steps, bridge installation,
competition allowlists, and separate 3+2 / 10+5 configurations. Run a complete
practice game on your own laptop before the tournament. Local UCI tests do not
establish that account permissions, network, and server integration work.

## Submission and authorship disclosure

**This project was substantially implemented with OpenAI Codex assistance.**
The core search and evaluation were written for this project; no existing
engine implementation or published piece-square table was copied into them.
The classical algorithm concepts are standard and are described in the supplied
build guide. Initial piece values and heuristic weights here are hand-selected,
untuned guesses, not parameters learned from another engine.

The competition rules say the team's chess intelligence must be its own work;
they do not explicitly settle AI-assisted development. **Ask the organisers
whether this level of AI assistance is acceptable before submitting.** Keep this
disclosure, explain your actual contributions, understand the implementation,
and do not present generated code as solely human-written work.

External utilities and references:

- `python-chess` rules, board, and UCI client documentation:
  https://python-chess.readthedocs.io/en/latest/core.html
  and https://python-chess.readthedocs.io/en/latest/engine.html
- Official lichess-bot bridge and configuration schema, used for the config tool:
  https://github.com/lichess-bot-devs/lichess-bot
- The two supplied competition PDFs. The rules take precedence over suggestions
  in the build guide if they conflict (for example, importing engine parameters).

No training code is needed because this version does not train a model. Complete
engine source is included in `source/` and the entry point in `engine/`.

Before submission, update these fields:

- Team name: **TO FILL IN**
- Team members: **TO FILL IN**
- Lichess bot username: **TO FILL IN**
- Actual Python version used on the competition laptop: **TO FILL IN**
- Organisers' decision on AI assistance: **TO CONFIRM**

Submit the GitHub repository link, bot username, and separate `challenge:write`
token through the organisers' designated channel. Never put either token in a
public README, repository, screenshot, or chat transcript. The `bot:play` token
remains private to your team. Freeze the submitted engine for both stages.
