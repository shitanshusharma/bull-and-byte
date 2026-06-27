#!/usr/bin/env python3
"""Entry point shim. Real logic lives in the ``src`` package.

Kept so ``python bot.py`` (and the GitHub Actions workflow) continue to work
unchanged after the move to a package layout.
"""

import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
