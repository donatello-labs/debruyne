"""Single source of truth for package/release version (SemVer)."""

from pathlib import Path

__version__ = (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()
