"""Execute notebooks in fresh project-Python kernels and persist verified outputs."""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def execute(path: Path, *, write=True):
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    if "northstar" in notebook.metadata:
        notebook.metadata["northstar"]["mode"] = "live"
    client = NotebookClient(
        notebook, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}
    )
    client.km = client.create_kernel_manager()
    # Use the exact locked interpreter rather than a machine's global Jupyter kernel.
    client.km.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    started = time.perf_counter()
    with TemporaryDirectory(prefix="northstar-kernel-") as directory:
        runtime = Path(directory)
        client.execute(
            cleanup_kc=True,
            env={
                **os.environ,
                "DEEP_LAB_MODE": "live",
                "LANGFUSE_ENABLED": "false",
                "RUN_LANGFUSE_EXPORT": "0",
                "IPYTHONDIR": str(runtime / "ipython"),
                "JUPYTER_RUNTIME_DIR": str(runtime),
            },
        )
    images = []
    figure_records = []
    for cell in notebook.cells:
        if cell.cell_type == "code":
            image_index = 0
            assert cell.execution_count is not None
            for output in cell.get("outputs", []):
                if output.output_type == "error":
                    raise AssertionError(f"Unexpected notebook error: {path}")
                if "image/png" in output.get("data", {}):
                    images.append(base64.b64decode(output.data["image/png"]))
                    declarations = cell.metadata.get("northstar_figures", [])
                    if image_index >= len(declarations):
                        raise AssertionError(f"Undeclared figure in {path.name}#{cell.id}")
                    figure_records.append({"cell_id": cell.id, **declarations[image_index]})
                    image_index += 1
    if path.name != "deep_agents.ipynb" and not images:
        raise AssertionError(f"Notebook did not render a diagram: {path}")
    relative = path.relative_to(ROOT).as_posix()
    code_cells = sum(c.cell_type == "code" for c in notebook.cells)
    notebook.metadata["northstar_verification"] = {
        "mode": "live",
        "fresh_kernel": True,
        "code_cells": code_cells,
        "rendered_pngs": len(images),
    }
    if write:
        nbformat.write(notebook, path)
        image_dir = ROOT / "docs/reports/figures" / path.parent.name
        image_dir.mkdir(parents=True, exist_ok=True)
        for index, data in enumerate(images):
            (image_dir / f"{path.stem}-{index:02d}.png").write_bytes(data)
        for old in image_dir.glob(f"{path.stem}-[0-9][0-9].png"):
            if int(old.stem.rsplit("-", 1)[1]) >= len(images):
                old.unlink()
    return {
        "notebook": relative,
        "status": "passed",
        "code_cells": code_cells,
        "rendered_pngs": len(images),
        "figures": figure_records,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or sorted((ROOT / "notebooks").rglob("*.ipynb"))
    results, failures = [], []
    for path in paths:
        path = path.resolve()
        print(f"Executing {path.relative_to(ROOT)}", flush=True)
        try:
            result = execute(path)
            results.append(result)
            print(
                f"  Passed: {result['code_cells']} cells, {result['rendered_pngs']} PNGs",
                flush=True,
            )
        except Exception as error:
            failures.append(
                {
                    "notebook": path.relative_to(ROOT).as_posix(),
                    "status": "failed",
                    "error": str(error),
                }
            )
            print(str(error), flush=True)
    report_path = ROOT / "docs/reports/notebooks.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"mode": "live", "results": results, "failures": failures}, indent=2),
        encoding="utf-8",
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
