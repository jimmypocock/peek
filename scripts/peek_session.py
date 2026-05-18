#!/usr/bin/env python3
"""peek_session — entry point for the /peek slash command.

Real implementation lives in the `peek/` package next to this file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from peek.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
