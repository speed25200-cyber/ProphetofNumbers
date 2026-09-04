import json
import tempfile
import unittest
from pathlib import Path

import capture_order


def state(draw_id=101, balls=None, scene="DrawScene"):
    return {
        "scene": scene,
        "duration": 110000,
        "startTime": 0,
        "endTime": 110000,
        "progress": 500,
        "meta": {
            "fr-ch": {
                "id": draw_id,
                "balls": balls or [20, 1, 80] + list(range(2, 19)),
                "boost": 2,
                "extra": 20,
            }
        },
    }


class CaptureOrderTests(unittest.TestCase):
    def test_signalr_frame_and_order_are_preserved(self):
        payload = state()
        frame = json.dumps({"type": 1, "target": "SendCurrentState", "arguments": [payload]}) + "\x1e"
        message = list(capture_order.signalr_messages(frame))[0]
        record = capture_order.extract_state(message["arguments"][0], received_at="2026-09-04T00:00:00Z")
        self.assertEqual(record["balls"], payload["meta"]["fr-ch"]["balls"])
        self.assertTrue(capture_order.valid_full_draw(record))
        self.assertEqual(len(record["raw_sha256"]), 64)

    def test_plain_night_state_is_not_a_draw(self):
        record = capture_order.extract_state({"scene": "NightModeScene", "meta": {"fr-ch": {}}})
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_analysis_detects_sorted_sequences_and_gaps(self):
        records = []
        for draw_id in (10, 12):
            records.append(capture_order.extract_state(
                state(draw_id, list(range(1, 21)), "ResultsScene"),
                received_at=f"2026-09-04T00:00:{draw_id:02d}Z",
            ))
        report = capture_order.analyze(records)
        self.assertEqual(report["ascending_sequences"], 2)
        self.assertEqual(report["id_gaps"], [[10, 12]])

    def test_export_refuses_false_contiguity(self):
        records = [
            capture_order.extract_state(state(10), received_at="a"),
            capture_order.extract_state(state(12), received_at="b"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "id gaps"):
                capture_order.export_order(records, Path(directory) / "ordered.txt", False)

    def test_conflicting_sequences_are_reported(self):
        one = capture_order.extract_state(state(10, list(range(1, 21))), received_at="a")
        two = capture_order.extract_state(state(10, list(range(20, 0, -1))), received_at="b")
        _, conflicts = capture_order.select_draws([one, two])
        self.assertEqual(conflicts, [10])


if __name__ == "__main__":
    unittest.main()
