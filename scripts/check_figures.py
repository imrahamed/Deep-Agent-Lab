"""Check declared figure semantics and exported pixels, retaining human review status."""

import json
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
REVIEW_FIELDS = {"arrow_direction", "overlap", "text_legibility", "mechanism_communicated"}


def validate_declaration(declaration: dict) -> None:
    if not declaration.get("semantic_kind") or not declaration.get("expected_title"):
        raise ValueError("Figure kind and expected title must be declared")
    if not declaration.get("required_labels"):
        raise ValueError("Required figure labels must be declared")
    if declaration.get("plots_values") and declaration.get("measurement_kind") not in {
        "heuristic estimate",
        "fixture measurement",
        "live measurement",
        "illustrative",
    }:
        raise ValueError("Plotted values require a measurement kind")
    review = declaration.get("manual_readability_review", {})
    if not REVIEW_FIELDS <= review.keys():
        raise ValueError("Manual readability review fields required")


def main():
    notebooks = json.loads((ROOT / "docs/reports/notebooks.json").read_text(encoding="utf-8"))
    records = []
    for notebook in notebooks["results"]:
        path = Path(notebook["notebook"])
        declarations = notebook.get("figures", [])
        if len(declarations) != notebook["rendered_pngs"]:
            raise ValueError(f"Missing figure declarations for {path}")
        for index, declaration in enumerate(declarations):
            validate_declaration(declaration)
            figure = (
                ROOT / "docs/reports/figures" / path.parent.name / f"{path.stem}-{index:02d}.png"
            )
            if not figure.is_file():
                raise ValueError(f"Missing PNG: {figure}")
            with Image.open(figure) as original:
                image = original.convert("RGB")
                if image.width < 400 or image.height < 200:
                    raise ValueError(f"Figure too small: {figure}")
                if max(ImageStat.Stat(image).stddev) <= 5:
                    raise ValueError(f"Blank figure: {figure}")
                records.append(
                    {
                        "figure": figure.relative_to(ROOT).as_posix(),
                        "width": image.width,
                        "height": image.height,
                        "pixel_checks": "passed",
                        **declaration,
                    }
                )
    if not records:
        raise ValueError("No figures were exported")
    report = {"pixel_checks_prove_semantic_readability": False, "figures": records}
    (ROOT / "docs/reports/figures.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Checked {len(records)} declared figures. Human readability status is retained.")


if __name__ == "__main__":
    main()
