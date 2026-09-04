import asyncio
import base64
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import capture_campaign
import capture_order


BALLS = [20, 1, 80] + list(range(2, 19))


def candidate(draw_id=101, cutoff="2026-09-04T04:05:00+00:00"):
    return capture_campaign.Candidate(
        draw_id=draw_id,
        draw_date=cutoff,
        wager_end_date=cutoff,
        wager_end_ns=capture_campaign.parse_aware_iso_ns(cutoff),
        phase="OPEN",
    )


def captured(
    draw_id=101, *, scene="DrawScene", balls=None, boost=2, extra=20, tick=1
):
    values = BALLS if balls is None else balls
    metadata = {"id": draw_id, "balls": values}
    if boost is not None:
        metadata["boost"] = boost
    if extra is not None:
        metadata["extra"] = extra
    raw = {
        "scene": scene,
        "duration": 110000,
        "startTime": 0,
        "endTime": 110000,
        "progress": 500,
        "meta": {
            "fr-ch": metadata
        },
    }
    received_ns = int(
        datetime(2026, 9, 4, 4, 5, tick, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    record = capture_order.extract_state(
        raw,
        received_at=f"2026-09-04T04:05:{tick:02d}.000+00:00",
        received_unix_ns=received_ns,
        received_monotonic_ns=1_000_000_000 + tick,
        expected_draw_id=draw_id,
        session_id="00000000000000000000000000000001",
        frame_index=tick,
    )
    message = {"type": 1, "target": "SendCurrentState", "arguments": [raw]}
    wire = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    record.update({
        "message_index": 0,
        "hub_message_raw": wire,
        "hub_message_sha256": hashlib.sha256(wire.encode()).hexdigest(),
        "hub_message_canonical_sha256": capture_order.canonical_sha256(message),
    })
    return record


def rest_payload(
    draw_id=101,
    numbers=None,
    draw_date="2026-09-04T04:05:00+00:00",
    wager_end_date="2026-09-04T04:05:00+00:00",
):
    values = sorted(BALLS) if numbers is None else numbers
    return {
        "drawNumber": draw_id,
        "drawDate": draw_date,
        "wagerEndDate": wager_end_date,
        "phase": "RESULTS_AVAILABLE",
        "drawResult": {
            "matrix1": {
                "main": values,
                "boost": [2],
                "bonus": [20],
            }
        },
    }


def report_for(
    records,
    draw_id=101,
    *,
    numbers=None,
    fake_verdict=None,
    draw_date="2026-09-04T04:05:00+00:00",
    wager_end_date="2026-09-04T04:05:00+00:00",
):
    payload = rest_payload(draw_id, numbers, draw_date, wager_end_date)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    wall_ns = int(
        datetime(2026, 9, 4, 4, 5, 2, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    evidence = {
        "url": capture_order.REST_DRAW_URL.format(draw_id=draw_id) + "?_=1&l=fr-CH",
        "status": 200,
        "http_date": "Fri, 04 Sep 2026 04:05:02 GMT",
        "server_unix_ns": wall_ns,
        "request_wall_ns": wall_ns,
        "response_wall_ns": wall_ns + 10_000_000,
        "request_monotonic_ns": 2_000_000_000,
        "response_monotonic_ns": 2_010_000_000,
        "rtt_ms": 10.0,
        "server_clock_offset_ms": -5.0,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "body_base64": base64.b64encode(body).decode("ascii"),
    }
    record, first_seen, auxiliary = capture_order.validation_records_for_draw(
        records, draw_id, True
    )
    result = capture_order.verify_record(
        record,
        capture_order.parse_rest_draw(payload),
        evidence,
        draw_id,
        first_seen,
        auxiliary,
    )
    if fake_verdict is not None:
        result["verdict"] = fake_verdict
    return {
        "schema": 2,
        "validated_at": "2026-09-04T04:05:03.000+00:00",
        "draw_id_override": draw_id,
        "capture_record_count": len(records),
        "capture_records_canonical_sha256": capture_order.canonical_sha256(records),
        "results": [result],
        "rest_payloads": {
            str(draw_id): {
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
                "encoding": "base64",
                "body_base64": base64.b64encode(body).decode("ascii"),
            }
        },
    }


class CandidateTests(unittest.TestCase):
    def test_selects_earliest_cutoff_then_id(self):
        payload = {
            "results": [
                {
                    "drawNumber": 103,
                    "drawDate": "2026-09-04T04:15:00Z",
                    "wagerEndDate": "2026-09-04T04:15:00Z",
                    "phase": "OPEN",
                },
                {
                    "drawNumber": 102,
                    "drawDate": "2026-09-04T04:10:00Z",
                    "wagerEndDate": "2026-09-04T04:10:00Z",
                    "phase": "OPEN",
                },
                {
                    "drawNumber": 101,
                    "drawDate": "2026-09-04T04:10:00Z",
                    "wagerEndDate": "2026-09-04T04:10:00Z",
                    "phase": "OPEN",
                },
            ]
        }
        now_ns = capture_campaign.parse_aware_iso_ns("2026-09-04T04:00:00Z")
        selected = capture_campaign.select_next_candidate(payload, now_ns)
        self.assertEqual(selected.draw_id, 101)

    def test_skips_stale_complete_and_malformed_rows(self):
        payload = {
            "results": [
                {
                    "drawNumber": 99,
                    "drawDate": "2026-09-04T03:00:00Z",
                    "wagerEndDate": "2026-09-04T03:00:00Z",
                    "phase": "OPEN",
                },
                {
                    "drawNumber": 100,
                    "drawDate": "2026-09-04T04:05:00Z",
                    "wagerEndDate": "2026-09-04T04:05:00Z",
                    "phase": "RESULTS_AVAILABLE",
                },
                {"drawNumber": True, "drawDate": "bad"},
                {
                    "drawNumber": 101,
                    "drawDate": "2026-09-04T04:10:00Z",
                    "wagerEndDate": "2026-09-04T04:10:00Z",
                },
            ]
        }
        now_ns = capture_campaign.parse_aware_iso_ns("2026-09-04T04:00:00Z")
        self.assertEqual(
            capture_campaign.select_next_candidate(payload, now_ns).draw_id, 101
        )

    def test_conflicting_duplicate_id_is_rejected(self):
        payload = {"results": [
            {
                "drawNumber": 101,
                "drawDate": "2026-09-04T04:05:00Z",
                "wagerEndDate": "2026-09-04T04:05:00Z",
            },
            {
                "drawNumber": 101,
                "drawDate": "2026-09-04T04:10:00Z",
                "wagerEndDate": "2026-09-04T04:10:00Z",
            },
        ]}
        now_ns = capture_campaign.parse_aware_iso_ns("2026-09-04T04:00:00Z")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            capture_campaign.select_next_candidate(payload, now_ns)

    def test_naive_timestamps_are_not_eligible(self):
        payload = {"results": [{
            "drawNumber": 101,
            "drawDate": "2026-09-04T04:05:00",
            "wagerEndDate": "2026-09-04T04:05:00",
        }]}
        with self.assertRaisesRegex(ValueError, "no eligible"):
            capture_campaign.select_next_candidate(payload, 1)

    def test_discovery_evidence_is_bound_to_official_exact_body(self):
        payload = {"results": []}
        body = json.dumps(payload, separators=(",", ":")).encode()
        evidence = {
            "url": capture_campaign.REST_DRAWS_URL + "?status=OPEN",
            "status": 200,
            "body_base64": base64.b64encode(body).decode(),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_bytes": len(body),
        }
        capture_campaign.validate_discovery_evidence(payload, evidence)
        evidence["url"] = "https://attacker.invalid/draws"
        with self.assertRaisesRegex(ValueError, "official"):
            capture_campaign.validate_discovery_evidence(payload, evidence)

    def test_discovery_evidence_rejects_changed_body(self):
        payload = {"results": []}
        body = b'{"results":[1]}'
        evidence = {
            "url": capture_campaign.REST_DRAWS_URL,
            "status": 200,
            "body_base64": base64.b64encode(body).decode(),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_bytes": len(body),
        }
        with self.assertRaisesRegex(ValueError, "differs"):
            capture_campaign.validate_discovery_evidence(payload, evidence)


class ChainTests(unittest.TestCase):
    def test_append_chain_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            first = capture_campaign.append_chain(path, "ONE", {"value": 1})
            second = capture_campaign.append_chain(path, "TWO", {"value": 2})
            rows = capture_campaign.read_chain(path)
            self.assertEqual([row["event"] for row in rows], ["ONE", "TWO"])
            self.assertEqual(second["previous_entry_sha256"], first["entry_sha256"])
            text = path.read_text().replace('"value": 1', '"value": 9', 1)
            path.write_text(text)
            with self.assertRaisesRegex(capture_campaign.CampaignIntegrityError, "SHA-256"):
                capture_campaign.read_chain(path)

    def test_partial_tail_is_rejected_not_silently_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            capture_campaign.append_chain(path, "ONE", {})
            with path.open("ab") as handle:
                handle.write(b'{"partial":true}')
            with self.assertRaisesRegex(capture_campaign.CampaignIntegrityError, "partial"):
                capture_campaign.read_chain(path)

    def test_symlinked_chain_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("")
            link = root / "events.jsonl"
            link.symlink_to(target)
            with self.assertRaisesRegex(capture_campaign.CampaignIntegrityError, "symlink"):
                capture_campaign.read_chain(link)


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def _capture(self, path, _locale, _duration, _events, _draws, draw_id, _verbose):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(captured(draw_id), sort_keys=True) + "\n")
        return {"events": 1, "full_draws": 1}

    async def test_verified_draw_is_promoted_once_and_reverified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = capture_campaign.CampaignConfig(max_draws=1)

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            first = await capture_campaign.process_draw(
                root, candidate(), config,
                capture_func=self._capture, validate_func=validate,
            )
            self.assertEqual(first, "VERIFIED_ORDER")
            rows = capture_campaign.verify_manifest(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["balls"], BALLS)
            data = root / "datasets" / "ordered-101-101.txt"
            self.assertEqual(data.read_text(), " ".join(map(str, BALLS)) + "\n")

            never_capture = mock.AsyncMock(side_effect=AssertionError("recaptured"))
            second = await capture_campaign.process_draw(
                root, candidate(), config,
                capture_func=never_capture, validate_func=validate,
            )
            self.assertEqual(second, "ALREADY_VERIFIED")
            never_capture.assert_not_awaited()
            self.assertEqual(len(capture_campaign.verify_manifest(root)), 1)

    async def test_delayed_extra_scene_is_promoted_with_animation_scope(self):
        async def capture_delayed(
            path, _locale, _duration, _events, _draws, draw_id, _verbose
        ):
            records = [
                captured(draw_id, extra=None, tick=1),
                captured(draw_id, scene="ExtraScene", tick=2),
            ]
            with path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
            return {"events": 2, "full_draws": 1}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            outcome = await capture_campaign.process_draw(
                root,
                candidate(),
                capture_campaign.CampaignConfig(),
                capture_func=capture_delayed,
                validate_func=validate,
            )
            rows = capture_campaign.verify_manifest(root)
            export_manifest = capture_order.read_jsonl(
                root / "draws" / "101" / "ordered.txt.manifest.jsonl"
            )

        self.assertEqual(outcome, "VERIFIED_ORDER")
        self.assertEqual(rows[0]["order_scope"], "ANIMATION_SEQUENCE_ONLY")
        self.assertEqual(export_manifest[0]["order_scope"], "ANIMATION_SEQUENCE_ONLY")

    async def test_preloaded_capture_without_live_receipt_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture_path = root / "draws" / "101" / "capture.jsonl"
            capture_path.parent.mkdir(parents=True)
            capture_path.write_text(json.dumps(captured()) + "\n")
            never_capture = mock.AsyncMock(side_effect=AssertionError("should not overwrite"))
            validate = mock.Mock(side_effect=AssertionError("should not validate"))
            with self.assertRaisesRegex(
                capture_campaign.CampaignIntegrityError, "preloaded evidence"
            ):
                await capture_campaign.process_draw(
                    root, candidate(), capture_campaign.CampaignConfig(),
                    capture_func=never_capture, validate_func=validate,
                )
            never_capture.assert_not_awaited()
            validate.assert_not_called()
            self.assertEqual(capture_campaign.verify_manifest(root), [])

    async def test_mismatch_is_not_exported_or_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id, numbers=list(range(1, 21)))

            outcome = await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=self._capture, validate_func=validate,
            )
            self.assertEqual(outcome, "MISMATCH")
            self.assertEqual(capture_campaign.verify_manifest(root), [])
            self.assertFalse((root / "draws" / "101" / "ordered.txt").exists())

    async def test_invalid_rest_chronology_cannot_poison_append_only_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def validate(records, draw_id, _retry, _interval):
                return report_for(
                    records,
                    draw_id,
                    draw_date="2026-09-04T04:05:00",
                    wager_end_date="2026-09-04T04:05:00",
                )

            with self.assertRaisesRegex(
                capture_campaign.CampaignIntegrityError, "timezone-aware"
            ):
                await capture_campaign.process_draw(
                    root, candidate(), capture_campaign.CampaignConfig(),
                    capture_func=self._capture, validate_func=validate,
                )
            self.assertEqual(capture_campaign.read_chain(root / capture_campaign.MANIFEST_NAME), [])
            self.assertFalse((root / "draws" / "101" / "ordered.txt").exists())

    async def test_fabricated_verified_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def validate(records, draw_id, _retry, _interval):
                return report_for(
                    records, draw_id, numbers=list(range(1, 21)),
                    fake_verdict="VERIFIED_ORDER",
                )

            with self.assertRaisesRegex(ValueError, "differs from recomputation"):
                await capture_campaign.process_draw(
                    root, candidate(), capture_campaign.CampaignConfig(),
                    capture_func=self._capture, validate_func=validate,
                )
            self.assertEqual(capture_campaign.verify_manifest(root), [])

    async def test_missing_drawscene_never_calls_rest_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            async def capture_reorder(path, _locale, _duration, _events, _draws, draw_id, _verbose):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(captured(draw_id, scene="ReorderScene")) + "\n")
                return {"events": 1, "full_draws": 0}

            validate = mock.Mock(side_effect=AssertionError("REST validation called"))
            outcome = await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=capture_reorder, validate_func=validate,
            )
            self.assertEqual(outcome, "NO_OBSERVATION")
            validate.assert_not_called()
            self.assertEqual(capture_campaign.verify_manifest(root), [])

    async def test_sorted_drawscene_is_distinguished_from_no_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            async def capture_sorted(path, _locale, _duration, _events, _draws, draw_id, _verbose):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(captured(draw_id, balls=sorted(BALLS))) + "\n")
                return {"events": 1, "full_draws": 0}

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            outcome = await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=capture_sorted, validate_func=validate,
            )
            self.assertEqual(outcome, "SORTED_NOT_ORDERED")
            self.assertEqual(capture_campaign.verify_manifest(root), [])
            self.assertFalse((root / "draws" / "101" / "ordered.txt").exists())

    async def test_resume_after_validation_failure_reuses_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def fail_validation(_records, _draw_id, _retry, _interval):
                raise OSError("temporary REST outage")

            with self.assertRaisesRegex(OSError, "temporary"):
                await capture_campaign.process_draw(
                    root, candidate(), capture_campaign.CampaignConfig(),
                    capture_func=self._capture, validate_func=fail_validation,
                )
            capture_path = root / "draws" / "101" / "capture.jsonl"
            before = capture_path.read_bytes()

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            never_capture = mock.AsyncMock(side_effect=AssertionError("recaptured"))
            outcome = await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=never_capture, validate_func=validate,
            )
            self.assertEqual(outcome, "VERIFIED_ORDER")
            never_capture.assert_not_awaited()
            self.assertEqual(capture_path.read_bytes(), before)

    async def test_capture_interruption_with_unreceipted_order_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = candidate()
            body = b'{"results":[]}'
            evidence = {
                "body_base64": base64.b64encode(body).decode(),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
            }
            capture_campaign.append_chain(
                root / capture_campaign.JOURNAL_NAME,
                "DISCOVERED",
                capture_campaign._discovery_journal_fields(item, {"results": []}, evidence),
            )
            capture_path = root / "draws" / "101" / "capture.jsonl"
            capture_path.parent.mkdir(parents=True)
            capture_campaign.append_chain(
                root / capture_campaign.JOURNAL_NAME,
                "CAPTURE_STARTED",
                {
                    "draw_id": 101,
                    "wager_end_date": item.wager_end_date,
                    "capture_path": "draws/101/capture.jsonl",
                },
            )
            capture_path.write_text(json.dumps(captured()) + "\n")

            never_capture = mock.AsyncMock(side_effect=AssertionError("recaptured"))
            validate = mock.Mock(side_effect=AssertionError("validated unreceipted data"))
            with self.assertRaisesRegex(
                capture_campaign.CampaignIntegrityError, "preloaded evidence"
            ):
                await capture_campaign.process_draw(
                    root, item, capture_campaign.CampaignConfig(),
                    capture_func=never_capture, validate_func=validate,
                )
            never_capture.assert_not_awaited()
            validate.assert_not_called()
            self.assertEqual(capture_campaign.verify_manifest(root), [])

    async def test_manifest_detects_artifact_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=self._capture, validate_func=validate,
            )
            validation_path = root / "draws" / "101" / "validation.json"
            with validation_path.open("a") as handle:
                handle.write(" ")
            with self.assertRaisesRegex(
                capture_campaign.CampaignIntegrityError, "artifact SHA-256"
            ):
                capture_campaign.verify_manifest(root)


