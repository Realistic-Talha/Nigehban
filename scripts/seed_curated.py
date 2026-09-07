"""Seed curated references only (run from repo root)."""

import asyncio
import os
import sys

API_DIR = os.path.join(os.path.dirname(__file__), "..", "apps", "api")
sys.path.insert(0, API_DIR)
os.chdir(API_DIR)

from scripts.seed_all import seed_curated  # noqa: E402


def main() -> None:
    n = asyncio.run(seed_curated())
    print(f"Seeded {n} curated references")


if __name__ == "__main__":
    main()
