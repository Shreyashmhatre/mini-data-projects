import csv
import tempfile
import unittest
from pathlib import Path

from api_log_explorer.analyze import (
    FIELDS,
    markdown_report,
    percentile,
    read_requests,
    summarize,
)

ROOT = Path(__file__).resolve().parent.parent


class AnalysisTests(unittest.TestCase):
    def test_sample_results(self):
        result = summarize(read_requests(ROOT / "data/sample_requests.csv"))
        self.assertEqual(result["requests"], 10)
        self.assertEqual(result["successes"], 6)
        self.assertEqual(result["client_errors"], 3)
        self.assertEqual(result["server_errors"], 1)
        self.assertEqual(result["error_rate"], 0.4)
        self.assertEqual(result["mean_latency_ms"], 19.9)
        self.assertEqual(result["p50_ms"], 10)
        self.assertEqual(result["p95_ms"], 100)
        products = next(r for r in result["routes"] if r["route"] == "/products")
        self.assertEqual(products["requests"], 5)
        self.assertEqual(result["requests_per_utc_minute"]["2026-01-01T10:01:00Z"], 3)
        self.assertIn("40.0%", markdown_report(result))

    def test_empty_input_and_percentile(self):
        result = summarize([])
        self.assertEqual(result["error_rate"], 0)
        self.assertIsNone(result["p95_ms"])
        self.assertIsNone(result["mean_latency_ms"])
        self.assertEqual(percentile([3, 1, 2, 4], 0.5), 2)
        with self.assertRaises(ValueError):
            percentile([1], 0)

    def make_source(self, row):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "requests.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            writer.writerow(row)
        return path

    def test_timezone_normalization(self):
        path = self.make_source(
            ["2026-01-01T15:30:00+05:30", "GET", "/products", "200", "1"]
        )
        result = summarize(read_requests(path))
        self.assertEqual(result["requests_per_utc_minute"], {"2026-01-01T10:00:00Z": 1})

    def test_malformed_values_fail_with_row_number(self):
        row = ["2026-01-01T10:00:00Z", "GET", "/products", "200", "1"]
        for index, value in [
            (0, "2026-01-01T10:00:00"),
            (1, "NOTHTTP"),
            (2, "/products?token=secret"),
            (3, "999"),
            (4, "NaN"),
            (4, "-1"),
        ]:
            changed = row.copy()
            changed[index] = value
            with (
                self.subTest(index=index, value=value),
                self.assertRaisesRegex(ValueError, "Row 2"),
            ):
                read_requests(self.make_source(changed))

    def test_redirect_is_not_an_error_or_success(self):
        path = self.make_source(["2026-01-01T10:00:00Z", "GET", "/old", "302", "1"])
        result = summarize(read_requests(path))
        self.assertEqual(result["error_rate"], 0)
        self.assertEqual(result["successes"], 0)


if __name__ == "__main__":
    unittest.main()
