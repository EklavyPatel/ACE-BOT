#!/usr/bin/env python3
"""Single-command entry point; imports always resolve relative to this file."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source.uci import UCI

if __name__ == "__main__":
    UCI().run()
