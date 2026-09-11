"""Offline checks for benchmark labels and failure-aware aggregation."""
import unittest

from compare_retrieval import load_benchmark, summarize, summarize_memory, validate_multilingual_metadata
from oceanclaw.query_expansion import expand_query


class BenchmarkTests(unittest.TestCase):
    def test_missing_memory_is_not_reported_as_zero(self):
        result = summarize_memory([{"memory_after_search": {"models": [{"name": "bge", "size": 100}]}}])
        self.assertEqual(result["models"][0]["max_observed_loaded_bytes"], 100)
        self.assertIsNone(result["models"][0]["max_observed_vram_bytes"])
        self.assertEqual(summarize_memory([{"memory_after_search": {"error": "offline"}}])["sampling_errors"], 1)

    def test_multilingual_index_must_preserve_documents(self):
        original = {"model": "nomic", "documents": [{"text": "original"}]}
        with self.assertRaises(ValueError):
            validate_multilingual_metadata(original, {"model": "bge", "documents": [{"text": "changed"}]})
        with self.assertRaises(ValueError):
            validate_multilingual_metadata(original, original)
        validate_multilingual_metadata(original, {"model": "bge", "documents": original["documents"]})

    def test_all_evidence_is_in_index_and_groups_are_balanced(self):
        _, _, _, questions = load_benchmark()
        for group in ("covered", "paraphrase", "uncovered"):
            self.assertEqual(sum(q["group"] == group for q in questions), 10)
        for q in questions:
            self.assertTrue(q["relevant_chunk_ids"])
            if q["group"] == "uncovered":
                self.assertEqual(expand_query(q["question"]), q["question"])

    def test_errors_are_not_removed_from_metric_denominator(self):
        rows = [
            dict(mode="original", group="covered", status="ok", hit_at_3=1, reciprocal_rank=0.5, total_seconds=2),
            dict(mode="original", group="covered", status="error", hit_at_3=0, reciprocal_rank=0, total_seconds=90),
        ]
        overall = summarize(rows)[0]
        self.assertEqual(overall["hit_at_3"], 0.5)
        self.assertEqual(overall["mrr_at_3"], 0.25)
        self.assertEqual(overall["errors"], 1)
        self.assertEqual(overall["mean_total_seconds_successful"], 2)

    def test_all_failures_have_no_successful_latency(self):
        rows = [dict(mode="translated", group="covered", status="error", hit_at_3=0, reciprocal_rank=0, total_seconds=90)]
        self.assertIsNone(summarize(rows)[0]["mean_total_seconds_successful"])


if __name__ == "__main__":
    unittest.main()
