"""Testes dos consumers WebSocket do FlowForge."""

from flowforge.consumers import WorkflowRunConsumer


class TestWorkflowRunConsumer:
    def test_extract_token_from_subprotocol(self):
        consumer = WorkflowRunConsumer()
        consumer.scope = {"subprotocols": ["flowforge.jwt", "jwt.access-token"]}

        assert consumer._extract_token() == "access-token"

    def test_extract_token_ignores_query_string(self):
        consumer = WorkflowRunConsumer()
        consumer.scope = {
            "query_string": b"token=leaked-token",
            "subprotocols": ["flowforge.jwt"],
        }

        assert consumer._extract_token() == ""
