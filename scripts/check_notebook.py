"""Execute every notebook code cell in offline mode and validate its assertions."""

import ast
import asyncio
from pathlib import Path

import nbformat

root = Path(__file__).resolve().parents[1]
notebook = nbformat.read(root / "notebooks" / "deep_agents.ipynb", as_version=4)
nbformat.validate(notebook)
namespace = {"__name__": "__main__"}
cells = [cell for cell in notebook.cells if cell.cell_type == "code"]


async def execute() -> None:
    for cell in cells:
        code = compile(
            cell.source,
            f"deep_agents.ipynb:{cell.id}",
            mode="exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        )
        result = eval(code, namespace)
        if result is not None:
            await result


asyncio.run(execute())
print(f"Executed {len(cells)} notebook cells in offline mode.")
