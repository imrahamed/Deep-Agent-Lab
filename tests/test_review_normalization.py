from deep_agent_lab.service import (
    AgentService,
    Decision,
    ReviewRequest,
    RunRequest,
    open_checkpointer,
)
from deep_agent_lab.settings import Settings
from tests.support import DemoModel


def test_review_hash_binds_the_validated_payload_that_the_tool_executes(tmp_path):
    class WhitespaceDemo(DemoModel):
        @staticmethod
        def respond(messages, names):
            response = DemoModel.respond(messages, names)
            for call in response.tool_calls:
                if call["name"] == "save_brief":
                    call["args"]["title"] = "  " + call["args"]["title"] + "  "
                    call["args"]["markdown"] = "\n" + call["args"]["markdown"] + "\n"
            return response

    settings = Settings(
        _env_file=None, deep_lab_mode="live", deep_lab_state_dir=tmp_path, langfuse_enabled=False
    )
    with open_checkpointer(settings) as saver:
        service = AgentService(settings, saver, model=WhitespaceDemo())
        try:
            pending = service.run(RunRequest(prompt="Draft and save a restore brief."))
            review = pending.reviews[0]
            payload = review.action_requests[0]["args"]
            assert payload["title"] == payload["title"].strip()
            assert payload["markdown"] == payload["markdown"].strip()
            result = service.resume(
                pending.thread_id,
                ReviewRequest(
                    interrupt_id=review.id,
                    decisions=[Decision(type="approve")],
                    payload_hashes=review.payload_hashes,
                    proposal_versions=review.proposal_versions,
                ),
            )
            assert len(result.saved_brief_ids) == 1
            saved = service.store.get(result.saved_brief_ids[0])
            assert saved.title == payload["title"] and saved.markdown == payload["markdown"]
        finally:
            service.close()
