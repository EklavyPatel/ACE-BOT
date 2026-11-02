# Local validation record

Test date: 2 November 2026. Host: Linux, CPython 3.12.14, chess 1.11.2.
The host is not the user's laptop, so timings are not laptop performance guarantees.

## Automated suite

**17 / 17 tests passed** using the project's installed `.venv`.

Coverage: mirrored colour evaluation; balanced starting position; mates and free
queen captures for both colours; node/time/cancel fallback with exact board
restoration; checkmate precedence over draw counters; repetition and fifty-move
positions; quiet check evasions in quiescence; alpha-beta scores compared with
exhaustive search on a small position; clock-side selection and tiny budgets;
real-client UCI handshake, setoption, castling, en passant, promotion, game
resets and black clocks; atomic position parsing; responsive infinite/stop and
isready handling; terminal null move and clean stdout; restricted bridge
configuration for knockout and final stages.

Additional integration checks passed:

- `bash setup.sh` installed the dependency into a fresh project environment.
- Shell syntax and Python compilation passed.
- Terminal practice game accepted `e4`, returned a legal reply, and quit cleanly.
- `engine/run.sh` launched through a real UCI client from a different directory.
- Config generation against the official bridge's current template succeeded;
  the generated file had 0600 permissions and correct engine/challenge fields.
  A fake test token was used. No real account or token was accessed.

## Games through the actual UCI entry point

Each move was validated before being played. Clocks were tracked. The baselines
are deliberately simple local implementations, not existing chess engines.
All six games ended in checkmate wins for Ekal Chess, without an illegal move,
engine crash, or time forfeit.

| Mode | Opponent | Ekal colour | Result | End reason | Plies | Longest move (s) |
|---|---|---|---|---|---:|---:|
| accelerated-move-cap | random | white | 1-0 | CHECKMATE | 31 | 0.0910 |
| accelerated-move-cap | random | black | 0-1 | CHECKMATE | 70 | 0.0951 |
| accelerated-move-cap | greedy | white | 1-0 | CHECKMATE | 13 | 0.0875 |
| accelerated-move-cap | greedy | black | 0-1 | CHECKMATE | 28 | 0.0872 |
| official-clock | random | white | 1-0 | CHECKMATE | 17 | 10.3148 |
| official-clock | random | black | 0-1 | CHECKMATE | 16 | 10.3126 |

The four accelerated games used a 100 ms per-move cap, in addition to simulated
180+2 clocks. The other two games used actual 180+2 clock allocation, with no
per-move cap. The complete PGNs and JSON records are included under `output/`.
These games and four weak-baseline wins are not an Elo estimate or evidence of
strength against other competition entrants. The two additional full-clock
wins test clock handling, not strong-opponent performance.

## Short search measurements

On this build host, an initial-position search completed depth 4 with 8,172
visited nodes in a 1.0-second hard budget. A developed middlegame completed
depth 3 with 6,692 nodes in about 0.855 seconds. Completed depth varies with
position and machine. These samples are not a sustained benchmark.

## What remains unverified

- The user's laptop, Python 3.14 environment, CPU speed, and network.
- A real Lichess bot login, account upgrade, bridge connection, and online game.
- Longer stress runs, strong opponents, or an Elo rating.
- Organisers' interpretation of the competition's own-work rule for this
  explicitly AI-assisted project.
