import json
import unittest
from unittest.mock import Mock, patch

from software.ai.local_model import LlamaCpp, ask_grounded


def note(number):
    return {
        "note_id": number,
        "title": f"Note {number}",
        "text": f"Stored excerpt {number}.",
        "citation": {"label": f"Source {number}", "url": f"https://example.org/{number}"},
    }


class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.store = Mock()
        self.complete = Mock()
        self.evidence = [note(3), note(4)]
        self.store.ask.return_value = {"status": "supported", "evidence": self.evidence}

    def test_model_selection_renders_only_stored_evidence_and_citations(self):
        self.complete.return_value = '{"sources": [2, 1]}'
        result = ask_grounded(self.store, "What explains orbital motion?", self.complete)
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["evidence"], self.evidence[::-1])
        self.assertEqual(
            result["answer"],
            "**Note 4** Stored excerpt 4. [Source 4](https://example.org/4)\n\n"
            "**Note 3** Stored excerpt 3. [Source 3](https://example.org/3)",
        )
        self.assertIn("Stored excerpt 3.", str(self.complete.call_args))
        self.assertNotIn("https://example.org", str(self.complete.call_args))

    def test_invalid_model_output_is_rejected(self):
        for output in (
            '{"sources": [3]}', '{"sources": [true]}', '{"sources": [1, 1]}',
            '{"sources": []}', '{"sources": [1], "citation": "made up"}',
            'malformed', '[]',
        ):
            with self.subTest(output=output):
                self.complete.return_value = output
                result = ask_grounded(self.store, "What explains orbital motion?", self.complete)
                self.assertEqual(result["status"], "invalid_model_output")
                self.assertEqual(result["evidence"], [])
                self.assertNotIn("made up", result["answer"])

    def test_insufficient_evidence_skips_model(self):
        self.store.ask.return_value = {"status": "insufficient_evidence", "evidence": []}
        self.assertEqual(
            ask_grounded(self.store, "Unrelated question", self.complete),
            self.store.ask.return_value,
        )
        self.complete.assert_not_called()

    @patch("software.ai.local_model.HTTPConnection")
    def test_llama_cpp_uses_loopback_and_disables_thinking(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"choices":[{"message":{"content":"answer"}}]}'
        self.assertEqual(LlamaCpp(port=8081).complete("system", "question"), "answer")
        connection.assert_called_once_with("127.0.0.1", 8081, timeout=120)
        request = connection.return_value.request.call_args
        self.assertEqual(request.args[:2], ("POST", "/v1/chat/completions"))
        self.assertEqual(json.loads(request.kwargs["body"])["chat_template_kwargs"],
                         {"enable_thinking": False})
        connection.return_value.close.assert_called_once()
