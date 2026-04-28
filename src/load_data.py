"""
Legacy entry point - retained for backwards compatibility.

All logic now lives in ``services.data_loader``. This file simply forwards
the CLI invocation so existing scripts/docs ("python src/load_data.py") keep
working.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.data_loader import main  # noqa: E402

if __name__ == "__main__":
    main()
