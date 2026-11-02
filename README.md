# ACE-BOT

A CPU-based classical chess engine for **Chess Engine Clash-Off**, organised by AI Club × DAU Chess Club. This is the reviewed Ekal Chess implementation, submitted as ACE-BOT. Its UCI identity remains `Ekal Chess 1.0`; the core code has not been changed for repository upload.

| Submission detail | Value |
|---|---|
| Participant | **Eklavy Patel** — solo participant |
| Lichess bot username | **[EklaVyPaTeL1](https://lichess.org/@/EklaVyPaTeL1)** |
| Repository | https://github.com/EklavyPatel/ACE-BOT |
| Exact launch command | **`./engine/run.sh`**, from the repository root after setup |
| Approach | Negamax / alpha-beta search with hand-crafted evaluation |
| Participant's environment | Ubuntu Linux, Python **3.14**, as shown in laptop installation output |
| Automated validation environment | Linux, CPython **3.12.14**, `chess==1.11.2` |
| Hardware | CPU; no GPU, trained model or database required |

The participant reported a successful BOT upgrade, connection and practice play on Lichess. Published automated measurements below were obtained on the development host, not the competition laptop. No Elo rating is claimed.

## Install and launch

```bash
git clone https://github.com/EklavyPatel/ACE-BOT.git
cd ACE-BOT
bash setup.sh
.venv/bin/python -m unittest discover -s tests -v
```

The source requires Python 3.10+ syntax. It was automatically tested on 3.12.14; the participant's laptop uses 3.14. If venv creation reports that ensurepip is unavailable, install the Ubuntu venv package matching your Python version. The separately installed bridge has its own Python requirements.

**Tournament engine launch command**, from the repository root after setup:

```bash
./engine/run.sh
```

Equivalent explicit command:

```bash
.venv/bin/python engine/main.py
```

The launcher uses the project's `.venv` and resolves imports relative to the project. There are no model, weight or external data files to load.

For a smoke check, start the engine, then enter these commands separately, waiting for `bestmove` after `go`:

```text
uci
isready
position startpos moves e2e4 e7e5
go movetime 1000
quit
```

For local terminal practice:

```bash
.venv/bin/python play.py
.venv/bin/python play.py --black --seconds 2
```

Moves can be SAN (`e4`, `Nf3`, `O-O`) or coordinates (`e2e4`). Commands include `moves`, `undo`, `fen` and `quit`. This practice interface is separate from the tournament UCI entry point.

## Approach summary

`python-chess` provides board rules, legal move generation, attacks, and make/unmake operations. It does not select the engine's moves. Search and evaluation are implemented in this repository.

- **Negamax and alpha-beta:** recursively consider both sides' replies, scoring from the side-to-move perspective and pruning branches that cannot improve the result.
- **Iterative deepening:** searches increasing depths. Only a completed iteration replaces the best move; a legal fallback is available immediately.
- **Move ordering:** previous best move, cached moves, captures/promotions, killer moves and history-scored quiet moves.
- **Quiescence:** examines captures and promotions beyond normal depth, including quiet promotions. All legal evasions are searched when in check, and stalemate is checked before static evaluation.
- **Hand-crafted evaluation:** material, formula-generated square bonuses, mobility, pawn structure, passed pawns, bishop pair, rook files, king shelter and king-neighbour attacks. Middlegame and endgame values are blended according to remaining material.
- **Caches:** a bounded history-aware transposition cache plus a bounded cache of the static evaluation formula. History-dependent draw/mate outcomes are checked before using static evaluation.
- **Time management:** side-specific clock and increment allocation, soft/hard search deadlines, interruption with board restoration, and configurable `Move Overhead`.

Checkmate scores dominate ordinary evaluation; shorter mates are preferred. Draw counters and repetition history are considered. The bridge and Lichess handle actual game termination. A position with no legal moves produces UCI `bestmove 0000`.

No neural network is used, so there is no training code or training dataset. Evaluation constants are hand-chosen, untuned guesses. Piece-square bonuses come from the visible formulas in `source/evaluation.py`, rather than copied engine tables.

## UCI and dependencies

Implemented: `uci`, `isready`, `ucinewgame`, `position startpos`, `position fen` with moves, `go` including `wtime`, `btime`, `winc`, `binc`, and `quit`. Additional controls include `stop`, `movetime`, `depth`, `nodes`, `movestogo`, `searchmoves`, `infinite` and `Move Overhead`.

The command reader remains responsive during search. Only UCI responses go to stdout; diagnostics go to stderr. Pondering is not advertised and must stay disabled. `go mate` is parsed but does not implement a dedicated mate-limited search. The info PV contains only the selected root move.

- Engine dependencies: [`requirements.txt`](requirements.txt), `chess==1.11.2`.
- Optional configuration tooling: [`requirements-tools.txt`](requirements-tools.txt), also installs `PyYAML==6.0.3`.
- The official lichess-bot bridge is installed separately with its own requirements.

## Lichess setup and competition settings

See [LICHESS_SETUP.md](LICHESS_SETUP.md). With the official bridge installed in a sibling `lichess-bot` folder:

```bash
.venv/bin/python -m pip install -r requirements-tools.txt
.venv/bin/python tools/configure_lichess.py --bridge ../lichess-bot --stage knockout --allow ORGANISER_USERNAME APPROVED_OPPONENT_USERNAME
```

Replace the username placeholders with the actual approved challengers. The helper asks for the private `bot:play` token with hidden input, writes the local bridge configuration and refuses to overwrite an existing file. The engine remains offline; the bridge provides Lichess game transport.

For competition, use standard chess, casual games, the approved challengers allowlist, and the appropriate stage time control: **3+2 knockout**, **10+5 final**. Disable online move sources, local books, tablebases, pondering and automatic matchmaking. The helper generates exact stage-specific challenge filters. Adjust bridge filters between stages as necessary while keeping the submitted engine code identical.

Open public challenges and multiple simultaneous games are practice settings; restore the required challenger restrictions before a competition round. The participant hosts the bot on their own hardware and keeps it powered, awake and connected. No human may make moves for the bot or alter, restart or advise the agent during a tournament game.

**Neither token belongs in this repository.** Keep the `bot:play` token private. Submit the separate `challenge:write` token only through the organisers' designated private channel. Live `config.yml`, its backups, secrets and virtual environments are excluded.

## Validation

The reviewed revision passed **22 automated tests**, including legal special moves, mate detection for both colours, draw history, interruption/board restoration, quiescence check evasions, alpha-beta comparison with a small exhaustive search, low-clock handling, real-client UCI integration and static-cache behaviour.

Eight fixed-depth positions returned identical moves and scores to the original. One development-host depth-3 run took **2.251 s original / 1.497 s reviewed** (about 33.5% less total elapsed time). This small sample is not a guarantee across positions or hardware.

Eight paired games against the original, with colours reversed and **100 ms requested per move for both engines**, produced:

| Wins | Draws | Losses | Unfinished |
|---:|---:|---:|---:|
| 6 | 1 | 1 | 0 |

No illegal moves, crashes or engine timeouts occurred. Neither version exceeded its requested budget by more than 50 ms, although some whole-request wall times exceeded 100 ms including scheduling and communication overhead. This reviewed-vs-original match was not a full 3+2 match. Older full-clock records in `VALIDATION.md` concern the original version only.

See [REVIEW.md](REVIEW.md) for findings, limitations, isolated patches and reproduction details. PGNs and raw results are in [`output/review/`](output/review/). Eight short games against one opponent do not establish an Elo rating or general tournament strength. Remaining limitations include quiet-check coverage, absolute search bounds and conservative repetition-aware cache reuse.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/compare_versions.py --original baseline --seconds 0.1 --output output/repeat
```

The original implementation is preserved in `baseline/` with checksums in the review records. Its documentation is historical; this root README contains the current submission details.

## AI assistance and declared sources

**OpenAI ChatGPT/Codex substantially assisted with writing, debugging, reviewing and improving this project.** Core search and evaluation were written for this project. No existing chess-engine implementation, pretrained engine weights, published engine evaluation tables, or engine-generated analysis was copied or used. Comparisons use this project's own original version or simple locally written baselines.

The organisers clarified by email to the participant that LLM assistance is permitted when the chess intelligence is original, prohibited engine resources are not used, the agent operates independently during games, assistance is disclosed, and the participant can explain the implementation. This disclosure is retained. Eklavy Patel is responsible for understanding and explaining the submitted algorithms and evaluation.

Declared utilities and learning references:

- The supplied **Competition Guidelines for Competitors** and **How to Build a Chess Agent**: competition requirements and standard algorithm concepts. No existing engine search/evaluation code was imported.
- [python-chess documentation](https://python-chess.readthedocs.io/en/latest/): board rules, move generation and UCI client interfaces. Tests use its UCI client to communicate with this project's engine; no external chess engine is invoked.
- [Official lichess-bot](https://github.com/lichess-bot-devs/lichess-bot): the separately installed bridge and configuration schema used by the helper.
- [PyYAML](https://pyyaml.org/): optional configuration serialization utility.

No third-party engine source, engine training data, weights, opening books or tablebases are included.

## Repository layout

```text
ACE-BOT/
  engine/                 launch wrapper and UCI entry point
  source/                 complete search, evaluation and UCI source
  tests/                  automated tests
  tools/                  configuration, validation and comparison tools
  baseline/               preserved original implementation
  output/                 recorded development validation evidence
  play.py                 terminal practice interface
  setup.sh                virtual environment setup
  requirements.txt        engine dependencies
  requirements-tools.txt  optional tool dependencies
  README.md               submission details and disclosures
  REVIEW.md               engineering review and paired results
  LEARN_THE_ENGINE.md      explanations for participant preparation
  LICHESS_SETUP.md         bridge setup instructions
```
