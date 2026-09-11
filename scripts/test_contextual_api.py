"""Offline regression checks for opt-in manual context retrieval."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from oceanclaw.api import AskRequest, ask
from oceanclaw.answer import answer_question, format_context, search_manual
from oceanclaw.contextual_manual import extend_context


def doc(i, page=1, section="a", text="body"):
    return {"chunk_id": str(i), "source": "manual.pdf", "page": page, "text": text,
            "sections": [{"section_id": section, "text": text, "title_path": ["Title"]}]}


class ContextTests(unittest.TestCase):
    @patch("oceanclaw.contextual_manual.search_contextual_manual", return_value=[])
    def test_manual_default_uses_titles_without_neighbors(self, search):
        search_manual("original question")
        search.assert_called_once_with("original question", 3, False, 0.0, 5000)

    @patch("oceanclaw.answer.route_by_score")
    @patch("oceanclaw.answer.search_sensor", return_value=[])
    @patch("oceanclaw.answer.search_wiki", return_value=[])
    @patch("oceanclaw.contextual_manual.search_contextual_manual", return_value=[])
    def test_default_routes_use_titles_without_cross_model_score_routing(self, manual, wiki, sensor, router):
        for route in (None, "manual", "both", "all"):
            result = answer_question("question", route_override=route)
            self.assertEqual(result["manual_profile"], "titles")
        self.assertEqual(manual.call_count, 4)
        router.assert_not_called()

    def test_neighbors_stay_on_page_and_section(self):
        docs = [doc(0, page=2), doc(1), doc(2, section="b")]
        self.assertEqual(len(extend_context([docs[1]], docs)), 1)

    def test_budget_and_nonrecursive_neighbors(self):
        docs = [doc(i) for i in range(5)]
        self.assertEqual([p["document"]["chunk_id"] for p in extend_context([docs[2]], docs)], ["2", "1", "3"])
        self.assertEqual(len(extend_context([docs[2]], docs, 4)), 1)
        self.assertEqual(extend_context([docs[2]], docs, 3), [])

    def test_section_clipping(self):
        docs = [doc(0, text="same OTHER SECTION"), doc(1)]
        docs[0]["sections"][0]["text"] = "same"
        self.assertEqual(extend_context([docs[1]], docs)[1]["text"], "same")

    @patch("oceanclaw.api.answer_question", return_value={})
    def test_api_allows_titles_for_all_routes(self, mocked):
        for route in (None, "manual", "all", "both", "sensor", "wiki"):
            ask(AskRequest(question="test", route=route))
            self.assertEqual(mocked.call_args.kwargs["manual_profile"], "titles")

    @patch("oceanclaw.api.answer_question", return_value={"ok": True})
    def test_api_passes_options_and_defaults(self, mocked):
        ask(AskRequest(question="test"))
        self.assertEqual(mocked.call_args.kwargs["manual_profile"], "titles")
        ask(AskRequest(question="test", route="manual", manual_profile="titles_neighbors"))
        self.assertEqual(mocked.call_args.kwargs["manual_profile"], "titles_neighbors")

    @patch("oceanclaw.contextual_manual.search_contextual_manual", return_value=[])
    @patch("oceanclaw.answer.chat")
    def test_empty_context_does_not_generate(self, chat, search):
        result = answer_question("test", route_override="manual", manual_profile="titles")
        chat.assert_not_called()
        self.assertEqual(result["manual_profile"], "titles")
        self.assertEqual(result["timing"]["generation_seconds"], 0)

    def test_headings_reach_prompt(self):
        result = {**doc(1), "kind": "manual", "title_paths": [["Engine oil"]]}
        self.assertIn("Engine oil", format_context([result]))


if __name__ == "__main__":
    unittest.main()
