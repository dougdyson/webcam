#!/usr/bin/env python3
"""
Download MobileNet-SSD model files for neural presence verification.

Downloads:
  - MobileNetSSD_deploy.prototxt  (~28 KB)
  - MobileNetSSD_deploy.caffemodel (~23 MB)

Usage:
    python scripts/download_model.py
"""
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

FILES = {
    "MobileNetSSD_deploy.prototxt": {
        "url": "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt",
        "min_size": 20_000,  # ~28 KB
    },
    "MobileNetSSD_deploy.caffemodel": {
        "url": "https://raw.githubusercontent.com/PINTO0309/MobileNet-SSD-RealSense/master/caffemodel/MobileNetSSD/MobileNetSSD_deploy.caffemodel",
        "min_size": 20_000_000,  # ~23 MB
    },
}


def download_file(url: str, dest: Path) -> None:
    """Download a file with progress indication."""
    print(f"  Downloading {dest.name} ...")
    try:
        urllib.request.urlretrieve(url, str(dest))
    except Exception as e:
        raise RuntimeError(
            f"Failed to download {dest.name}: {e}\n"
            f"Manual download: {url}\n"
            f"Save to: {dest}"
        ) from e


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Model directory: {MODELS_DIR}")

    for filename, info in FILES.items():
        dest = MODELS_DIR / filename
        if dest.exists() and dest.stat().st_size >= info["min_size"]:
            print(f"  {filename} already exists ({dest.stat().st_size:,} bytes) - skipping")
            continue

        download_file(info["url"], dest)

        # Verify size
        actual_size = dest.stat().st_size
        if actual_size < info["min_size"]:
            print(
                f"  WARNING: {filename} is only {actual_size:,} bytes "
                f"(expected >= {info['min_size']:,}). File may be incomplete.",
                file=sys.stderr,
            )
        else:
            print(f"  {filename} OK ({actual_size:,} bytes)")

    print("\nDone. Models saved to:", MODELS_DIR)


if __name__ == "__main__":
    main()
