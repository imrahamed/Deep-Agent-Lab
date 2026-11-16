from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def test_all_modules_have_substantive_standalone_notebooks():
    modules = sorted(
        path for path in (ROOT / "notebooks").iterdir() if path.is_dir() and path.name[:2].isdigit()
    )
    assert [path.name[:2] for path in modules] == [f"{n:02d}" for n in range(1, 14)]
    sections = [
        "Problem",
        "Learning objectives",
        "Concept explanation",
        "Mental model",
        "Implementation from scratch",
        "Framework implementation",
        "Code walkthrough",
        "Interactive experiments",
        "Failure experiment",
        "Verification",
        "Exercise",
        "Trade-offs",
    ]
    for module in modules:
        for path in module.glob("*.ipynb"):
            notebook = nbformat.read(path, as_version=4)
            nbformat.validate(notebook)
            prose = "\n".join(
                cell.source for cell in notebook.cells if cell.cell_type == "markdown"
            )
            assert len(prose.split()) > 500, path
            assert all(section in prose for section in sections), path
            code = [cell for cell in notebook.cells if cell.cell_type == "code"]
            assert len(code) >= 8 and all(cell.source.strip() for cell in code), path
            assert any("assert " in cell.source for cell in code)
            assert "```mermaid" not in prose  # Notebook diagrams must have a renderer.
            assert not any(
                output.output_type == "error" for cell in code for output in cell.get("outputs", [])
            ), path
