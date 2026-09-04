import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import prospective_commit


class ProspectiveCommitTests(unittest.TestCase):
    def setUp(self):
        self.bundle_result = {
            "bundle_sha256": None,
            "next_draw_id": 102,
            "order_scope": "ANIMATION_SEQUENCE_ONLY",
        }

    def prepare(self, directory, **changes):
        root = Path(directory)
        bundle = root / "evidence.json"
        bundle.write_bytes(b"verified evidence\n")
        self.bundle_result["bundle_sha256"] = prospective_commit.file_sha256(bundle)
        options = {
            "public_path": root / "prediction.commit.json",
            "reveal_path": root / "prediction.reveal.json",
            "draw_id": 102,
            "wager_end_date": "2030-01-02T03:04:05Z",
            "prediction": list(range(1, 21)),
            "evidence_bundle": bundle,
            "now_ns": 1_700_000_000_000_000_000,
            "salt_hex": "ab" * 32,
        }
        options.update(changes)
        with mock.patch.object(
            prospective_commit.proof_bundle,
            "verify_bundle",
            return_value=dict(self.bundle_result),
        ):
            result = prospective_commit.prepare_commitment(**options)
        return result, options

    def test_prepare_and_verify_exact_prediction(self):
        with tempfile.TemporaryDirectory() as directory:
            result, options = self.prepare(directory)
            verified = prospective_commit.verify_commitment(
                options["public_path"], options["reveal_path"]
            )
            reveal_mode = stat.S_IMODE(options["reveal_path"].stat().st_mode)
            public = json.loads(options["public_path"].read_text())
        self.assertEqual(result["verdict"], "COMMITMENT_PREPARED")
        self.assertEqual(verified["verdict"], "REVEAL_MATCHES_COMMITMENT")
        self.assertEqual(verified["prediction_order"], list(range(1, 21)))
        self.assertEqual(public["commitment_sha256"], result["commitment_sha256"])
        self.assertEqual(reveal_mode, 0o600)

    def test_changed_prediction_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            _, options = self.prepare(directory)
            reveal = json.loads(options["reveal_path"].read_text())
            reveal["prediction_order"][0] = 80
            options["reveal_path"].write_bytes(
                prospective_commit.canonical_bytes(reveal) + b"\n"
            )
            with self.assertRaisesRegex(
                prospective_commit.CommitmentError, "differs|does not match"
            ):
                prospective_commit.verify_commitment(
                    options["public_path"], options["reveal_path"]
                )

    def test_duplicate_or_out_of_range_numbers_are_rejected(self):
        bad_values = [list(range(1, 20)) + [19], list(range(1, 20)) + [81]]
        for values in bad_values:
            with self.subTest(last=values[-1]), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(
                    prospective_commit.CommitmentError, "20 unique"
                ):
                    self.prepare(directory, prediction=values)

    def test_past_or_naive_cutoff_is_rejected(self):
        for cutoff in ("2020-01-01T00:00:00Z", "2030-01-01T00:00:00"):
            with self.subTest(cutoff=cutoff), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(
                    prospective_commit.CommitmentError, "future|timezone"
                ):
                    self.prepare(directory, wager_end_date=cutoff)

    def test_target_must_be_bundle_next_draw(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                prospective_commit.CommitmentError, "next draw"
            ):
                self.prepare(directory, draw_id=103)

    def test_files_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            _, options = self.prepare(directory)
            before = options["public_path"].read_bytes()
            with self.assertRaisesRegex(
                prospective_commit.CommitmentError, "overwrite"
            ):
                self.prepare(directory)
            self.assertEqual(options["public_path"].read_bytes(), before)

    def test_bundle_mutation_between_verify_and_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "evidence.json"
            bundle.write_bytes(b"one")
            expected = prospective_commit.file_sha256(bundle)

            def mutate(_path):
                bundle.write_bytes(b"two")
                return {
                    "bundle_sha256": expected,
                    "next_draw_id": 102,
                    "order_scope": "ANIMATION_SEQUENCE_ONLY",
                }

            with mock.patch.object(
                prospective_commit.proof_bundle, "verify_bundle", side_effect=mutate
            ), self.assertRaisesRegex(
                prospective_commit.CommitmentError, "changed"
            ):
                prospective_commit.prepare_commitment(
                    root / "public.json",
                    root / "reveal.json",
                    draw_id=102,
                    wager_end_date="2030-01-02T03:04:05Z",
                    prediction=list(range(1, 21)),
                    evidence_bundle=bundle,
                    now_ns=1_700_000_000_000_000_000,
                    salt_hex="ab" * 32,
                )


if __name__ == "__main__":
    unittest.main()
