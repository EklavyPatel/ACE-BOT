#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
chmod +x engine/run.sh
echo "Ready. Test with: .venv/bin/python -m unittest discover -s tests -v"
echo "Play with: .venv/bin/python play.py"
