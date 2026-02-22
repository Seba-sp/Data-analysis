#!/usr/bin/env python3
"""Simple launcher for CL Streamlit app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    app_path = Path(__file__).parent / "app.py"
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.headless", "true", "--server.port", "8501"],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"Error launching Streamlit: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
