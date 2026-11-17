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
        ROOT / "notebooks/deep_agents.ipynb",
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
            if target.startswith(("http:", "https:", "mailto:")):
                continue
            target, _, fragment = unquote(target.strip("<>")).partition("#")
            destination = (path.parent / target).resolve() if target else path
            count += 1
            if not destination.exists():
                problems.append(f"{path.relative_to(ROOT)} -> {target}")
            elif fragment and destination.suffix == ".ipynb":
                notebook = json.loads(destination.read_text(encoding="utf-8"))
                anchors = {cell["id"] for cell in notebook["cells"]}
                for cell in notebook["cells"]:
                    if cell["cell_type"] == "markdown":
                        anchors.update(re.findall(r'<a id="([^"]+)"', "".join(cell["source"])))
                if fragment not in anchors:
                    problems.append(f"{path.relative_to(ROOT)} -> {target}#{fragment}")
    if problems:
        raise AssertionError("Broken course links:\n" + "\n".join(problems))
    print(f"Validated {count} local document/notebook links.")


if __name__ == "__main__":
    main()
