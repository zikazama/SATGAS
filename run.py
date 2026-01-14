#!/usr/bin/env python3
"""Entry point for running SATGAS."""
import subprocess
import sys


def main():
    """Run the Streamlit application."""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/app.py",
        "--server.headless", "true"
    ])


if __name__ == "__main__":
    main()
