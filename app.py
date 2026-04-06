"""Compatibility ASGI entrypoint.

This shim keeps `uvicorn app:app` working by booting the v2 app from `src/dailyai`.
Preferred command remains: `uv run dailyai`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src-layout imports work when launched as `uvicorn app:app`
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dailyai.ui.app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
    )
