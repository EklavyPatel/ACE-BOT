# Ubuntu: connect the engine to Lichess

The engine works locally already. These steps require your own accounts and
network and have **not** been carried out automatically.

## 1. Prepare the local engine

In `ACE-BOT`:

```bash
bash setup.sh
.venv/bin/python -m unittest discover -s tests -v
./engine/run.sh
```

Enter `uci`, wait for `uciok`, then enter `quit`.

## 2. Account and tokens

Follow the supplied competition guidelines:

1. Create a dedicated unused Lichess account identifying the team. It must never
   have played a game before the bot upgrade.
2. In Preferences > API access tokens, create a token with **bot:play only**.
   Keep it private. The config helper asks for it with hidden input; never type
   it into a shell command that will be saved in command history.
3. Later, create a different token with **challenge:write only** for submission
   to the organisers. This is not the token used in the bridge config.

## 3. Install the official bridge

Use a separate folder next to this project:

```bash
cd ..
git clone https://github.com/lichess-bot-devs/lichess-bot.git
cd lichess-bot
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Use the Python version supported by the bridge's current README if installation
reports a Python-version mismatch. The bridge is maintained separately from
this engine. Do not install another chess engine or enable its move sources.

## 4. Generate the restricted config

Return to `ACE-BOT`, install the optional config tool dependency, then run:

```bash
cd ../ACE-BOT
.venv/bin/python -m pip install -r requirements-tools.txt
.venv/bin/python tools/configure_lichess.py --bridge ../lichess-bot --stage knockout --allow YOUR_PERSONAL_USERNAME
```

Replace `YOUR_PERSONAL_USERNAME` with your real personal account username so you
can test by challenging the bot from that account. The helper reads the
official bridge's current `config.yml.default`, sets the engine paths for this
laptop, prompts for your private bot token, and creates an owner-readable-only
`config.yml` inside the bridge folder. It never replaces an existing config.

The generated configuration:

- Enables standard chess, casual games, and exactly **180 seconds + 2 seconds**.
- Accepts only the usernames supplied after `--allow`.
- Disables all online move sources, local books/tablebases, automatic
  matchmaking, pondering, draw offers, resignations, and greeting messages.
- Uses one concurrent game and the engine's relative launcher.

Before competition, replace the practice allowlist with all organiser usernames
and eligible competing bots supplied by the organisers. A missing username
will cause that challenge to be declined. Ensure every required challenger is
listed and do not leave the practice account as the only allowed challenger.

## 5. Upgrade the account and run

Only after you have chosen the dedicated unused bot account, run from the
bridge folder:

```bash
cd ../lichess-bot
.venv/bin/python lichess-bot.py -u
```

The upgrade is **permanent**; that account cannot return to ordinary human play.
Read the bridge's current prompts. Then start it normally:

```bash
.venv/bin/python lichess-bot.py
```

Challenge it from the allowlisted personal account: standard chess, casual,
3+2. Finish a full game. Confirm there are no start failures, illegal moves,
unanswered challenges, or time forfeits. Increase `Move Overhead` and/or the
bridge's `move_overhead` if your machine or network needs more margin.

## 6. Tournament day and final stage

Keep the laptop powered, connected, awake, and running the bridge for the
entire round. Once a game starts, do not alter, restart, or advise the agent.
Do not make human moves on the bot account. Matchmaking stays off.

The final stage uses exactly **600 seconds + 5 seconds**. Between rounds, with
no game running, edit only the bridge challenge filters:

```yaml
challenge:
  min_base: 600
  max_base: 600
  min_increment: 5
  max_increment: 5
  time_controls: [rapid]
```

Preserve all other fields, update the allowlist to include the approved chess
club members, and keep the submitted engine code identical. Alternatively,
back up and remove `config.yml` locally, then regenerate it using `--stage final`
and the complete approved allowlist. Do not upload the backup: it contains a
private token.

Reference: https://github.com/lichess-bot-devs/lichess-bot
