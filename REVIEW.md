> Historical review: the organisers subsequently approved LLM assistance under the conditions stated in the current README. Engine logic was not changed for repository upload.

# Ekal Chess: engineering review and measured revision

Reviewed 2 November 2026 on Linux / Python 3.12.14, chess 1.11.2.
The uploaded archive is preserved byte-for-byte by file under `baseline/` (excluding generated Python bytecode). Its source checksums are in `output/review/baseline-sha256.json`. This revision retains the original AI-assistance disclosure.

## Decision

Keep two small, measured speed improvements. The evaluation formula, score perspective, depth limits, clock policy, legal move rules and history-sensitive draw handling are unchanged. No external engine code, engine analysis, weights, opening books, tablebases, or live services were used. All comparison opponents were the supplied original engine.

## Priorities and findings

| Priority | Finding | Benefit / risk | Action |
|---|---|---|---|
| 1 | Quiescence eagerly enumerated all legal moves at every leaf, including quiet moves discarded immediately afterward. | High expected CPU saving; low risk if stalemate, check evasions and promotions are retained. | Fixed: cheap terminal probe, captures generated directly, quiet promotions added separately. All legal evasions retained in check. |
| 2 | Static evaluation repeatedly recomputed identical board scores reached through different move orders. | Useful CPU saving; low risk only if cached scores exclude history-dependent game outcomes. | Fixed: bounded 16,000-entry static cache, cleared for each search. Draw/mate checks occur first; turn is in the key. |
| 3 | Exact search-cache keys copy the entire repetition-count context into a frozenset. This costs allocation and prevents many otherwise useful transposition hits. | Potentially large benefit, medium/high correctness risk if draw history is ignored. | Retained for safety. A future change can share move-order hints independently of cached scores. |
| 4 | No quiet checking moves in quiescence; no check extensions or deeper tactical regression suite. Depth-bound tactical threats can remain unseen. | Potential tactical benefit, medium/high search-explosion and timing risk. | Deferred. Added a poisoned-capture regression, without extending the tree. |
| 5 | Time control starts a new depth until the soft threshold, then can consume the hard allowance. Root setup, worker scheduling, IPC and stdout are outside portions of the search budget. | High operational importance; real laptop/network measurements required. | Retained the tested policy and its safety reserve. Measured wall-clock overhead explicitly; do not set tournament overhead to zero. |
| 6 | At absolute MAX_PLY, evaluation can score a checked position; quiet quiescence also stops at its depth cap. | Rare correctness approximation, but removing bounds risks runaway searches. | Documented and retained. No manifestation observed in these tests. |
| 7 | Floor division in tapered evaluation can make colour inversion differ by one centipawn. | Very small evaluation bias, low implementation risk. | Left unchanged to isolate performance changes; existing mirror test tolerates one centipawn. |
| 8 | UCI parses `go mate` but does not implement that search constraint; pondering is not advertised. | Low priority for the required tournament protocol. | Documented existing limitation. Keep pondering disabled. |

No demonstrated legality, ordinary checkmate-precedence, board-restoration or required-UCI failure was found. This is a bounded review, not proof that the engine has no bugs. The initial tests mainly covered mate-in-one and basic material tactics; they did not establish competitive chess strength.

## Changes and checks, in order

1. Original upload: all 17 existing tests passed.
2. Selective quiescence: all 17 tests passed. The isolated diff is included.
3. Static-only evaluation cache: all 17 tests passed. The isolated diff is included.
4. Five regressions added: quiet quiescence promotion, stalemate before cached evaluation, static cache reuse and side-to-move separation, fifty-move draw precedence over cached material, and avoiding a queen capture of a protected rook. **22/22 tests passed**.
5. Eight fixed-depth positions: every selected move and root score matched the original. Depth 3 aggregate time: original **2.251 s**, candidate **1.497 s** (~33.5% less elapsed time, or 1.50x throughput on this small sample). This is one sequential run, not a statistically controlled hardware benchmark. Raw FENs, outputs and reproduction script are included.

Profiling the original at starting-position depth 4 attributed about 45% of profiled cumulative runtime to evaluation and 32% to legal move generation. Profiler overhead and this particular position affect those figures.

## Equal-time paired games

Four deterministic test fixtures, each played twice with candidate colours reversed, for eight games total. Fixtures were the normal initial position and three short manually specified legal move sequences. These are offline test starting positions, not books accessed during play. All fixtures and match code are included.

Both engines used one search worker, the same Python runtime, **100 ms requested thinking time per move**, and `Move Overhead = 0` solely for the comparison. Processes searched sequentially on the same host. No resignations or evaluation-based adjudication. Standard game endings were checked with draw claims enabled. A 240-ply cap would be marked unfinished.

**Candidate: 6 wins, 1 draw, 1 loss, 0 unfinished games.**

| Fixture | Candidate as White | Candidate as Black |
|---|---|---|
| Initial position | Win | Loss |
| e4 e5 | Win | Win |
| d4 d5 c4 e6 | Win | Win |
| Nf3 Nf6 g3 g6 | Draw | Win |

**Failures:** zero illegal moves, zero engine exceptions/timeouts, zero wall-clock responses more than 50 ms beyond the requested budget for either engine. The maximum measured whole-request wall time was 125.5 ms for the candidate and 128.2 ms for the original. Therefore strict 100 ms wall deadlines were not uniformly met: these measurements include scheduling and IPC overhead. No actual 3+2 match between versions was run in this review; the older full-clock tests belong to the original version only.

All PGNs and detailed per-game JSON are under `output/review/`. Eight short games against one opponent are promising evidence, not statistical proof of overall strength. Fixed-depth equivalence shows unchanged decisions on the tested positions, not all positions. Timing-dependent outcomes can vary by CPU and load. No Elo is claimed.

## Use and reproduce

From this folder:

```bash
bash setup.sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python play.py
.venv/bin/python tools/compare_versions.py --original baseline --seconds 0.1 --output output/repeat
```

To compare at a longer budget, repeat with `--seconds 1`. Keep the laptop plugged in, close heavy applications, and run no other benchmarks during the games. Re-test the Lichess bridge and clocks on your actual laptop before a tournament.

Original launcher for rollback: `.venv/bin/python baseline/engine/main.py`.
Revised launcher: `.venv/bin/python engine/main.py` or `./engine/run.sh` after setup.
The baseline wrapper expects its own venv, so use the explicit Python command above for rollback with the revised project's environment.

The competition's AI-assistance question remains unchanged. Both implementations disclose Codex assistance; this review does not change eligibility or remove the disclosure.
