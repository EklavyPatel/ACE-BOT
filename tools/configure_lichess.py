#!/usr/bin/env python3
"""Generate a competition config from the installed official bridge template.

Does not create/upgrade accounts, send challenges, or start the bridge.
Install requirements-tools.txt or run inside the bridge's own Python venv.
"""
import argparse
import getpass
import os
from pathlib import Path
import sys


def build_config(config, project, allow, stage):
    engine = config.setdefault("engine", {})
    engine.update(dir=str(project / "engine"), name="run.sh", working_dir=str(project),
                  protocol="uci", ponder=False, uci_options={"Move Overhead": 200})
    for option in ("interpreter", "interpreter_options", "engine_options"):
        engine.pop(option, None)
    engine.setdefault("polyglot", {})["enabled"] = False
    # Fail closed for all enabled switches, including future online move sources.
    def disable(tree):
        if isinstance(tree, dict):
            for key, value in tree.items():
                if key == "enabled":
                    tree[key] = False
                else:
                    disable(value)
    disable(engine.setdefault("online_moves", {}))
    disable(engine.setdefault("lichess_bot_tbs", {}))
    engine.setdefault("draw_or_resign", {}).update(
        resign_enabled=False, offer_draw_enabled=False)
    base, increment = (180, 2) if stage == "knockout" else (600, 5)
    config.setdefault("challenge", {}).update(
        concurrency=1, accept_bot=True, only_bot=False, variants=["standard"],
        modes=["casual"], time_controls=["blitz" if stage == "knockout" else "rapid"],
        min_base=base, max_base=base, min_increment=increment, max_increment=increment,
        allow_list=allow, block_list=[], max_simultaneous_games_per_user=1)
    for key in ("online_block_list", "min_rating", "max_rating", "rating_difference"):
        config["challenge"].pop(key, None)
    config.setdefault("matchmaking", {})["allow_matchmaking"] = False
    config.setdefault("correspondence", {})["ponder"] = False
    config["greeting"] = {key: "" for key in (
        "hello", "goodbye", "hello_spectators", "goodbye_spectators")}
    config["fake_think_time"] = False
    config["max_takebacks_accepted"] = 0
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path, required=True, help="Your installed lichess-bot folder")
    parser.add_argument("--allow", nargs="+", required=True, help="Approved challenger usernames (space separated)")
    parser.add_argument("--stage", choices=["knockout", "final"], default="knockout")
    args = parser.parse_args()
    try:
        import yaml
    except ImportError:
        sys.exit("Install tools: python -m pip install -r requirements-tools.txt")
    bridge = args.bridge.expanduser().resolve()
    target = bridge / "config.yml"
    if target.exists():
        sys.exit("config.yml already exists. Back it up and remove it before generating a replacement.")
    template = bridge / "config.yml.default"
    if not template.is_file():
        sys.exit("Cannot find the official config.yml.default in that folder.")
    config = yaml.safe_load(template.read_text())
    project = Path(__file__).resolve().parents[1]
    config = build_config(config, project, args.allow, args.stage)
    token = getpass.getpass("Private bot:play token (hidden; do not use the challenge token): ").strip()
    if not token:
        sys.exit("A token is required. No file was written.")
    config["token"] = token
    # Exclusive creation and owner-only permissions from the first write.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        yaml.safe_dump(config, stream, sort_keys=False)
    print(f"Created {target}. Keep it private; never commit it.")
    print(f"Stage: {args.stage}. Allowed challengers: {', '.join(args.allow)}")
    print("The bot has NOT been started or the account upgraded.")


if __name__ == "__main__":
    main()
