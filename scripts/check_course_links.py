"""Validate local Markdown links in course documents and notebook reading cells."""

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    problems = []
    count = 0
    paths = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "notebooks").rglob("*.md")),
        *sorted((ROOT / "notebooks").rglob("*.ipynb")),
    ]
    for path in paths:
        if path.suffix == ".ipynb":
            data = json.loads(path.read_text(encoding="utf-8"))
            text = "\n".join(
                "".join(cell["source"]) for cell in data["cells"] if cell["cell_type"] == "markdown"
            )
        else:
            text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("http:", "https:", "mailto:", "#")):
                continue
            target = unquote(target.split("#", 1)[0].strip("<>"))
            if not target:
                continue
            count += 1
            if not (path.parent / target).resolve().exists():
                problems.append(f"{path.relative_to(ROOT)} -> {target}")
    if problems:
        raise AssertionError("Broken course links:\n" + "\n".join(problems))
    print(f"Validated {count} local document/notebook links.")


if __name__ == "__main__":
    main()
