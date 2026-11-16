import re
from pathlib import Path

import pytest

from deep_agent_lab.context import WorkingState, approximate_tokens, context_payload
from deep_agent_lab.courseware import bars

ROOT = Path(__file__).resolve().parents[1]


def test_module_two_has_executable_tool_contract():
    text = (ROOT / "docs/modules/02-tools-and-mcp.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    example = next(block for block in blocks if "SearchArgs.model_json_schema()" in block)
    namespace = {}
    exec(compile(example, "module-02-contract", "exec"), namespace)
    assert {row["status"] for row in namespace["asyncio"].run(namespace["examples"]())} == {
        "success",
        "invalid_request",
        "transient_error",
    }
    assert "def do_it(x)" in text


def test_context_estimate_includes_state_and_is_deterministic():
    state = WorkingState(objective="preserve", summary="history " * 100)
    compacted = state.model_copy(update={"summary": "history"})
    rows = [{"id": "a", "excerpt": "required"}]
    assert context_payload(rows, state) == context_payload(rows, state)
    assert approximate_tokens(context_payload(rows, state)) > approximate_tokens(
        context_payload(rows, compacted)
    )


def test_chart_measurement_labels():
    import matplotlib.pyplot as plt

    figure = bars("Context", {"full": 100}, ylabel="Tokens", measurement_kind="heuristic estimate")
    assert "heuristic estimate" in figure.axes[0].get_title(loc="left")
    assert "measured in this run" not in figure.axes[0].get_title(loc="left")
    plt.close(figure)
    with pytest.raises(ValueError):
        bars("Invalid", {}, ylabel="Tokens", measurement_kind="measured")
