#!/usr/bin/env python
"""Generate platform desktop icons from the project logo."""
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "logo.png"
OUT_DIR = ROOT / "build" / "desktop-icons"
ICO_PATH = OUT_DIR / "logo.ico"
ICNS_PATH = OUT_DIR / "logo.icns"


def generate_desktop_icons() -> tuple[Path, Path]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing source logo: {SOURCE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image = Image.open(SOURCE).convert("RGBA")
    image.save(
        ICO_PATH,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    image.save(
        ICNS_PATH,
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512)],
    )
    return ICO_PATH, ICNS_PATH


if __name__ == "__main__":
    ico_path, icns_path = generate_desktop_icons()
    print(f"[icons] Windows icon: {ico_path}")
    print(f"[icons] macOS icon: {icns_path}")
