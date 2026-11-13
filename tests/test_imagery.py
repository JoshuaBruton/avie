import json
import tempfile
import unittest
from pathlib import Path
from brutils.imagery import assess_imagery, capture_label
from scripts.flag_anomalies import log_detections


def verified(**overrides):
    return dict(source="Licensed survey", source_type="aerial", native_gsd_cm=3,
                license_reference="Contract ABC", analysis_permitted=True,
                display_permitted=True, **overrides)


class ImageryTests(unittest.TestCase):
    def test_resolution_boundaries_and_unknowns(self):
        for gsd in [None, 0, -1, 5.1, 12.5, True, "3", float("nan"), float("inf")]:
            metadata = verified()
            metadata["native_gsd_cm"] = gsd
            self.assertFalse(assess_imagery(metadata)["eligible"], gsd)
        for gsd in [2, 3, 5]:
            metadata = verified()
            metadata["native_gsd_cm"] = gsd
            self.assertTrue(assess_imagery(metadata)["eligible"])

    def test_age_is_not_a_filter_but_licensing_is(self):
        self.assertTrue(assess_imagery(verified(capture_date="2000-01-01"))["eligible"])
        metadata = verified()
        metadata["analysis_permitted"] = False
        self.assertFalse(assess_imagery(metadata)["eligible"])
        self.assertFalse(assess_imagery({})["eligible"])

    def test_capture_precision(self):
        self.assertEqual(capture_label({}), "Capture date/time unavailable")
        self.assertEqual(capture_label({"capture_date": "2020-01-02"}),
                         "2020-01-02 (capture time unavailable)")
        self.assertEqual(capture_label({"captured_at": "2020-01-02T12:30:00Z"}),
                         "2020-01-02T12:30:00Z")
        self.assertEqual(capture_label({"captured_at": "2020-01-02T12:30:00"}),
                         "Capture date/time unavailable")
        self.assertIn("exact capture date/time unavailable", capture_label({
            "capture_date_range": {"start": "2020-01-01", "end": "2020-12-31"}}))

    def test_blocked_scan_is_not_an_empty_success(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "report.jsonl")
            entry = log_detections([object()], 51.1789, -1.8262, "image.jpg", output_path=path)
            saved = json.loads(Path(path).read_text())
            self.assertEqual(saved["detection_status"], "not_run_insufficient_imagery")
            self.assertEqual(saved["detections"], [])
            self.assertEqual(entry["capture_label"], "Capture date/time unavailable")
            self.assertTrue(entry["analysis_at"].endswith("+00:00"))

    def test_historical_capture_is_preserved_in_report(self):
        with tempfile.TemporaryDirectory() as folder:
            entry = log_detections([], 51.1789, -1.8262, "image.jpg",
                output_path=str(Path(folder) / "report.jsonl"),
                imagery_metadata=verified(capture_date="2000-01-01"))
            self.assertEqual(entry["detection_status"], "completed")
            self.assertIn("2000-01-01", entry["capture_label"])
            self.assertNotEqual(entry["analysis_at"][:10], "2000-01-01")


if __name__ == "__main__":
    unittest.main()
