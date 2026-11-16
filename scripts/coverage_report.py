"""Validate topic-specific evidence and generate the curriculum coverage matrix."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVELS = {
    "explained",
    "demonstrated",
    "implemented",
    "exercised",
    "deterministically_tested",
    "live_measured",
}


def validate_reference(root: Path, reference: str) -> None:
    path_text, _, cell_id = reference.partition("#")
    if "::" in path_text:
        path_text, symbol = path_text.split("::", 1)
    elif ".py:" in path_text:
        path_text, symbol = path_text.split(":", 1)
    else:
        symbol = None
    path = root / path_text
    if not path.is_file():
        raise ValueError(f"Missing reference file: {reference}")
    if symbol:
        nodes = ast.parse(path.read_text(encoding="utf-8")).body
        for part in symbol.split("."):
            found = next((node for node in nodes if getattr(node, "name", None) == part), None)
            if found is None:
                raise ValueError(f"Missing symbol: {reference}")
            nodes = getattr(found, "body", [])
    if cell_id and path.suffix == ".ipynb":
        notebook = json.loads(path.read_text(encoding="utf-8"))
        if cell_id not in {cell["id"] for cell in notebook["cells"]}:
            raise ValueError(f"Missing exercise cell: {reference}")


def validate_topic(topic: dict, root: Path = ROOT) -> None:
    level = topic["verification_level"]
    if level not in LEVELS:
        raise ValueError(f"Invalid verification level: {level}")
    validate_reference(root, topic["explained_in"])
    implementations = topic.get("implemented_by", [])
    tests = topic.get("assertion_or_test", [])
    for reference in implementations + tests:
        validate_reference(root, reference)
    exercise = topic.get("exercise_cell")
    if exercise:
        validate_reference(root, exercise)
    if level in {"implemented", "exercised", "deterministically_tested", "live_measured"}:
        if not implementations:
            raise ValueError("Implementation evidence required")
    if level in {"exercised", "deterministically_tested", "live_measured"} and not exercise:
        raise ValueError("Exercise cell required")
    if level == "deterministically_tested" and not tests:
        raise ValueError("Topic-specific test evidence required")
    live = topic.get("live_experiment")
    if live:
        validate_reference(root, live)
    if level == "live_measured":
        if not live:
            raise ValueError("Live measurement requires a concrete live record")
        report = json.loads((root / live).read_text(encoding="utf-8"))
        if report.get("measurement_kind") != "live measurement":
            raise ValueError("Live report must declare its measurement kind")
        records = report.get("records", report.get("trials", []))
        if not any(record.get("status") != "skipped" for record in records):
            raise ValueError("Live report has no executed records")


def main():
    lessons = json.loads((ROOT / "docs/course-manifest.json").read_text(encoding="utf-8"))
    rows = []
    text = """# Course coverage and verification scope

Each topic declares its own explanation, implementation, exercise and test evidence.
Levels describe the linked contract. A successful notebook does not promote every topic.
Live measurement requires a concrete executed report. Unit tests may isolate services.
The `topics` string list is retained temporarily for readers of the old manifest format;
`topic_records` is authoritative for this report.

| Module / topic | Level | Explanation | Implementation | Exercise | Tests | Live record |
| --- | --- | --- | --- | --- | --- | --- |
"""
    for lesson in lessons:
        for topic in lesson["topic_records"]:
            validate_topic(topic)
            row = {"module": lesson["slug"], **topic}
            rows.append(row)

            def links(references):
                rendered = []
                for reference in references:
                    target = reference.split("::", 1)[0]
                    if ".py:" in target:
                        target = target.split(".py:", 1)[0] + ".py"
                    rendered.append(f"[{reference}](../{target})")
                return "<br>".join(rendered)

            exercise = topic.get("exercise_cell")
            live = topic.get("live_experiment")
            text += (
                f"| {lesson['slug'][:2]} · {topic['topic']} | {topic['verification_level']} | "
                f"[Chapter](../{topic['explained_in']}) | {links(topic['implemented_by'])} | "
                f"{links([exercise]) if exercise else ''} | {links(topic['assertion_or_test'])} | "
                f"{links([live]) if live else ''} |\n"
            )
    (ROOT / "docs/coverage.md").write_text(text, encoding="utf-8")
    (ROOT / "docs/reports/coverage.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Validated evidence references for {len(rows)} topics.")


if __name__ == "__main__":
    main()