class DatasetTests(unittest.TestCase):
    def test_gaps_become_separate_solver_inputs(self):
        rows = [
            {"draw_id": 10, "draw_date": "2026-09-04T04:00:00Z", "balls": BALLS},
            {"draw_id": 11, "draw_date": "2026-09-04T04:05:00Z", "balls": list(reversed(BALLS))},
            {"draw_id": 13, "draw_date": "2026-09-04T04:15:00Z", "balls": BALLS},
        ]
        segments = capture_campaign.contiguous_segments(rows)
        self.assertEqual([[r["draw_id"] for r in segment] for segment in segments], [[10, 11], [13]])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = capture_campaign.rebuild_datasets(root, rows)
            self.assertEqual([segment["draws"] for segment in index["segments"]], [2, 1])
            first = root / index["segments"][0]["data"]
            self.assertEqual(len(first.read_text().splitlines()), 2)

    def test_consecutive_ids_across_night_are_separate(self):
        rows = [
            {"draw_id": 20, "draw_date": "2026-09-04T20:00:00Z", "balls": BALLS},
            {"draw_id": 21, "draw_date": "2026-09-05T05:00:00Z", "balls": BALLS},
        ]
        segments = capture_campaign.contiguous_segments(rows)
        self.assertEqual([len(segment) for segment in segments], [1, 1])
        with tempfile.TemporaryDirectory() as directory:
            index = capture_campaign.rebuild_datasets(Path(directory), rows)
            boundary = index["segments"][1]["boundary_from_previous"]
            self.assertEqual(boundary["draw_time_gap_seconds"], 9 * 60 * 60)
            self.assertIn("TIME_GAP_OR_SESSION_BOUNDARY", boundary["reasons"])

    def test_small_timestamp_drift_is_tolerated_but_larger_is_split(self):
        base = {"draw_id": 30, "draw_date": "2026-09-04T04:00:00Z", "balls": BALLS}
        within = {"draw_id": 31, "draw_date": "2026-09-04T04:05:05Z", "balls": BALLS}
        outside = {"draw_id": 32, "draw_date": "2026-09-04T04:10:11Z", "balls": BALLS}
        self.assertEqual(
            [len(segment) for segment in capture_campaign.contiguous_segments([base, within, outside])],
            [2, 1],
        )


class RunTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_candidate_is_processed_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = candidate(cutoff="2026-09-04T04:00:00Z")
            body = b'{"results":[]}'
            evidence = {
                "status": 200,
                "server_unix_ns": item.wager_end_ns,
                "response_wall_ns": item.wager_end_ns,
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
                "body_base64": base64.b64encode(body).decode(),
            }
            discover = mock.Mock(return_value=(item, {"results": []}, evidence))
            process = mock.AsyncMock(return_value="NO_OBSERVATION")
            result = await capture_campaign.run_campaign(
                root,
                capture_campaign.CampaignConfig(max_draws=1, capture_lead_seconds=0),
                discover_func=discover,
                process_func=process,
            )
            self.assertEqual(result["outcomes"], {101: "NO_OBSERVATION"})
            process.assert_awaited_once()
            events = [row["event"] for row in capture_campaign.read_chain(root / capture_campaign.JOURNAL_NAME)]
            self.assertEqual(events, ["CAMPAIGN_STARTED", "DISCOVERED", "CAMPAIGN_STOPPED"])

    async def test_max_runtime_stops_repeated_discovery_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            discover = mock.Mock(side_effect=OSError("offline"))
            result = await capture_campaign.run_campaign(
                root,
                capture_campaign.CampaignConfig(
                    max_draws=1, max_runtime=0.02, discovery_interval=0.001
                ),
                discover_func=discover,
            )
            self.assertEqual(result["completed_draws"], 0)
            events = [row["event"] for row in capture_campaign.read_chain(root / capture_campaign.JOURNAL_NAME)]
            self.assertEqual(events[0], "CAMPAIGN_STARTED")
            self.assertIn("DISCOVERY_FAILED", events)
            self.assertEqual(events[-1], "CAMPAIGN_STOPPED")

    async def test_restart_prioritizes_pending_validation_before_new_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = candidate()
            payload = {"results": []}
            body = json.dumps(payload, separators=(",", ":")).encode()
            evidence = {
                "body_base64": base64.b64encode(body).decode(),
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
            }
            capture_campaign.append_chain(
                root / capture_campaign.JOURNAL_NAME,
                "DISCOVERED",
                capture_campaign._discovery_journal_fields(item, payload, evidence),
            )

            async def capture(path, _locale, _duration, _events, _draws, draw_id, _verbose):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(captured(draw_id)) + "\n")
                return {"events": 1, "full_draws": 1}

            def fail_validation(_records, _draw_id, _retry, _interval):
                raise OSError("interrupted REST phase")

            with self.assertRaises(OSError):
                await capture_campaign.process_draw(
                    root, item, capture_campaign.CampaignConfig(),
                    capture_func=capture, validate_func=fail_validation,
                )

            never_capture = mock.AsyncMock(side_effect=AssertionError("recaptured"))

            async def resume(root_path, pending, config):
                def validate(records, draw_id, _retry, _interval):
                    return report_for(records, draw_id)
                return await capture_campaign.process_draw(
                    root_path, pending, config,
                    capture_func=never_capture, validate_func=validate,
                )

            discover = mock.Mock(side_effect=AssertionError("new draw discovered first"))
            result = await capture_campaign.run_campaign(
                root,
                capture_campaign.CampaignConfig(max_draws=1),
                discover_func=discover,
                process_func=resume,
            )
            self.assertEqual(result["outcomes"], {101: "VERIFIED_ORDER"})
            discover.assert_not_called()
            never_capture.assert_not_awaited()


class ManifestAdversaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_verified_draw_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            async def capture(path, _locale, _duration, _events, _draws, draw_id, _verbose):
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(captured(draw_id)) + "\n")
                return {"events": 1, "full_draws": 1}

            def validate(records, draw_id, _retry, _interval):
                return report_for(records, draw_id)

            await capture_campaign.process_draw(
                root, candidate(), capture_campaign.CampaignConfig(),
                capture_func=capture, validate_func=validate,
            )
            original = capture_campaign.verify_manifest(root)[0]
            duplicate_fields = {
                key: value for key, value in original.items()
                if key not in {
                    "schema", "sequence", "recorded_at", "event",
                    "previous_entry_sha256", "entry_sha256",
                }
            }
            capture_campaign.append_chain(
                root / capture_campaign.MANIFEST_NAME,
                "VERIFIED_ORDER",
                duplicate_fields,
            )
            with self.assertRaisesRegex(
                capture_campaign.CampaignIntegrityError, "malformed draw"
            ):
                capture_campaign.verify_manifest(root)


if __name__ == "__main__":
    unittest.main()
