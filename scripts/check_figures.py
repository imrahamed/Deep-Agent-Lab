"""Validate the exported course figures and record their dimensions."""

import json
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]


def main():
    figures = sorted((ROOT / "docs/reports/figures").rglob("*.png"))
    assert figures
    records = []
    for path in figures:
        with Image.open(path) as original:
            original.load()
            image = original.convert("RGB")
        assert image.width >= 400 and image.height >= 200, path
        assert max(ImageStat.Stat(image).stddev) > 5, path
        records.append(
            {
                "figure": path.relative_to(ROOT).as_posix(),
                "width": image.width,
                "height": image.height,
                "status": "passed",
            }
        )
    (ROOT / "docs/reports/figures.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Validated {len(records)} nonblank course figures.")


if __name__ == "__main__":
    main()
