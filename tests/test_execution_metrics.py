from langchain.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from deep_agent_lab.instrumentation import ExecutionMetrics


def test_call_metrics_include_failures_and_keep_incomplete_usage_null():
    metrics = ExecutionMetrics()
    metrics.on_chat_model_start({}, [])
    metrics.on_llm_end(
        LLMResult(
            generations=[
                [
                    ChatGeneration(
                        message=AIMessage(
                            content="answer",
                            usage_metadata={
                                "input_tokens": 10,
                                "output_tokens": 2,
                                "total_tokens": 12,
                            },
                        )
                    )
                ]
            ]
        )
    )
    assert metrics.report()["input_tokens"] == 10
    metrics.on_chat_model_start({}, [])
    metrics.on_llm_error(TimeoutError())
    report = metrics.report()
    assert report["model_calls"] == 2 and report["failed_model_calls"] == 1
    assert report["input_tokens"] is None and not report["usage_complete"]


def test_duplicate_retrieval_records_its_normalization_basis():
    metrics = ExecutionMetrics()
    for query in ['{"query":" Production Restore "}', '{"query":"production restore"}']:
        metrics.on_tool_start({"name": "search_knowledge"}, query)
    assert metrics.report()["duplicated_retrieval"] == 1
    assert metrics.report()["duplicate_retrieval_basis"] == "normalized_query"
