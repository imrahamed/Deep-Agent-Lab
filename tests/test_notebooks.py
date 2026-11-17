import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

import nbformat

from deep_agent_lab.settings import Settings
from scripts.coverage_report import validate_reference

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "notebooks/deep_agents.ipynb"


def test_master_covers_all_modules_and_has_valid_executable_cells():
    paths = sorted(
        path
        for path in (ROOT / "notebooks").rglob("*.ipynb")
        if ".ipynb_checkpoints" not in path.parts
    )
    assert paths == [MASTER]
    notebook = nbformat.read(MASTER, as_version=4)
    nbformat.validate(notebook)
    ids = [cell.id for cell in notebook.cells]
    assert len(ids) == len(set(ids))
    assert all(f"{num:02d}-00" in ids for num in range(1, 14))
    assert ids.index("07-08") < ids.index("03-08") < ids.index("06-08")
    assert {"claims-13", "recovery-06", "runtime-examples", "context-history"} <= set(ids)
    assert ids[-1] == "master-cleanup"
    for cell in notebook.cells:
        assert cell.source.strip()
        if cell.cell_type == "code":
            compile(cell.source, f"{MASTER.name}#{cell.id}", "exec", ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            assert not any(output.output_type == "error" for output in cell.get("outputs", []))


def test_all_topic_exercises_resolve_in_the_master():
    lessons = json.loads((ROOT / "docs/course-manifest.json").read_text(encoding="utf-8"))
    for lesson in lessons:
        for topic in lesson["topic_records"]:
            if reference := topic.get("exercise_cell"):
                assert reference.startswith("notebooks/deep_agents.ipynb#")
                validate_reference(ROOT, reference)


def test_revisited_sections_get_independent_workspaces_and_settings():
    notebook = nbformat.read(MASTER, as_version=4)
    setup = next(cell.source for cell in notebook.cells if cell.id == "master-setup")
    function = next(
        node for node in ast.parse(setup).body
        if isinstance(node, ast.FunctionDef) and node.name == "start_section"
    )
    with TemporaryDirectory() as directory:
        namespace = {
            "Path": Path,
            "mkdtemp": mkdtemp,
            "Settings": Settings,
            "ROOT": Path(directory),
            "course_workspace": type("Workspace", (), {"name": directory})(),
            "_service_settings": None,
        }
        module = ast.Module(body=[function], type_ignores=[])
        exec(compile(module, "section-setup", "exec"), namespace)
        start = namespace["start_section"]
        foundation, no_settings = start("01", services=False)
        assert foundation.is_dir() and no_settings is None
        assert namespace["_service_settings"] is None
        first, config_a = start("10")
        second, config_b = start("10")
        assert first != second and first.is_dir() and second.is_dir()
        assert config_a.deep_lab_state_dir != config_b.deep_lab_state_dir
        config_a.deep_lab_state_dir = first / "changed"
        assert config_b.deep_lab_state_dir == second / "state"
        assert not config_b.langfuse_enabled and not config_b.langfuse_capture_content
