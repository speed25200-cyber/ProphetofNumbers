import base64
import hashlib
import asyncio
import contextlib
import io
import json
import logging
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from unittest import mock
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
                "balls": balls if balls is not None else [20, 1, 80] + list(range(2, 19)),
                "boost": 2,
                "extra": 20,
            }
        },
    }


def rest(draw_id=101, balls=None, boost="2.0", bonus="20"):
    values = balls if balls is not None else sorted(state(draw_id)["meta"]["fr-ch"]["balls"])
    return {
        "drawNumber": draw_id,
        "drawDate": "2026-09-04T04:05:00+00:00",
        "wagerEndDate": "2026-09-04T04:05:00+00:00",
        "phase": "PAYABLE",
        "drawResult": {
            "matrix1": {
                "main": [str(value) for value in values],
                "boost": [boost],
                "bonus": [bonus],
            }
        },
    }


def captured(draw_id=101, balls=None, scene="DrawScene", *, raw_state=None, tick=1):
    payload = raw_state if raw_state is not None else state(draw_id, balls, scene)
    received_ns = int(
        datetime(2026, 9, 4, 4, 5, tick, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    record = capture_order.extract_state(
        payload,
        received_at=f"2026-09-04T04:05:{tick:02d}.000+00:00",
        received_unix_ns=received_ns,
        received_monotonic_ns=10_000_000_000 + tick,
        session_id="00000000000000000000000000000001",
        frame_index=tick,
    )
    message = {"type": 1, "target": "SendCurrentState", "arguments": [payload]}
    wire = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    record.update({
        "message_index": 0,
        "hub_message_raw": wire,
        "hub_message_sha256": hashlib.sha256(wire.encode()).hexdigest(),
        "hub_message_canonical_sha256": capture_order.canonical_sha256(message),
    })
    return record


def rest_evidence(draw_id=101, payload=None):
    payload = payload if payload is not None else rest(draw_id)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    request_wall = int(
        datetime(2026, 9, 4, 4, 5, 2, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    response_wall = request_wall + 10_000_000
    server_ns = request_wall
    evidence = {
        "url": capture_order.REST_DRAW_URL.format(draw_id=draw_id) + "?_=1&l=fr-CH",
        "status": 200,
        "http_date": "Fri, 04 Sep 2026 04:05:02 GMT",
        "server_unix_ns": server_ns,
        "request_wall_ns": request_wall,
        "response_wall_ns": response_wall,
        "request_monotonic_ns": 1_000_000_000,
        "response_monotonic_ns": 1_010_000_000,
        "rtt_ms": 10.0,
        "server_clock_offset_ms": -5.0,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "body_base64": base64.b64encode(body).decode("ascii"),
    }
    return body, evidence


def validation_for(records, record=None, first_seen=None, payload=None, target_id=None):
    record = record or records[0]
    first_seen = first_seen or record
    target_id = record["draw_id"] if target_id is None else target_id
    payload = payload if payload is not None else rest(target_id)
    body, evidence = rest_evidence(target_id, payload)
    result = capture_order.verify_record(
        record,
        capture_order.parse_rest_draw(payload),
        evidence,
        target_id,
        first_seen,
    )
    return {
        "schema": 2,
        "validated_at": "2026-09-04T04:05:03.000+00:00",
        "draw_id_override": target_id if record.get("draw_id") is None else None,
        "capture_record_count": len(records),
        "capture_records_canonical_sha256": capture_order.canonical_sha256(records),
        "results": [result],
        "rest_payloads": {
            str(target_id): {
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_bytes": len(body),
                "encoding": "base64",
                "body_base64": base64.b64encode(body).decode("ascii"),
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

    def test_decoder_preserves_split_utf8_records(self):
        messages = [
            {},
            {"type": 1, "target": "SendCurrentState", "arguments": [{"scene": "Tiragé"}]},
            {"type": 3, "invocationId": "1"},
        ]
        wire = "".join(json.dumps(item, ensure_ascii=False) + "\x1e" for item in messages).encode()
        decoder = capture_order.SignalRTextDecoder()
        decoded = []
        for byte in wire:
            decoded.extend(decoder.feed(bytes([byte])))
        self.assertEqual(decoded, messages)
        self.assertEqual(decoder.buffer, "")

    def test_decoder_rejects_malformed_complete_record(self):
        decoder = capture_order.SignalRTextDecoder()
        with self.assertRaisesRegex(ValueError, "invalid complete"):
            decoder.feed('{"broken":' + "\x1e")

    def test_websocket_url_replaces_existing_token(self):
        url = capture_order.websocket_url(
            "https://example.invalid/client/?hub=x&access_token=old", "new token"
        )
        query = dict(capture_order.urllib.parse.parse_qsl(capture_order.urllib.parse.urlsplit(url).query))
        self.assertEqual(query["access_token"], "new token")
        self.assertEqual(url.count("access_token="), 1)

    def test_websocket_url_preserves_azure_route_bytes(self):
        route = "hub=x&asrs.op=%2Fclient%2F%3Fa%3D1%2B2&asrs_request_id=a%2Bb"
        url = capture_order.websocket_url(f"https://example.invalid/client/?{route}", "token")
        self.assertEqual(capture_order.urllib.parse.urlsplit(url).query.split("&access_token=")[0], route)

    def test_websocket_url_supports_only_web_schemes(self):
        expected = {"https": "wss", "http": "ws", "wss": "wss", "ws": "ws"}
        for source, target in expected.items():
            with self.subTest(source=source):
                url = capture_order.websocket_url(f"{source}://example.invalid/client", "token")
                self.assertEqual(capture_order.urllib.parse.urlsplit(url).scheme, target)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            capture_order.websocket_url("ftp://example.invalid/client", "token")

    def test_plain_night_state_is_not_a_draw(self):
        record = capture_order.extract_state({"scene": "NightModeScene", "meta": {"fr-ch": {}}})
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_locale_with_balls_wins_over_empty_preference(self):
        payload = state()
        payload["meta"] = {
            "fr_CH": {"text": "pas encore"},
            "de_CH": {"id": 101, "balls": [20, 1, 80] + list(range(2, 19)), "boost": ["2.0"], "extra": ["20"]},
        }
        record = capture_order.extract_state(payload)
        self.assertEqual(record["locale"], "de-ch")
        self.assertTrue(capture_order.valid_full_draw(record))
        self.assertEqual(record["boost"], 2)
        self.assertEqual(record["extra"], 20)

    def test_empty_preferred_ball_list_does_not_mask_complete_locale(self):
        payload = state()
        payload["meta"] = {
            "fr-ch": {"id": 101, "balls": []},
            "de-ch": payload["meta"]["fr-ch"],
        }
        record = capture_order.extract_state(payload)
        self.assertEqual(record["locale"], "de-ch")
        self.assertTrue(capture_order.valid_full_draw(record))

    def test_conflicting_locales_are_quarantined(self):
        payload = state()
        payload["meta"]["de-ch"] = {
            "id": 101,
            "balls": list(reversed(payload["meta"]["fr-ch"]["balls"])),
        }
        record = capture_order.extract_state(payload)
        self.assertTrue(record["locale_conflict"])
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_conflicting_normalized_locale_keys_are_quarantined(self):
        payload = state()
        payload["meta"]["fr_CH"] = {
            "id": 101,
            "balls": list(reversed(payload["meta"]["fr-ch"]["balls"])),
        }
        record = capture_order.extract_state(payload)
        self.assertTrue(record["locale_conflict"])
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_invalid_21_item_sequence_is_not_compacted_to_valid(self):
        values = [20, 1, 80] + list(range(2, 19)) + [None]
        record = capture_order.extract_state(state(balls=values))
        self.assertEqual(len(record["balls"]), 20)
        self.assertEqual(record["balls_raw_count"], 21)
        self.assertEqual(record["balls_parse_errors"], 1)
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_boolean_ids_and_balls_are_not_integers(self):
        payload = state(draw_id=True)
        payload["meta"]["fr-ch"]["balls"][0] = True
        record = capture_order.extract_state(payload)
        self.assertIsNone(record["draw_id"])
        self.assertFalse(capture_order.valid_ball_sequence(record))

    def test_ball_object_tries_all_supported_keys(self):
        self.assertEqual(capture_order.ball_value({"value": "bad", "number": "42"}), 42)
        self.assertIsNone(capture_order.ball_value({"value": 41, "number": 42}))

    def test_state_without_id_can_use_explicit_correlation(self):
        payload = state()
        del payload["meta"]["fr-ch"]["id"]
        pending = capture_order.extract_state(payload)
        correlated = capture_order.extract_state(payload, expected_draw_id=101)
        self.assertTrue(capture_order.valid_ball_sequence(pending))
        self.assertFalse(capture_order.valid_full_draw(pending))
        self.assertTrue(capture_order.valid_full_draw(correlated))
        self.assertEqual(correlated["draw_id_source"], "expected")

    def test_zero_signalr_id_is_not_replaced_by_expected_id(self):
        record = capture_order.extract_state(state(draw_id=0), expected_draw_id=101)
        self.assertEqual(record["draw_id"], 0)
        self.assertTrue(record["draw_id_conflict"])
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_derived_field_tampering_is_rejected(self):
        record = capture_order.extract_state(state())
        record["balls"] = list(reversed(record["balls"]))
        self.assertIn("derived field balls differs from raw state", capture_order.record_integrity_errors(record))
        self.assertFalse(capture_order.valid_full_draw(record))

    def test_missing_security_fields_and_legacy_schema_are_rejected(self):
        for field in ("balls_raw_count", "balls_parse_errors", "locale_conflict"):
            with self.subTest(field=field):
                record = capture_order.extract_state(state())
                del record[field]
                self.assertFalse(capture_order.valid_ball_sequence(record))
        legacy = capture_order.extract_state(state())
        legacy["schema"] = 1
        self.assertFalse(capture_order.valid_ball_sequence(legacy))

    def test_results_scene_is_not_authoritative_order(self):
        record = capture_order.extract_state(state(scene="ResultsScene"))
        self.assertTrue(capture_order.valid_full_draw(record))
        self.assertFalse(capture_order.plausible_order(record))

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
            captured(10, tick=1),
            captured(12, tick=2),
        ]
        validation = validation_for(records, record=records[0], payload=rest(10))
        second = validation_for(records, record=records[1], payload=rest(12))
        validation["results"].extend(second["results"])
        validation["rest_payloads"].update(second["rest_payloads"])
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "id gaps"):
                capture_order.export_order(
                    records, Path(directory) / "ordered.txt", validation
                )

    def test_conflicting_sequences_are_reported(self):
        one = captured(10, list(range(1, 21)), tick=1)
        two = captured(10, list(range(20, 0, -1)), tick=2)
        _, conflicts = capture_order.select_draws([one, two])
        self.assertEqual(conflicts, [10])

    def test_rest_verification_accepts_only_matching_draw_scene(self):
        record = captured()
        parsed = capture_order.parse_rest_draw(rest())
        _, evidence = rest_evidence()
        report = capture_order.verify_record(record, parsed, evidence, 101)
        self.assertEqual(report["verdict"], "VERIFIED_ORDER")
        self.assertTrue(all(report["checks"].values()))

    def test_rest_verification_rejects_sorted_display(self):
        values = sorted(state()["meta"]["fr-ch"]["balls"])
        record = captured(balls=values, scene="ResultsScene")
        _, evidence = rest_evidence(payload=rest(balls=values))
        report = capture_order.verify_record(
            record, capture_order.parse_rest_draw(rest(balls=values)), evidence, 101
        )
        self.assertEqual(report["verdict"], "SORTED_NOT_ORDERED")

    def test_rest_verification_requires_observed_boost_and_bonus(self):
        payload = state()
        del payload["meta"]["fr-ch"]["boost"]
        del payload["meta"]["fr-ch"]["extra"]
        record = captured(raw_state=payload)
        parsed = capture_order.parse_rest_draw(rest(boost="bad", bonus="bad"))
        _, evidence = rest_evidence(payload=rest(boost="bad", bonus="bad"))
        report = capture_order.verify_record(record, parsed, evidence, 101)
        self.assertEqual(report["verdict"], "MISMATCH")
        self.assertFalse(report["checks"]["boost_match"])
        self.assertFalse(report["checks"]["bonus_match"])

    def test_rest_verification_rejects_out_of_domain_auxiliary_values(self):
        payload = state()
        payload["meta"]["fr-ch"]["boost"] = -1
        payload["meta"]["fr-ch"]["extra"] = -1
        record = captured(raw_state=payload)
        rest_payload = rest(boost="-1", bonus="-1")
        _, evidence = rest_evidence(payload=rest_payload)
        report = capture_order.verify_record(
            record, capture_order.parse_rest_draw(rest_payload), evidence, 101
        )
        self.assertEqual(report["verdict"], "MISMATCH")
        self.assertFalse(report["checks"]["boost_match"])
        self.assertFalse(report["checks"]["bonus_match"])

    def test_hub_envelope_requires_signalr_invocation_type(self):
        record = captured()
        message = json.loads(record["hub_message_raw"])
        del message["type"]
        wire = json.dumps(message, separators=(",", ":"))
        record["hub_message_raw"] = wire
        record["hub_message_sha256"] = hashlib.sha256(wire.encode()).hexdigest()
        record["hub_message_canonical_sha256"] = capture_order.canonical_sha256(message)
        self.assertIn(
            "raw state is not the first SendCurrentState argument",
            capture_order.capture_envelope_errors(record),
        )

    def test_jsonl_rejects_non_object_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.jsonl"
            path.write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not an object"):
                capture_order.read_jsonl(path)

    def test_path_alias_detection_handles_relative_and_hard_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "capture.jsonl"
            source.write_text("{}\n", encoding="utf-8")
            hardlink = root / "alias.jsonl"
            hardlink.hardlink_to(source)
            self.assertTrue(capture_order.paths_alias(source, root / "." / "capture.jsonl"))
            self.assertTrue(capture_order.paths_alias(source, hardlink))
            self.assertFalse(capture_order.paths_alias(source, root / "other.jsonl"))

    def test_export_requires_matching_validation_hash(self):
        record = captured()
        good_validation = validation_for([record])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ordered.txt"
            result = capture_order.export_order([record], output, good_validation)
            self.assertEqual(result["draws"], 1)
            self.assertEqual(output.read_text().strip(), " ".join(map(str, record["balls"])))
            bad_validation = {"results": []}
            with self.assertRaisesRegex(ValueError, "schema 2"):
                capture_order.export_order([record], output, bad_validation)

    def test_export_rejects_fabricated_or_modified_validation(self):
        record = captured()
        minimal = {
            "schema": 2,
            "capture_record_count": 1,
            "capture_records_canonical_sha256": capture_order.canonical_sha256([record]),
            "results": [{
                "draw_id": 101,
                "verdict": "VERIFIED_ORDER",
                "animation": {"raw_sha256": record["raw_sha256"]},
            }],
            "rest_payloads": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ordered.txt"
            with self.assertRaisesRegex(ValueError, "capture record hash|no exact REST body"):
                capture_order.export_order([record], output, minimal)
            modified = validation_for([record])
            modified["results"][0]["checks"]["boost_match"] = False
            with self.assertRaisesRegex(ValueError, "differs from recomputation"):
                capture_order.export_order([record], output, modified)

    def test_export_replays_conflict_and_first_seen_selection(self):
        order_a = [20, 1, 80] + list(range(2, 19))
        order_b = [1, 20, 80] + list(range(2, 19))
        one = captured(101, order_a, tick=1)
        conflicting = captured(101, order_b, tick=2)
        conflict_validation = validation_for([one, conflicting], record=one)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ordered.txt"
            with self.assertRaisesRegex(ValueError, "conflicting authoritative"):
                capture_order.export_order(
                    [one, conflicting], output, conflict_validation
                )

            later = captured(101, order_a, tick=2)
            late_validation = validation_for(
                [one, later], record=later, first_seen=later
            )
            with self.assertRaisesRegex(ValueError, "deterministic capture selection"):
                capture_order.export_order([one, later], output, late_validation)

    def test_validation_can_use_later_auxiliary_state_and_first_seen_time(self):
        early_payload = state()
        del early_payload["meta"]["fr-ch"]["boost"]
        del early_payload["meta"]["fr-ch"]["extra"]
        early = captured(raw_state=early_payload, tick=1)
        complete = captured(tick=2)
        payload = rest()
        _, evidence = rest_evidence(payload=payload)
        with mock.patch.object(
            capture_order,
            "fetch_rest_result",
            return_value=(capture_order.parse_rest_draw(payload), payload, evidence),
        ):
            validation = capture_order.validate_capture([early, complete], 101, 0, 0)
        result = validation["results"][0]
        self.assertEqual(result["verdict"], "VERIFIED_ORDER")
        self.assertEqual(result["animation"]["received_at"], complete["received_at"])
        self.assertEqual(result["animation"]["first_seen"]["received_at"], early["received_at"])

    def test_idless_capture_validates_and_exports_with_explicit_draw_id(self):
        payload = state()
        del payload["meta"]["fr-ch"]["id"]
        record = captured(raw_state=payload)
        self.assertIsNone(record["draw_id"])
        validation = validation_for([record], target_id=101)
        self.assertEqual(validation["results"][0]["verdict"], "VERIFIED_ORDER")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "ordered.txt"
            summary = capture_order.export_order([record], output, validation)
            manifest = json.loads(Path(summary["manifest"]).read_text())
        self.assertEqual(summary["draws"], 1)
        self.assertEqual(manifest["draw_id"], 101)
        self.assertIsNone(manifest["capture_draw_id"])
        self.assertEqual(manifest["draw_id_source"], "validation")


class FakeWebSocket:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def send(self, value):
        self.sent.append(value)

    async def recv(self):
        if not self.frames:
            raise AssertionError("capture requested an unexpected frame")
        item = self.frames.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class ConnectSequence:
    def __init__(self, *sockets):
        self.sockets = list(sockets)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if not self.sockets:
            raise AssertionError("capture requested an unexpected connection")
        return self.sockets.pop(0)


class LoggingConnector:
    def __init__(self, socket):
        self.socket = socket

    def __call__(self, url, *args, **kwargs):
        kwargs["logger"].debug("connecting to %s", url)
        return self.socket


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def monotonic_ns(self):
        return int(self.value * 1_000_000_000)


class AdvancingFakeWebSocket(FakeWebSocket):
    def __init__(self, frames, clock, advance=16.0):
        super().__init__(frames)
        self.clock = clock
        self.advance = advance

    async def recv(self):
        self.clock.value += self.advance
        return await super().recv()


class CaptureNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_handshake_and_state_in_one_frame_capture_once_without_token(self):
        hub_message = {
            "type": 1,
            "target": "SendCurrentState",
            "arguments": [state()],
        }
        wire_record = json.dumps(hub_message, ensure_ascii=False)
        socket = FakeWebSocket(["{}\x1e" + wire_record + "\x1e"])
        fake_module = types.SimpleNamespace(connect=lambda *args, **kwargs: socket)
        sentinel = "SENTINEL-NEGOTIATION-TOKEN"
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.dict(sys.modules, {"websockets": fake_module}), \
             mock.patch.object(
                 capture_order,
                 "negotiate",
                 new=mock.AsyncMock(return_value=f"wss://example.invalid/client/?access_token={sentinel}"),
             ):
            output = Path(directory) / "capture.jsonl"
            stats = await capture_order.capture(output, "fr-ch", 10, 1, 1, 101)
            saved = output.read_text(encoding="utf-8")
            record = json.loads(saved)

        self.assertEqual(stats, {"events": 1, "full_draws": 1})
        self.assertEqual(len(socket.sent), 2)
        self.assertIn('"protocol": "json"', socket.sent[0])
        self.assertIn('"target": "ConnectLoop"', socket.sent[1])
        self.assertEqual(record["hub_message_sha256"], capture_order.hashlib.sha256(wire_record.encode()).hexdigest())
        self.assertEqual(record["hub_message_raw"], wire_record)
        self.assertNotIn(sentinel, saved)

    async def test_access_token_is_suppressed_even_with_debug_logging(self):
        hub_message = {"type": 1, "target": "SendCurrentState", "arguments": [state()]}
        socket = FakeWebSocket(["{}\x1e" + json.dumps(hub_message) + "\x1e"])
        sentinel = "SENTINEL-DEBUG-TOKEN"
        fake_module = types.SimpleNamespace(connect=LoggingConnector(socket))
        stdout = io.StringIO()
        stderr = io.StringIO()
        root_logger = logging.getLogger()
        previous_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)
        try:
            with tempfile.TemporaryDirectory() as directory, \
                 mock.patch.dict(sys.modules, {"websockets": fake_module}), \
                 mock.patch.object(
                     capture_order, "negotiate",
                     new=mock.AsyncMock(
                         return_value=f"wss://example.invalid/client/?access_token={sentinel}"
                     ),
                 ), \
                 contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                output = Path(directory) / "capture.jsonl"
                await capture_order.capture(output, "fr-ch", 10, 1, 1, 101, verbose=True)
                combined = stdout.getvalue() + stderr.getvalue() + output.read_text()
        finally:
            root_logger.setLevel(previous_level)
        self.assertNotIn(sentinel, combined)

    async def test_timeout_before_first_state_reconnects(self):
        hub_message = {"type": 1, "target": "SendCurrentState", "arguments": [state()]}
        wire = json.dumps(hub_message) + "\x1e"
        for silent_frames in ([asyncio.TimeoutError()], ["{}\x1e", asyncio.TimeoutError()]):
            with self.subTest(silent_frames=len(silent_frames)):
                connector = ConnectSequence(
                    FakeWebSocket(silent_frames),
                    FakeWebSocket(["{}\x1e" + wire]),
                )
                fake_module = types.SimpleNamespace(connect=connector)
                with tempfile.TemporaryDirectory() as directory, \
                     mock.patch.dict(sys.modules, {"websockets": fake_module}), \
                     mock.patch.object(
                         capture_order, "negotiate",
                         new=mock.AsyncMock(return_value="wss://example.invalid/client/?access_token=x"),
                     ), \
                     mock.patch.object(capture_order.asyncio, "sleep", new=mock.AsyncMock()):
                    stats = await capture_order.capture(
                        Path(directory) / "capture.jsonl", "fr-ch", 10, 1, 1, 101
                    )
                self.assertEqual(stats["events"], 1)
                self.assertEqual(connector.calls, 2)

    async def test_close_reconnect_flag_and_signalr_ping_semantics(self):
        for close in ({"type": 7}, {"type": 7, "allowReconnect": False}):
            with self.subTest(close=close):
                socket = FakeWebSocket(["{}\x1e" + json.dumps(close) + "\x1e"])
                fake_module = types.SimpleNamespace(connect=lambda *args, **kwargs: socket)
                with tempfile.TemporaryDirectory() as directory, \
                     mock.patch.dict(sys.modules, {"websockets": fake_module}), \
                     mock.patch.object(
                         capture_order, "negotiate",
                         new=mock.AsyncMock(return_value="wss://example.invalid/client/?access_token=x"),
                     ):
                    stats = await capture_order.capture(
                        Path(directory) / "capture.jsonl", "fr-ch", 10, 1, 1, 101
                    )
                self.assertEqual(stats["events"], 0)
                self.assertEqual(len(socket.sent), 2)

        hub_message = {"type": 1, "target": "SendCurrentState", "arguments": [state()]}
        first = FakeWebSocket([
            "{}\x1e" + json.dumps({"type": 7, "allowReconnect": True}) + "\x1e"
        ])
        second = FakeWebSocket([
            "{}\x1e" + json.dumps({"type": 6}) + "\x1e" + json.dumps(hub_message) + "\x1e"
        ])
        connector = ConnectSequence(first, second)
        fake_module = types.SimpleNamespace(connect=connector)
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.dict(sys.modules, {"websockets": fake_module}), \
             mock.patch.object(
                 capture_order, "negotiate",
                 new=mock.AsyncMock(return_value="wss://example.invalid/client/?access_token=x"),
             ), \
             mock.patch.object(capture_order.asyncio, "sleep", new=mock.AsyncMock()):
            stats = await capture_order.capture(
                Path(directory) / "capture.jsonl", "fr-ch", 10, 1, 1, 101
            )
        self.assertEqual(stats["events"], 1)
        self.assertEqual(connector.calls, 2)
        self.assertEqual(len(second.sent), 2, "SignalR ping must not be echoed")

    async def test_hub_ping_is_sent_and_inbound_pings_cannot_mask_no_state(self):
        clock = FakeClock()
        ping = json.dumps({"type": 6}) + "\x1e"
        silent = AdvancingFakeWebSocket(["{}\x1e", ping, ping], clock)
        hub_message = {"type": 1, "target": "SendCurrentState", "arguments": [state()]}
        working = FakeWebSocket(["{}\x1e" + json.dumps(hub_message) + "\x1e"])
        connector = ConnectSequence(silent, working)
        fake_module = types.SimpleNamespace(connect=connector)
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.dict(sys.modules, {"websockets": fake_module}), \
             mock.patch.object(
                 capture_order, "negotiate",
                 new=mock.AsyncMock(return_value="wss://example.invalid/client/?access_token=x"),
             ), \
             mock.patch.object(capture_order.asyncio, "sleep", new=mock.AsyncMock()), \
             mock.patch.object(capture_order.time, "monotonic", side_effect=clock.monotonic), \
             mock.patch.object(capture_order.time, "monotonic_ns", side_effect=clock.monotonic_ns):
            stats = await capture_order.capture(
                Path(directory) / "capture.jsonl", "fr-ch", 0, 1, 1, 101
            )
        self.assertEqual(stats["events"], 1)
        self.assertEqual(connector.calls, 2)
        self.assertTrue(any('"type": 6' in message for message in silent.sent))


if __name__ == "__main__":
    unittest.main()
