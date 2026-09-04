import base64
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import capture_order
import proof_bundle
from test_capture_order import captured, rest, rest_evidence


HERE = Path(__file__).resolve().parent
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


def fnv_byte(value, byte):
    return ((value ^ byte) * FNV_PRIME) & MASK64


def fnv_integer(value, integer, byte_count):
    for shift in range(0, byte_count * 8, 8):
        value = fnv_byte(value, (integer >> shift) & 0xFF)
    return value


def input_fnv(draws):
    value = fnv_integer(FNV_OFFSET, len(draws), 4)
    for draw in draws:
        for ball in draw:
            value = fnv_integer(value, ball, 4)
    return value


def checkpoint_checksum(fields, words):
    value = FNV_OFFSET
    for byte in b"KENO_BREAK_MT19937":
        value = fnv_byte(value, byte)
    for integer in (
        1,
        fields["sampler"],
        fields["mapping"],
        fields["stride"],
        fields["draws_consumed"],
        fields["holdout"],
    ):
        value = fnv_integer(value, integer, 4)
    value = fnv_integer(value, fields["input_fnv1a64"], 8)
    value = fnv_integer(value, fields["mti"], 4)
    for word in words:
        value = fnv_integer(value, word, 4)
    return value


def write_checkpoint(path, draws, *, wrong_input=False, mti=40):
    fields = {
        "sampler": 0,
        "mapping": 0,
        "stride": 20,
        "draws_consumed": len(draws),
        "holdout": 1,
        "input_fnv1a64": input_fnv(draws) ^ int(wrong_input),
        "mti": mti,
    }
    words = [((index + 1) * 0x6C078965) & 0xFFFFFFFF for index in range(624)]
    lines = [
        "KENO_BREAK_MT19937 1",
        f"sampler {fields['sampler']}",
        f"mapping {fields['mapping']}",
        f"stride {fields['stride']}",
        f"draws_consumed {fields['draws_consumed']}",
        f"holdout {fields['holdout']}",
        f"input_fnv1a64 {fields['input_fnv1a64']:016x}",
        f"mti {fields['mti']}",
        "words 624",
    ]
    lines.extend(
        " ".join(f"{word:08x}" for word in words[index : index + 8])
        for index in range(0, 624, 8)
    )
    lines.extend(
        [
            f"checksum_fnv1a64 {checkpoint_checksum(fields, words):016x}",
            "end",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


class ProofBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.capture = self.directory / "capture.jsonl"
        self.validation = self.directory / "capture.validation.json"
        self.ordered = self.directory / "ordered.txt"
        self.export_manifest = self.directory / "ordered.txt.manifest.jsonl"
        self.checkpoint = self.directory / "recovered-state.txt"
        self.bundle = self.directory / "prospective-proof.json"

        first = captured(101, tick=1)
        second_balls = [80, 2, 79] + list(range(3, 19)) + [20]
        second = captured(102, second_balls, tick=2)
        self.records = [first, second]
        results = []
        payloads = {}
        for record in self.records:
            draw_id = record["draw_id"]
            payload = rest(draw_id, sorted(record["balls"]), bonus=str(record["extra"]))
            body, evidence = rest_evidence(draw_id, payload)
            results.append(
                capture_order.verify_record(
                    record,
                    capture_order.parse_rest_draw(payload),
                    evidence,
                    draw_id,
                    record,
                )
            )
            payloads[str(draw_id)] = {
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
                "encoding": "base64",
                "body_base64": base64.b64encode(body).decode("ascii"),
            }
        self.validation_value = {
            "schema": 2,
            "validated_at": "2026-09-04T04:05:03.000+00:00",
            "draw_id_override": None,
            "capture_record_count": len(self.records),
            "capture_records_canonical_sha256": capture_order.canonical_sha256(
                self.records
            ),
            "results": results,
            "rest_payloads": payloads,
        }
        self.capture.write_text(
            "".join(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                for record in self.records
            ),
            encoding="utf-8",
        )
        self.validation.write_text(
            json.dumps(self.validation_value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        capture_order.export_order(
            self.records, self.ordered, self.validation_value
        )
        write_checkpoint(self.checkpoint, [record["balls"] for record in self.records])

    def tearDown(self):
        self.temporary.cleanup()

    def create(self):
        return proof_bundle.create_bundle(
            self.bundle,
            capture=self.capture,
            validation=self.validation,
            ordered=self.ordered,
            export_manifest=self.export_manifest,
            checkpoint=self.checkpoint,
            capture_implementation=HERE / "capture_order.py",
            solver_implementation=HERE / "keno_break.c",
        )

    def test_create_and_verify_recomputes_complete_chain(self):
        digest = self.create()
        result = proof_bundle.verify_bundle(self.bundle, digest)
        value = json.loads(self.bundle.read_text(encoding="utf-8"))

        self.assertEqual(result["verdict"], "CONSISTENT_EVIDENCE_CHAIN")
        self.assertTrue(result["independent_digest_checked"])
        self.assertEqual((result["first_draw_id"], result["last_draw_id"]), (101, 102))
        self.assertEqual(result["next_draw_id"], 103)
        self.assertEqual(result["order_scope"], "ANIMATION_SEQUENCE_ONLY")
        self.assertEqual(value["chain"]["draws"][0]["balls"], self.records[0]["balls"])
        self.assertEqual(value["chain"]["checkpoint"]["draws_consumed"], 2)
        self.assertEqual(value["hash_algorithm"], "SHA-256")
        self.assertEqual(stat.S_IMODE(self.bundle.stat().st_mode), 0o600)

    def test_ordered_dataset_tampering_is_rejected(self):
        digest = self.create()
        lines = self.ordered.read_text(encoding="ascii").splitlines()
        lines[0] = " ".join(reversed(lines[0].split()))
        self.ordered.write_text("\n".join(lines) + "\n", encoding="ascii")
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "size/SHA-256 mismatch"):
            proof_bundle.verify_bundle(self.bundle, digest)

    def test_source_code_tampering_is_rejected(self):
        capture_copy = self.directory / "capture_order.py"
        solver_copy = self.directory / "keno_break.c"
        capture_copy.write_bytes((HERE / "capture_order.py").read_bytes())
        solver_copy.write_bytes((HERE / "keno_break.c").read_bytes())
        digest = proof_bundle.create_bundle(
            self.bundle,
            capture=self.capture,
            validation=self.validation,
            ordered=self.ordered,
            export_manifest=self.export_manifest,
            checkpoint=self.checkpoint,
            capture_implementation=capture_copy,
            solver_implementation=solver_copy,
        )
        solver_copy.write_bytes(solver_copy.read_bytes() + b"\n")
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "size/SHA-256 mismatch"):
            proof_bundle.verify_bundle(self.bundle, digest)

    def test_checkpoint_must_be_bound_to_all_ordered_draws(self):
        write_checkpoint(
            self.checkpoint,
            [record["balls"] for record in self.records],
            wrong_input=True,
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "differs from ordered"):
            self.create()

    def test_checkpoint_index_must_match_consumed_stride(self):
        write_checkpoint(
            self.checkpoint,
            [record["balls"] for record in self.records],
            mti=39,
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "mti is inconsistent"):
            self.create()

    def test_recomputed_manifest_cannot_forge_verified_order(self):
        forged = json.loads(self.validation.read_text(encoding="utf-8"))
        forged["results"][0]["verdict"] = "VERIFIED_ORDER"
        forged["results"][0]["animation"]["balls"][0] = 77
        self.validation.write_text(
            json.dumps(forged, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "validation failed"):
            self.create()

    def test_bundle_requires_canonical_duplicate_free_json(self):
        self.create()
        original = self.bundle.read_text(encoding="utf-8")
        self.bundle.write_text(
            original.replace('{"artifacts":', '{"schema":"evil","artifacts":', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "duplicate JSON key"):
            proof_bundle.verify_bundle(self.bundle)

    def test_independent_digest_detects_manifest_replacement(self):
        digest = self.create()
        value = json.loads(self.bundle.read_text(encoding="utf-8"))
        value["security_model"] = dict(value["security_model"])
        value["security_model"]["not_guaranteed"] = "nothing"
        self.bundle.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "independent commitment"):
            proof_bundle.verify_bundle(self.bundle, digest)

    def test_json_boolean_cannot_substitute_for_integer_version_or_ball(self):
        self.create()
        value = json.loads(self.bundle.read_text(encoding="utf-8"))
        value["version"] = True
        self.bundle.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "unsupported"):
            proof_bundle.verify_bundle(self.bundle)

        self.bundle.unlink()
        self.create()
        value = json.loads(self.bundle.read_text(encoding="utf-8"))
        value["chain"]["draws"][0]["balls"][1] = True
        self.bundle.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "summary differs"):
            proof_bundle.verify_bundle(self.bundle)

    def test_cli_prints_digest_and_checks_it(self):
        command = [
            sys.executable,
            str(HERE / "proof_bundle.py"),
            "create",
            str(self.bundle),
            "--capture",
            str(self.capture),
            "--validation",
            str(self.validation),
            "--ordered",
            str(self.ordered),
            "--export-manifest",
            str(self.export_manifest),
            "--checkpoint",
            str(self.checkpoint),
        ]
        created = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(created.returncode, 0, created.stderr)
        created_result = json.loads(created.stdout)
        digest = created_result["bundle_sha256"]
        self.assertFalse(created_result["independent_digest_checked"])
        verified = subprocess.run(
            [
                sys.executable,
                str(HERE / "proof_bundle.py"),
                "verify",
                str(self.bundle),
                "--expect-sha256",
                digest,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertTrue(json.loads(verified.stdout)["independent_digest_checked"])

    def test_unrecognized_implementation_sources_are_rejected(self):
        fake_capture = self.directory / "fake_capture.py"
        fake_solver = self.directory / "fake_solver.c"
        fake_capture.write_text("this is not Python\n", encoding="ascii")
        fake_solver.write_text("this is not C\n", encoding="ascii")
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "not recognized|differs"):
            proof_bundle.create_bundle(
                self.bundle,
                capture=self.capture,
                validation=self.validation,
                ordered=self.ordered,
                export_manifest=self.export_manifest,
                checkpoint=self.checkpoint,
                capture_implementation=fake_capture,
                solver_implementation=fake_solver,
            )

    def test_existing_proof_is_never_overwritten(self):
        self.bundle.write_bytes(b"already committed\n")
        with self.assertRaisesRegex(proof_bundle.EvidenceError, "already exists"):
            self.create()
        self.assertEqual(self.bundle.read_bytes(), b"already committed\n")


if __name__ == "__main__":
    unittest.main()
