"""Section boundary and frozen-body regression checks."""
import unittest

from compare_chunk_context import annotate, contexts


class ContextTests(unittest.TestCase):
    def test_title_carries_to_next_chunk_without_changing_body(self):
        text = "Oil Filter\nRemove filter.\nTurn three quarters.\nFuel Filter\nOther step."
        chunks = [dict(source="manual", page=1, chunk_id="a", text="Oil Filter\nRemove filter."),
                  dict(source="manual", page=1, chunk_id="b", text="Turn three quarters."),
                  dict(source="manual", page=1, chunk_id="c", text="Fuel Filter\nOther step.")]
        docs, missing = annotate([dict(source="manual", page=1, text=text)], chunks,
            [dict(page=1, path=["Oil Filter"]), dict(page=1, path=["Fuel Filter"])])
        self.assertFalse(missing)
        self.assertEqual([d["text"] for d in docs], [d["text"] for d in chunks])
        self.assertEqual(docs[1]["sections"][0]["title_path"], ["Oil Filter"])
        self.assertIn("Oil Filter\n\nTurn three quarters.", docs[1]["embedding_text"])
        expanded = contexts([docs[1]], docs)
        self.assertIn("a", [c["chunk_id"] for c in expanded])
        self.assertNotIn("c", [c["chunk_id"] for c in expanded])

    def test_neighbor_is_clipped_at_new_section(self):
        seed = dict(source="m", page=1, chunk_id="a", text="first", sections=[dict(section_id="oil")])
        neighbor = dict(source="m", page=1, chunk_id="b", text="oil end FUEL SECRET", sections=[
            dict(section_id="oil", text="oil end"), dict(section_id="fuel", text="FUEL SECRET")])
        result = contexts([seed], [seed, neighbor])
        self.assertEqual(result[1]["text"], "oil end")
        self.assertNotIn("FUEL SECRET", str(result))

    def test_no_cross_page_or_transitive_expansion(self):
        docs = [dict(source="m", page=1, chunk_id=str(i), text=str(i), sections=[dict(section_id="s", text=str(i))]) for i in range(4)]
        self.assertEqual({c["chunk_id"] for c in contexts([docs[0]], docs)}, {"0", "1"})
        docs[1]["page"] = 2
        self.assertEqual(len(contexts([docs[0]], docs)), 1)

    def test_unmatched_heading_does_not_invent_a_title(self):
        docs, missing = annotate([dict(source="m", page=1, text="body")],
            [dict(source="m", page=1, chunk_id="a", text="body")], [dict(page=1, path=["Absent"])])
        self.assertEqual(len(missing), 1)
        self.assertEqual(docs[0]["sections"], [])
        self.assertEqual(docs[0]["embedding_text"], "body")


if __name__ == "__main__":
    unittest.main()
