from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    base = Path("apps/api")
    if not base.exists():
        raise SystemExit(f"{base} does not exist")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and name != "__pycache__"
        ]
        for filename in filenames:
            if filename.startswith(".") or filename.startswith("__"):
                continue
            path = Path(dirpath) / filename
            print(path.relative_to(base))


if __name__ == "__main__":
    main()
