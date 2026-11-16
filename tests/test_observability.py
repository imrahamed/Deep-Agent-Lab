from unittest.mock import Mock

import pytest

from deep_agent_lab.tracing import Observation, Tracing


def test_telemetry_failure_does_not_change_application_result():
    tracing = Tracing()
    tracing.client = Mock()
    tracing.client.start_as_current_observation.side_effect = RuntimeError("secret URL")
    with tracing.span("read", input="private"):
        value = 42
    assert value == 42


def test_exception_trace_uses_type_not_secret_message():
    span = Mock()
    tracing = Tracing()
    manager = Mock()
    manager.__enter__ = Mock(return_value=span)
    manager.__exit__ = Mock(return_value=False)
    tracing.client = Mock()
    tracing.client.start_as_current_observation.return_value = manager
    with pytest.raises(ValueError):
        with tracing.span("failure", input="private"):
            raise ValueError("postgresql://private:credential@example")
    assert span.update.call_args.kwargs["status_message"] == "ValueError"
    assert "credential" not in str(span.update.call_args)
    manager.__exit__.assert_called_once_with(None, None, None)
    output = Mock()
    Observation(output).update(input="secret", output="secret", metadata={"count": 1})
    assert output.update.call_args.kwargs == {"metadata": {"count": 1}}
