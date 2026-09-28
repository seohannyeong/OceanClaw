#!/usr/bin/env python3
"""Unit tests for AIS natural-language filter parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw.ais_search import parse_ais_query


class AISQueryParserTests(unittest.TestCase):
    def test_anchoring_has_priority_over_generic_voyage_word(self):
        filters, expanded = parse_ais_query("괌에서 정박한 선박의 운항 기록을 알려줘")
        self.assertEqual(filters.event_types, ("anchored", "moored"))
        self.assertIn("anchored", expanded)

    def test_minimum_hours(self):
        filters, _ = parse_ais_query("10시간 이상 정박한 선박")
        self.assertEqual(filters.min_duration_minutes, 600)
        self.assertEqual(filters.event_types, ("anchored", "moored"))

    def test_low_speed(self):
        filters, _ = parse_ais_query("저속으로 이동한 선박")
        self.assertEqual(filters.event_types, ("low-speed movement",))

    def test_mmsi_and_month(self):
        filters, _ = parse_ais_query("MMSI 431341000의 2025년 8월 운항 기록")
        self.assertEqual(filters.mmsi, "431341000")
        self.assertEqual(filters.date_prefix, "2025-08")

    def test_long_duration_sort(self):
        filters, _ = parse_ais_query("장시간 계류한 선박")
        self.assertTrue(filters.sort_by_duration)
        self.assertEqual(filters.event_types, ("anchored", "moored"))


if __name__ == "__main__":
    unittest.main()
