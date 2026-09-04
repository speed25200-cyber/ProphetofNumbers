#!/usr/bin/env python3
"""Capture and audit the ordered Loto Express animation feed.

The REST API publishes sorted sets.  The public animation SignalR hub publishes
``meta[locale].balls`` and the web client renders that array sequentially before
sorting it in the reorder scene.  This tool records the raw states needed to test
whether that array is the missing draw order.

No negotiation token is logged or written to disk.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import codecs
import hashlib
import json
import logging
import math
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable


RS = "\x1e"
NEGOTIATE_URL = (
    "https://prod.jeux-webretail.loro.ch/api/animation/"
    "negotiate?negotiateVersion=1"
)
REST_DRAW_URL = "https://jeux.loro.ch/api/dbg/game/lotoexpress/draws/{draw_id}"
SOURCE = "Loto Express animationhub / SendCurrentState"
MAX_SIGNALR_BUFFER = 8 * 1024 * 1024
VALID_BOOSTS = frozenset((1, 2, 3, 4, 5, 10))
ORDER_SCOPE = "ANIMATION_SEQUENCE_ONLY"
AUXILIARY_STATE_SCENES = frozenset((
    "drawscene", "reorderscene", "extrascene", "bangoscene", "resultsscene",
    "didyouknowscene", "lotteryscene", "responsiblescene", "happywinnersscene",
))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def canonical_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        return int(parsed) if parsed.is_integer() else None
    return None


def first_parsed_int(*values: Any) -> int | None:
    for value in values:
        parsed = as_int(value)
        if parsed is not None:
            return parsed
    return None


def first_int(value: Any) -> int | None:
    if isinstance(value, list):
        if not value:
            return None
        return as_int(value[0])
    return as_int(value)


def post_json(url: str, token: str | None = None) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "ProphetofNumbers-order-audit/1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=b"", headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("negotiation response is not an object")
    return payload


def websocket_url(azure_url: str, access_token: str) -> str:
    parts = urllib.parse.urlsplit(azure_url)
    schemes = {"https": "wss", "http": "ws", "wss": "wss", "ws": "ws"}
    try:
        scheme = schemes[parts.scheme.lower()]
    except KeyError as exc:
        raise ValueError("unsupported SignalR URL scheme") from exc
    # Azure's existing query is routing material. Preserve it byte-for-byte; a
    # decode/re-encode round trip can invalidate the route even though the HTTP
    # upgrade itself still succeeds.
    segments = []
    for segment in parts.query.split("&") if parts.query else []:
        encoded_key = segment.partition("=")[0]
        if urllib.parse.unquote_plus(encoded_key).lower() != "access_token":
            segments.append(segment)
    segments.append("access_token=" + urllib.parse.quote(access_token, safe=""))
    return urllib.parse.urlunsplit(parts._replace(
        scheme=scheme,
        query="&".join(segments),
    ))


async def negotiate() -> str:
    first = await asyncio.to_thread(post_json, NEGOTIATE_URL)
    azure_url = first.get("url")
    access_token = first.get("accessToken")
    if not isinstance(azure_url, str) or not isinstance(access_token, str):
        raise ValueError("first negotiation response is incomplete")
    # Azure SignalR's serverless endpoint is already a ready-to-connect client URL.
    # A second /client/negotiate round-trip produces an id that this endpoint rejects.
    return websocket_url(azure_url, access_token)


class SignalRTextDecoder:
    """Decode record-separated SignalR JSON without dropping partial records."""

    def __init__(self) -> None:
        self.buffer = ""
        self.utf8_decoder = codecs.getincrementaldecoder("utf-8")()

    def feed_records(self, frame: str | bytes) -> list[tuple[str, dict[str, Any]]]:
        if isinstance(frame, bytes):
            frame = self.utf8_decoder.decode(frame, final=False)
        self.buffer += frame
        if len(self.buffer) > MAX_SIGNALR_BUFFER:
            raise ValueError("SignalR receive buffer exceeded safety limit")
        parts = self.buffer.split(RS)
        self.buffer = parts.pop()
        messages: list[tuple[str, dict[str, Any]]] = []
        for part in parts:
            if not part.strip():
                continue
            try:
                value = json.loads(part)
            except json.JSONDecodeError as exc:
                raise ValueError("invalid complete SignalR JSON record") from exc
            if not isinstance(value, dict):
                raise ValueError("SignalR JSON record is not an object")
            messages.append((part, value))
        return messages

    def feed(self, frame: str | bytes) -> list[dict[str, Any]]:
        return [value for _, value in self.feed_records(frame)]


def signalr_messages(frame: str | bytes) -> Iterable[dict[str, Any]]:
    """Compatibility helper for a complete frame; live capture uses a stateful decoder."""
    return SignalRTextDecoder().feed(frame)


def normalize_locale(value: Any) -> str:
    return str(value).replace("_", "-").lower()


def locale_payload(meta: Any, preferred: str) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(meta, dict):
        return None, {}
    entries = [(normalize_locale(key), value) for key, value in meta.items()]
    ordered_keys = list(dict.fromkeys(
        (normalize_locale(preferred), "fr-ch", "de-ch", "it-ch", *(key for key, _ in entries))
    ))
    # During language transitions one locale can contain an empty/partial array
    # while another already contains the complete draw.
    for key in ordered_keys:
        for normalized_key, value in entries:
            if normalized_key != key or not isinstance(value, dict):
                continue
            balls, count, errors = ball_sequence(value.get("balls"))
            if (
                count == 20 and errors == 0 and len(balls) == 20
                and len(set(balls)) == 20
                and all(type(ball) is int and 1 <= ball <= 80 for ball in balls)
            ):
                return key, value
    for key in ordered_keys:
        for normalized_key, value in entries:
            if normalized_key == key and isinstance(value, dict):
                return key, value
    return None, {}


def ball_value(value: Any) -> int | None:
    if isinstance(value, dict):
        parsed_values: list[int] = []
        for key in ("value", "number", "ball"):
            if key in value:
                parsed = as_int(value[key])
                if parsed is not None:
                    parsed_values.append(parsed)
        return parsed_values[0] if parsed_values and len(set(parsed_values)) == 1 else None
    return as_int(value)


def ball_sequence(raw: Any) -> tuple[list[int], int, int]:
    """Return parsed values, raw element count, and parse-error count."""
    if not isinstance(raw, list):
        return [], 0, 0
    values: list[int] = []
    errors = 0
    for item in raw:
        value = ball_value(item)
        if value is None:
            errors += 1
        else:
            values.append(value)
    return values, len(raw), errors


def locale_ball_variants(meta: Any) -> list[tuple[str, tuple[int, ...]]]:
    if not isinstance(meta, dict):
        return []
    variants: list[tuple[str, tuple[int, ...]]] = []
    for key, payload in meta.items():
        if not isinstance(payload, dict) or not isinstance(payload.get("balls"), list):
            continue
        values, count, errors = ball_sequence(payload["balls"])
        if count == 20 and errors == 0:
            variants.append((normalize_locale(key), tuple(values)))
    return variants


def extract_state(
    state: dict[str, Any],
    preferred_locale: str = "fr-ch",
    received_at: str | None = None,
    *,
    received_unix_ns: int | None = None,
    received_monotonic_ns: int | None = None,
    expected_draw_id: int | None = None,
    session_id: str | None = None,
    frame_index: int | None = None,
) -> dict[str, Any]:
    if received_unix_ns is None:
        received_unix_ns = iso8601_unix_ns(received_at)
    if received_unix_ns is None:
        received_unix_ns = time.time_ns()
    if received_at is None:
        received_at = datetime.fromtimestamp(
            received_unix_ns / 1_000_000_000, timezone.utc
        ).isoformat(timespec="milliseconds")
    locale, localized = locale_payload(state.get("meta"), preferred_locale)
    balls, raw_count, parse_errors = ball_sequence(localized.get("balls"))
    variants = locale_ball_variants(state.get("meta"))
    locale_conflict = len({sequence for _, sequence in variants}) > 1
    signalr_draw_id = first_parsed_int(
        localized.get("id"),
        localized.get("drawId"),
        localized.get("drawNumber"),
        state.get("id"),
        state.get("drawId"),
        state.get("drawNumber"),
    )
    draw_id_conflict = (
        signalr_draw_id is not None
        and expected_draw_id is not None
        and signalr_draw_id != expected_draw_id
    )
    draw_id = signalr_draw_id if signalr_draw_id is not None else expected_draw_id
    result = {
        "schema": 2,
        "received_at": received_at,
        "received_unix_ns": received_unix_ns,
        "received_monotonic_ns": (
            time.monotonic_ns() if received_monotonic_ns is None else received_monotonic_ns
        ),
        "session_id": session_id,
        "frame_index": frame_index,
        "source": SOURCE,
        "scene": state.get("scene"),
        "draw_id": draw_id,
        "draw_id_source": "signalr" if signalr_draw_id is not None else (
            "expected" if expected_draw_id is not None else None
        ),
        "draw_id_conflict": draw_id_conflict,
        "locale": locale,
        "locale_conflict": locale_conflict,
        "balls": balls,
        "balls_raw_count": raw_count,
        "balls_parse_errors": parse_errors,
        "boost": first_int(localized.get("boost")),
        "extra": first_int(localized.get("extra")),
        "next_draw_time": localized.get("nextDrawTime"),
        "duration": as_int(state.get("duration")),
        "start_time": as_int(state.get("startTime")),
        "end_time": as_int(state.get("endTime")),
        "progress": as_int(state.get("progress")),
        "state_canonical_sha256": canonical_sha256(state),
        # Backward-compatible name used by the first capture schema.
        "raw_sha256": canonical_sha256(state),
        "raw": state,
    }
    return result


def record_integrity_errors(record: dict[str, Any]) -> list[str]:
    raw = record.get("raw")
    if not isinstance(raw, dict):
        return ["raw state is missing"]
    errors: list[str] = []
    if record.get("schema") != 2:
        errors.append("unsupported record schema")
    if record.get("source") != SOURCE:
        errors.append("unexpected record source")
    if record.get("raw_sha256") != canonical_sha256(raw):
        errors.append("raw SHA-256 mismatch")
    if record.get("state_canonical_sha256") != canonical_sha256(raw):
        errors.append("canonical state SHA-256 mismatch")
    derived = extract_state(
        raw,
        str(record.get("locale") or "fr-ch"),
        received_at=str(record.get("received_at") or ""),
        expected_draw_id=(
            as_int(record.get("draw_id")) if record.get("draw_id_source") == "expected" else None
        ),
    )
    required_derived_fields = (
        "scene", "draw_id", "draw_id_source", "draw_id_conflict", "locale",
        "locale_conflict", "balls", "balls_raw_count", "balls_parse_errors", "boost",
        "extra", "duration", "start_time", "end_time", "progress",
    )
    for key in required_derived_fields:
        if key not in record:
            errors.append(f"required derived field {key} is missing")
        elif record.get(key) != derived.get(key):
            errors.append(f"derived field {key} differs from raw state")
    if "state_canonical_sha256" not in record:
        errors.append("canonical state SHA-256 is missing")
    received_at_ns = iso8601_unix_ns(record.get("received_at"))
    received_unix_ns = record.get("received_unix_ns")
    if received_at_ns is None:
        errors.append("received_at is not an ISO-8601 timestamp")
    if type(received_unix_ns) is not int or received_unix_ns <= 0:
        errors.append("received_unix_ns is not a positive integer")
    elif received_at_ns is not None and abs(received_at_ns - received_unix_ns) > 2_000_000:
        errors.append("received_at differs from received_unix_ns")
    if record.get("draw_id_conflict"):
        errors.append("SignalR draw id conflicts with expected draw id")
    if record.get("locale_conflict"):
        errors.append("localized ball sequences conflict")
    return errors


def capture_envelope_errors(record: dict[str, Any]) -> list[str]:
    """Validate the self-contained wire envelope used as order evidence."""
    errors = record_integrity_errors(record)
    if type(record.get("received_monotonic_ns")) is not int or record["received_monotonic_ns"] <= 0:
        errors.append("received_monotonic_ns is not a positive integer")
    session_id = record.get("session_id")
    try:
        uuid.UUID(hex=session_id) if isinstance(session_id, str) else None
    except (ValueError, AttributeError):
        session_id = None
    if not isinstance(session_id, str):
        errors.append("session_id is not a UUID")
    if type(record.get("frame_index")) is not int or record["frame_index"] < 1:
        errors.append("frame_index is not a positive integer")
    if type(record.get("message_index")) is not int or record["message_index"] < 0:
        errors.append("message_index is not a non-negative integer")
    wire_record = record.get("hub_message_raw")
    if not isinstance(wire_record, str):
        errors.append("raw hub message is missing")
        return errors
    if record.get("hub_message_sha256") != hashlib.sha256(wire_record.encode()).hexdigest():
        errors.append("raw hub message SHA-256 mismatch")
    try:
        message = json.loads(wire_record)
    except json.JSONDecodeError:
        errors.append("raw hub message is invalid JSON")
        return errors
    if not isinstance(message, dict):
        errors.append("raw hub message is not an object")
        return errors
    if record.get("hub_message_canonical_sha256") != canonical_sha256(message):
        errors.append("canonical hub message SHA-256 mismatch")
    arguments = message.get("arguments")
    if (
        type(message.get("type")) is not int
        or message.get("type") != 1
        or message.get("target") != "SendCurrentState"
        or not isinstance(arguments, list)
        or not arguments
        or arguments[0] != record.get("raw")
    ):
        errors.append("raw state is not the first SendCurrentState argument")
    return errors


def valid_auxiliary_values(boost: Any, bonus: Any, balls: list[int]) -> bool:
    return (
        type(boost) is int
        and boost in VALID_BOOSTS
        and type(bonus) is int
        and 1 <= bonus <= 80
        and bonus in balls
    )


def valid_ball_sequence(record: dict[str, Any]) -> bool:
    balls = record.get("balls")
    return (
        isinstance(balls, list)
        and len(balls) == 20
        and record.get("balls_raw_count", len(balls)) == 20
        and record.get("balls_parse_errors", 0) == 0
        and len(set(balls)) == 20
        and all(type(value) is int and 1 <= value <= 80 for value in balls)
        and not record_integrity_errors(record)
    )


def valid_full_draw(record: dict[str, Any]) -> bool:
    return type(record.get("draw_id")) is int and valid_ball_sequence(record)


def plausible_order(record: dict[str, Any]) -> bool:
    if not valid_ball_sequence(record):
        return False
    balls = record["balls"]
    scene = str(record.get("scene") or "").lower()
    return (
        balls != sorted(balls)
        and balls != sorted(balls, reverse=True)
        and scene == "drawscene"
    )


def parse_rest_draw(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("drawResult", payload.get("result", payload))
    if not isinstance(result, dict):
        result = {}
    matrix = result.get("matrix1", result)
    if not isinstance(matrix, dict):
        matrix = {}
    numbers, raw_count, parse_errors = ball_sequence(
        matrix.get("main", payload.get("primarySelection"))
    )
    return {
        "draw_id": as_int(payload.get("drawNumber")),
        "draw_date": payload.get("drawDate"),
        "wager_end_date": payload.get("wagerEndDate"),
        "phase": payload.get("phase"),
        "numbers": numbers,
        "numbers_raw_count": raw_count,
        "numbers_parse_errors": parse_errors,
        "boost": first_int(matrix.get("boost", payload.get("secondarySelection"))),
        "bonus": first_int(matrix.get("bonus", payload.get("tertiarySelection"))),
    }


def get_json_evidence(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    headers = {
        "Accept": "application/json",
        "Accept-Language": "fr-CH",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Origin": "https://jeux.loro.ch",
        "Referer": "https://jeux.loro.ch/games/lotoexpress/results",
        "User-Agent": "ProphetofNumbers-order-audit/1",
    }
    request = urllib.request.Request(url, headers=headers)
    request_wall_ns = time.time_ns()
    request_monotonic_ns = time.monotonic_ns()
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read()
        status = getattr(response, "status", None)
        http_date = response.headers.get("Date")
    response_monotonic_ns = time.monotonic_ns()
    response_wall_ns = time.time_ns()
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("REST response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("REST response is not an object")
    server_unix_ns = None
    if http_date:
        try:
            parsed = parsedate_to_datetime(http_date)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            server_unix_ns = int(parsed.timestamp() * 1_000_000_000)
        except (TypeError, ValueError, OverflowError):
            pass
    midpoint_wall_ns = (request_wall_ns + response_wall_ns) // 2
    return payload, {
        "url": url,
        "status": status,
        "http_date": http_date,
        "server_unix_ns": server_unix_ns,
        "request_wall_ns": request_wall_ns,
        "response_wall_ns": response_wall_ns,
        "request_monotonic_ns": request_monotonic_ns,
        "response_monotonic_ns": response_monotonic_ns,
        "rtt_ms": round((response_monotonic_ns - request_monotonic_ns) / 1_000_000, 3),
        "server_clock_offset_ms": (
            None if server_unix_ns is None
            else round((server_unix_ns - midpoint_wall_ns) / 1_000_000, 3)
        ),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "body_base64": base64.b64encode(body).decode("ascii"),
    }


def public_http_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Keep transport metadata in each result; store the exact body only once."""
    return {key: value for key, value in evidence.items() if key != "body_base64"}


def http_evidence_errors(evidence: dict[str, Any], draw_id: int) -> list[str]:
    errors: list[str] = []
    url = evidence.get("url")
    expected_url = urllib.parse.urlsplit(REST_DRAW_URL.format(draw_id=draw_id))
    actual_url = urllib.parse.urlsplit(url) if isinstance(url, str) else None
    if (
        actual_url is None
        or actual_url.scheme != expected_url.scheme
        or actual_url.hostname != expected_url.hostname
        or actual_url.path != expected_url.path
    ):
        errors.append("REST evidence URL does not identify the target draw")
    if evidence.get("status") != 200:
        errors.append("REST evidence does not contain HTTP 200")
    body_sha256 = evidence.get("body_sha256")
    if (
        not isinstance(body_sha256, str)
        or len(body_sha256) != 64
        or any(character not in "0123456789abcdef" for character in body_sha256.lower())
    ):
        errors.append("REST body SHA-256 is invalid")
    if type(evidence.get("body_bytes")) is not int or evidence["body_bytes"] <= 0:
        errors.append("REST body byte count is invalid")
    request_wall = evidence.get("request_wall_ns")
    response_wall = evidence.get("response_wall_ns")
    request_mono = evidence.get("request_monotonic_ns")
    response_mono = evidence.get("response_monotonic_ns")
    if not all(type(value) is int and value > 0 for value in (request_wall, response_wall)):
        errors.append("REST wall-clock bounds are invalid")
    elif request_wall > response_wall:
        errors.append("REST wall-clock bounds are reversed")
    if not all(type(value) is int and value > 0 for value in (request_mono, response_mono)):
        errors.append("REST monotonic bounds are invalid")
    elif request_mono > response_mono:
        errors.append("REST monotonic bounds are reversed")
    rtt_ms = evidence.get("rtt_ms")
    if (
        not isinstance(rtt_ms, (int, float))
        or isinstance(rtt_ms, bool)
        or not math.isfinite(float(rtt_ms))
        or rtt_ms < 0
    ):
        errors.append("REST round-trip time is invalid")
    elif type(request_mono) is int and type(response_mono) is int:
        measured = round((response_mono - request_mono) / 1_000_000, 3)
        if abs(float(rtt_ms) - measured) > 0.001:
            errors.append("REST round-trip time differs from monotonic bounds")
    http_date = evidence.get("http_date")
    server_unix_ns = evidence.get("server_unix_ns")
    clock_offset_ms = evidence.get("server_clock_offset_ms")
    if not isinstance(http_date, str) or type(server_unix_ns) is not int:
        errors.append("REST HTTP Date evidence is missing")
    elif type(request_wall) is int and type(response_wall) is int:
        try:
            parsed_date = parsedate_to_datetime(http_date)
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
            parsed_server_ns = int(parsed_date.timestamp() * 1_000_000_000)
        except (TypeError, ValueError, OverflowError):
            errors.append("REST HTTP Date evidence is invalid")
        else:
            if server_unix_ns != parsed_server_ns:
                errors.append("REST server time differs from HTTP Date")
            midpoint_wall_ns = (request_wall + response_wall) // 2
            expected_offset_ms = round(
                (parsed_server_ns - midpoint_wall_ns) / 1_000_000, 3
            )
            if (
                isinstance(clock_offset_ms, (int, float))
                and not isinstance(clock_offset_ms, bool)
                and abs(float(clock_offset_ms) - expected_offset_ms) > 0.001
            ):
                errors.append("REST server clock offset differs from HTTP Date")
    if (
        not isinstance(clock_offset_ms, (int, float))
        or isinstance(clock_offset_ms, bool)
        or not math.isfinite(float(clock_offset_ms))
    ):
        errors.append("REST server clock offset is missing")
    return errors


def rest_has_complete_result(rest: dict[str, Any]) -> bool:
    numbers = rest.get("numbers")
    return (
        type(rest.get("draw_id")) is int
        and isinstance(numbers, list)
        and rest.get("numbers_raw_count") == 20
        and rest.get("numbers_parse_errors") == 0
        and len(numbers) == 20
        and len(set(numbers)) == 20
        and all(type(value) is int and 1 <= value <= 80 for value in numbers)
    )


def fetch_rest_result(
    draw_id: int, retry_seconds: float = 120, retry_interval: float = 2
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + max(0, retry_seconds)
    last_error: Exception | None = None
    while True:
        cache_bust = int(time.time() * 1000)
        url = REST_DRAW_URL.format(draw_id=draw_id) + f"?_={cache_bust}&l=fr-CH"
        try:
            payload, evidence = get_json_evidence(url)
            parsed = parse_rest_draw(payload)
            if parsed.get("draw_id") != draw_id:
                raise ValueError("REST response draw id does not match request")
            if rest_has_complete_result(parsed):
                return parsed, payload, evidence
            last_error = ValueError(
                f"REST draw {draw_id} has no complete result (phase={parsed.get('phase')})"
            )
        except (OSError, ValueError) as exc:
            last_error = exc
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            assert last_error is not None
            raise ValueError(str(last_error)) from last_error
        time.sleep(min(max(0.1, retry_interval), remaining))


def iso8601_unix_ns(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


def verify_record(
    record: dict[str, Any],
    rest: dict[str, Any],
    evidence: dict[str, Any],
    target_draw_id: int,
    first_seen_record: dict[str, Any] | None = None,
    auxiliary_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    first_seen_record = first_seen_record or record
    auxiliary_record = auxiliary_record or record
    balls = (
        first_seen_record.get("balls")
        if isinstance(first_seen_record.get("balls"), list)
        else []
    )
    numbers = rest.get("numbers") if isinstance(rest.get("numbers"), list) else []
    integrity_errors = capture_envelope_errors(record)
    first_seen_errors = (
        [] if first_seen_record is record else capture_envelope_errors(first_seen_record)
    )
    integrity_errors.extend(f"first seen: {error}" for error in first_seen_errors)
    auxiliary_errors = (
        [] if auxiliary_record is record else capture_envelope_errors(auxiliary_record)
    )
    integrity_errors.extend(f"auxiliary: {error}" for error in auxiliary_errors)
    http_errors = http_evidence_errors(evidence, target_draw_id)
    auxiliary_bound = auxiliary_state_is_bound(
        first_seen_record, auxiliary_record, target_draw_id
    )
    checks = {
        "record_integrity": not integrity_errors,
        "structured_http_evidence": not http_errors,
        "draw_id_match": rest.get("draw_id") == target_draw_id and (
            record.get("draw_id") in (None, target_draw_id)
            and first_seen_record.get("draw_id") in (None, target_draw_id)
        ),
        "twenty_unique_animation_balls": (
            valid_ball_sequence(record)
            and valid_ball_sequence(first_seen_record)
            and record.get("balls") == balls
        ),
        "authoritative_draw_scene": (
            str(record.get("scene") or "").lower() == "drawscene"
            and str(first_seen_record.get("scene") or "").lower() == "drawscene"
        ),
        "animation_order_not_sorted": balls != sorted(balls),
        "animation_order_not_reverse_sorted": balls != sorted(balls, reverse=True),
        "complete_rest_result": rest_has_complete_result(rest),
        "sorted_set_match": sorted(balls) == sorted(numbers),
        "auxiliary_state_bound": auxiliary_bound,
        "boost_match": (
            auxiliary_bound
            and valid_auxiliary_values(
                auxiliary_record.get("boost"), auxiliary_record.get("extra"), balls
            )
            and type(rest.get("boost")) is int
            and rest.get("boost") in VALID_BOOSTS
            and auxiliary_record.get("boost") == rest.get("boost")
        ),
        "bonus_match": (
            auxiliary_bound
            and valid_auxiliary_values(
                auxiliary_record.get("boost"), auxiliary_record.get("extra"), balls
            )
            and type(rest.get("bonus")) is int
            and rest.get("bonus") in numbers
            and auxiliary_record.get("extra") == rest.get("bonus")
        ),
    }
    wager_end_ns = iso8601_unix_ns(rest.get("wager_end_date"))
    received_ns = as_int(first_seen_record.get("received_unix_ns"))
    delta_ms = None
    if wager_end_ns is not None and received_ns is not None:
        delta_ms = round((received_ns - wager_end_ns) / 1_000_000, 3)
    clock_offset_ms = evidence.get("server_clock_offset_ms")
    adjusted_delta_ms = None
    timing_interval_ms = None
    timing_verdict = "INCONCLUSIVE"
    if delta_ms is not None and isinstance(clock_offset_ms, (int, float)):
        adjusted_delta_ms = round(delta_ms + clock_offset_ms, 3)
        uncertainty_ms = 1000.0 + float(evidence.get("rtt_ms") or 0) / 2
        timing_interval_ms = [
            round(adjusted_delta_ms - uncertainty_ms, 3),
            round(adjusted_delta_ms + uncertainty_ms, 3),
        ]
        if timing_interval_ms[1] < 0:
            timing_verdict = "BEFORE_WAGER_END"
        elif timing_interval_ms[0] > 0:
            timing_verdict = "AFTER_WAGER_END"
    if all(checks.values()):
        verdict = "VERIFIED_ORDER"
    elif (
        checks["complete_rest_result"]
        and checks["sorted_set_match"]
        and not checks["animation_order_not_sorted"]
    ):
        verdict = "SORTED_NOT_ORDERED"
    else:
        verdict = "MISMATCH"
    result = {
        "draw_id": target_draw_id,
        "verdict": verdict,
        "order_scope": ORDER_SCOPE,
        "checks": checks,
        "integrity_errors": integrity_errors,
        "http_evidence_errors": http_errors,
        "animation": {
            key: record.get(key) for key in (
                "received_at", "received_unix_ns", "received_monotonic_ns", "session_id",
                "frame_index", "message_index", "scene", "locale", "balls", "boost", "extra",
                "raw_sha256", "state_canonical_sha256", "hub_message_sha256",
                "hub_message_canonical_sha256",
            )
        },
        "rest": {**rest, "http": public_http_evidence(evidence)},
        "timing": {
            "local_clock_delta_ms": delta_ms,
            "server_clock_adjusted_delta_ms": adjusted_delta_ms,
            "conservative_interval_ms": timing_interval_ms,
            "verdict": timing_verdict,
        },
    }
    result["animation"]["capture_record_sha256"] = canonical_sha256(record)
    result["animation"]["first_seen"] = {
        key: first_seen_record.get(key) for key in (
            "received_at", "received_unix_ns", "received_monotonic_ns", "session_id",
            "frame_index", "message_index", "scene", "raw_sha256",
            "hub_message_sha256",
        )
    }
    result["animation"]["first_seen"]["capture_record_sha256"] = canonical_sha256(
        first_seen_record
    )
    result["animation"]["auxiliary"] = {
        key: auxiliary_record.get(key) for key in (
            "received_at", "received_unix_ns", "received_monotonic_ns", "session_id",
            "frame_index", "message_index", "scene", "balls", "boost", "extra",
            "raw_sha256", "hub_message_sha256",
        )
    }
    result["animation"]["auxiliary"]["capture_record_sha256"] = canonical_sha256(
        auxiliary_record
    )
    return result


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def observation_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        as_int(record.get("received_unix_ns")) or sys.maxsize,
        as_int(record.get("received_monotonic_ns")) or sys.maxsize,
        str(record.get("session_id") or ""),
        as_int(record.get("frame_index")) or 0,
        as_int(record.get("message_index")) or 0,
    )


def auxiliary_state_is_bound(
    first_seen: dict[str, Any], auxiliary: dict[str, Any], target_id: int | None
) -> bool:
    """Bind late boost/bonus to one authoritative animation order."""
    return (
        valid_ball_sequence(first_seen)
        and valid_ball_sequence(auxiliary)
        and auxiliary.get("balls") == first_seen.get("balls")
        and first_seen.get("draw_id") in (None, target_id)
        and auxiliary.get("draw_id") in (None, target_id)
        and isinstance(first_seen.get("session_id"), str)
        and auxiliary.get("session_id") == first_seen.get("session_id")
        and observation_key(auxiliary) >= observation_key(first_seen)
        and str(auxiliary.get("scene") or "").lower() in AUXILIARY_STATE_SCENES
        and not capture_envelope_errors(auxiliary)
    )


def validation_records_for_draw(
    records: Iterable[dict[str, Any]], target_id: int, allow_idless: bool
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    matching = [
        record for record in records
        if valid_ball_sequence(record)
        and (
            record.get("draw_id") == target_id
            or (allow_idless and record.get("draw_id") is None)
        )
    ]
    if not matching:
        raise ValueError(f"no animation state matches draw id {target_id}")
    authoritative_variants = {
        tuple(record["balls"]) for record in matching if plausible_order(record)
    }
    if len(authoritative_variants) > 1:
        raise ValueError(f"conflicting authoritative sequences for draw id {target_id}")
    if not authoritative_variants:
        record = min(matching, key=observation_key)
        return record, record, record
    sequence = next(iter(authoritative_variants))
    ordered = sorted(
        (
            record for record in matching
            if plausible_order(record) and tuple(record["balls"]) == sequence
        ),
        key=observation_key,
    )
    first_seen = ordered[0]
    auxiliary_candidates = [
        record for record in matching
        if auxiliary_state_is_bound(first_seen, record, target_id)
        and valid_auxiliary_values(
            record.get("boost"), record.get("extra"), record["balls"]
        )
    ]
    auxiliary_variants = {
        (record.get("boost"), record.get("extra"))
        for record in auxiliary_candidates
    }
    if len(auxiliary_variants) > 1:
        raise ValueError(f"conflicting auxiliary values for draw id {target_id}")
    auxiliary = (
        min(auxiliary_candidates, key=observation_key)
        if auxiliary_candidates else first_seen
    )
    return first_seen, first_seen, auxiliary


def validate_capture(
    records: list[dict[str, Any]],
    draw_id_override: int | None,
    retry_seconds: float,
    retry_interval: float,
) -> dict[str, Any]:
    candidates = [record for record in records if valid_ball_sequence(record)]
    if not candidates:
        raise ValueError("capture contains no intact 20-ball animation state")
    if draw_id_override is not None:
        candidates = [
            record for record in candidates
            if record.get("draw_id") in (None, draw_id_override)
        ]
        if not candidates:
            raise ValueError("no animation state matches the requested draw id")
        target_ids = [draw_id_override]
    else:
        target_ids = sorted({record["draw_id"] for record in candidates
                             if type(record.get("draw_id")) is int})
        if not target_ids:
            raise ValueError("animation state has no id; pass --draw-id for REST correlation")
    results: list[dict[str, Any]] = []
    rest_payloads: dict[str, Any] = {}
    for target_id in target_ids:
        record, first_seen, auxiliary = validation_records_for_draw(
            candidates, target_id, draw_id_override is not None
        )
        rest, _payload, evidence = fetch_rest_result(
            target_id, retry_seconds, retry_interval
        )
        results.append(verify_record(
            record, rest, evidence, target_id, first_seen, auxiliary
        ))
        rest_payloads[str(target_id)] = {
            "body_sha256": evidence["body_sha256"],
            "body_bytes": evidence["body_bytes"],
            "encoding": "base64",
            "body_base64": evidence["body_base64"],
        }
    return {
        "schema": 2,
        "validated_at": utc_now(),
        "draw_id_override": draw_id_override,
        "capture_record_count": len(records),
        "capture_records_canonical_sha256": canonical_sha256(records),
        "results": results,
        "rest_payloads": rest_payloads,
    }


def select_draws(
    records: Iterable[dict[str, Any]], *, require_authoritative_order: bool = False
) -> tuple[list[dict[str, Any]], list[int]]:
    selected: dict[int, dict[str, Any]] = {}
    variants: dict[int, set[tuple[int, ...]]] = {}
    for record in records:
        if not valid_full_draw(record):
            continue
        if require_authoritative_order and not plausible_order(record):
            continue
        draw_id = record["draw_id"]
        sequence = tuple(record["balls"])
        variants.setdefault(draw_id, set()).add(sequence)
        current = selected.get(draw_id)
        if current is None or str(record.get("received_at", "")) < str(current.get("received_at", "")):
            selected[draw_id] = record
    conflicts = sorted(draw_id for draw_id, values in variants.items() if len(values) > 1)
    return [selected[key] for key in sorted(selected)], conflicts


def analyze(records: list[dict[str, Any]]) -> dict[str, Any]:
    draws, conflicts = select_draws(records)
    authoritative_draws, authoritative_conflicts = select_draws(
        records, require_authoritative_order=True
    )
    ranks = [0] * 20
    ascending = 0
    descending = 0
    for record in draws:
        balls = record["balls"]
        ordered = sorted(balls)
        ascending += balls == ordered
        descending += balls == list(reversed(ordered))
        ranks[ordered.index(balls[0])] += 1
    gaps = [
        [draws[i - 1]["draw_id"], draws[i]["draw_id"]]
        for i in range(1, len(draws))
        if draws[i]["draw_id"] != draws[i - 1]["draw_id"] + 1
    ]
    chi2 = None
    if draws:
        expected = len(draws) / 20
        chi2 = sum((count - expected) ** 2 / expected for count in ranks)
    return {
        "events": len(records),
        "scenes": dict(sorted(Counter(str(r.get("scene")) for r in records).items())),
        "full_draws": len(draws),
        "authoritative_order_draws": len(authoritative_draws),
        "first_draw_id": draws[0]["draw_id"] if draws else None,
        "last_draw_id": draws[-1]["draw_id"] if draws else None,
        "ascending_sequences": ascending,
        "descending_sequences": descending,
        "conflicting_draw_ids": conflicts,
        "authoritative_conflicting_draw_ids": authoritative_conflicts,
        "pending_id_sequences": sum(
            valid_ball_sequence(record) and type(record.get("draw_id")) is not int
            for record in records
        ),
        "integrity_failures": sum(bool(capture_envelope_errors(record)) for record in records),
        "id_gaps": gaps,
        "first_ball_rank_histogram": ranks,
        "first_ball_rank_chi2_df19": None if chi2 is None else round(chi2, 6),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: JSON record is not an object")
            records.append(value)
    return records


def validation_index(
    validation: dict[str, Any], records: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Recompute every saved validation from the captured wire and REST bytes."""
    if validation.get("schema") != 2:
        raise ValueError("validation report does not use schema 2")
    if validation.get("capture_record_count") != len(records):
        raise ValueError("validation report capture count differs from input")
    if validation.get("capture_records_canonical_sha256") != canonical_sha256(records):
        raise ValueError("validation report is not bound to this exact capture")
    results = validation.get("results")
    if not isinstance(results, list):
        raise ValueError("validation report has no results array")
    rest_payloads = validation.get("rest_payloads")
    if not isinstance(rest_payloads, dict):
        raise ValueError("validation report has no exact REST payloads")
    draw_id_override = validation.get("draw_id_override")
    if draw_id_override is not None and type(draw_id_override) is not int:
        raise ValueError("validation report draw-id override is malformed")
    records_by_hash = {canonical_sha256(record): record for record in records}
    index: dict[int, dict[str, Any]] = {}
    seen_ids: set[int] = set()
    seen_first_records: set[str] = set()
    for saved_result in results:
        if not isinstance(saved_result, dict) or type(saved_result.get("draw_id")) is not int:
            raise ValueError("validation result is malformed")
        draw_id = saved_result["draw_id"]
        if draw_id in seen_ids:
            raise ValueError(f"duplicate validation result for draw id {draw_id}")
        seen_ids.add(draw_id)
        if draw_id_override is not None and draw_id != draw_id_override:
            raise ValueError("validation result differs from its explicit draw-id scope")
        animation = saved_result.get("animation")
        if not isinstance(animation, dict):
            raise ValueError(f"validation result {draw_id} has no animation evidence")
        record_hash = animation.get("capture_record_sha256")
        if not isinstance(record_hash, str):
            raise ValueError(f"validation result {draw_id} has no capture record hash")
        record = records_by_hash.get(record_hash)
        first_seen_summary = animation.get("first_seen")
        first_seen_hash = (
            first_seen_summary.get("capture_record_sha256")
            if isinstance(first_seen_summary, dict) else None
        )
        if not isinstance(first_seen_hash, str):
            raise ValueError(f"validation result {draw_id} has no first-seen record hash")
        first_seen = records_by_hash.get(first_seen_hash)
        if record is None or first_seen is None:
            raise ValueError(f"validation result {draw_id} references a missing capture record")
        expected_record, expected_first_seen, expected_auxiliary = validation_records_for_draw(
            records, draw_id, draw_id_override == draw_id
        )
        auxiliary_summary = animation.get("auxiliary")
        auxiliary_hash = (
            auxiliary_summary.get("capture_record_sha256")
            if isinstance(auxiliary_summary, dict) else None
        )
        auxiliary = records_by_hash.get(auxiliary_hash) if isinstance(auxiliary_hash, str) else None
        if (
            record_hash != canonical_sha256(expected_record)
            or first_seen_hash != canonical_sha256(expected_first_seen)
            or auxiliary is None
            or auxiliary_hash != canonical_sha256(expected_auxiliary)
        ):
            raise ValueError(
                f"validation result {draw_id} does not use the deterministic capture selection"
            )
        if first_seen_hash in seen_first_records:
            raise ValueError("one captured state cannot validate multiple draw ids")
        seen_first_records.add(first_seen_hash)
        stored_body = rest_payloads.get(str(draw_id))
        if not isinstance(stored_body, dict) or stored_body.get("encoding") != "base64":
            raise ValueError(f"validation result {draw_id} has no exact REST body")
        encoded = stored_body.get("body_base64")
        if not isinstance(encoded, str):
            raise ValueError(f"validation result {draw_id} REST body is malformed")
        try:
            body = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"validation result {draw_id} REST body is invalid base64") from exc
        body_sha256 = hashlib.sha256(body).hexdigest()
        if (
            stored_body.get("body_sha256") != body_sha256
            or stored_body.get("body_bytes") != len(body)
        ):
            raise ValueError(f"validation result {draw_id} REST body hash/length mismatch")
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"validation result {draw_id} REST body is not JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"validation result {draw_id} REST body is not an object")
        parsed_rest = parse_rest_draw(payload)
        saved_rest = saved_result.get("rest")
        evidence = saved_rest.get("http") if isinstance(saved_rest, dict) else None
        if not isinstance(evidence, dict):
            raise ValueError(f"validation result {draw_id} has no HTTP evidence")
        if (
            evidence.get("body_sha256") != body_sha256
            or evidence.get("body_bytes") != len(body)
        ):
            raise ValueError(f"validation result {draw_id} REST evidence is not bound to its body")
        recomputed = verify_record(
            record, parsed_rest, evidence, draw_id, first_seen, auxiliary
        )
        if saved_result != recomputed:
            raise ValueError(f"validation result {draw_id} differs from recomputation")
        if recomputed.get("verdict") != "VERIFIED_ORDER":
            continue
        balls = first_seen.get("balls")
        if not isinstance(balls, list):
            raise ValueError(f"validation result {draw_id} has no ordered balls")
        index[draw_id] = first_seen
    return index


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def paths_alias(left: Path, right: Path) -> bool:
    """Detect lexical, symlink, and hard-link aliases without requiring existence."""
    try:
        if left.exists() and right.exists() and os.path.samefile(left, right):
            return True
    except OSError:
        pass
    try:
        return left.resolve(strict=False) == right.resolve(strict=False)
    except OSError:
        return os.path.abspath(left) == os.path.abspath(right)


def export_order(
    records: list[dict[str, Any]], output: Path, validation: dict[str, Any]
) -> dict[str, Any]:
    verified = validation_index(validation, records)
    draws: list[dict[str, Any]] = []
    for draw_id, captured_record in sorted(verified.items()):
        record = dict(captured_record)
        record["capture_draw_id"] = captured_record.get("draw_id")
        record["draw_id"] = draw_id
        record["draw_id_source"] = (
            captured_record.get("draw_id_source")
            if captured_record.get("draw_id") == draw_id
            else "validation"
        )
        record["order_scope"] = ORDER_SCOPE
        draws.append(record)
    if not draws:
        raise ValueError("capture contains no VERIFIED_ORDER result")
    gaps = [
        (draws[i - 1]["draw_id"], draws[i]["draw_id"])
        for i in range(1, len(draws))
        if draws[i]["draw_id"] != draws[i - 1]["draw_id"] + 1
    ]
    if gaps:
        raise ValueError(f"capture has id gaps; refusing a false-contiguous export: {gaps}")
    write_text_atomic(output, "".join(
        " ".join(map(str, record["balls"])) + "\n" for record in draws
    ))
    manifest = output.with_suffix(output.suffix + ".manifest.jsonl")
    manifest_rows = []
    for record in draws:
        kept = {key: record.get(key) for key in (
            "draw_id", "received_at", "received_unix_ns", "received_monotonic_ns",
            "session_id", "frame_index", "scene", "locale", "raw_sha256", "balls",
            "boost", "extra", "capture_draw_id", "draw_id_source",
            "order_scope",
        )}
        manifest_rows.append(json.dumps(kept, ensure_ascii=False, sort_keys=True) + "\n")
    write_text_atomic(manifest, "".join(manifest_rows))
    return {
        "draws": len(draws),
        "gaps": gaps,
        "order_scope": ORDER_SCOPE,
        "output": str(output),
        "manifest": str(manifest),
    }


def private_websocket_logger() -> logging.Logger:
    logger = logging.getLogger("prophetofnumbers.signalr.private")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    logger.setLevel(logging.CRITICAL + 1)
    return logger


async def capture(
    output: Path,
    locale: str,
    duration: float,
    max_events: int,
    max_draws: int,
    expected_draw_id: int | None,
    verbose: bool = False,
) -> dict[str, int]:
    import websockets

    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = math.inf if duration <= 0 else time.monotonic() + duration
    written = 0
    complete_draws: set[int | tuple[int, ...]] = set()
    authoritative_orders: dict[
        int | tuple[int, ...], dict[str, Any] | None
    ] = {}
    invocation = 0
    delay = 1.0

    def finished() -> bool:
        return (
            (max_events > 0 and written >= max_events)
            or (max_draws > 0 and len(complete_draws) >= max_draws)
        )

    with output.open("a", encoding="utf-8", buffering=1) as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            pass
        except BlockingIOError as exc:
            raise ValueError("another collector is already writing this capture") from exc
        while time.monotonic() < deadline and not finished():
            try:
                url = await negotiate()
                session_id = uuid.uuid4().hex
                decoder = SignalRTextDecoder()
                frame_index = 0
                handshake_ready = False
                connect_invoked = False
                connect_invoked_at: float | None = None
                last_state_monotonic: float | None = None
                last_hub_ping = time.monotonic()
                async with websockets.connect(
                    url,
                    open_timeout=25,
                    close_timeout=5,
                    ping_interval=15,
                    ping_timeout=20,
                    logger=private_websocket_logger(),
                ) as socket:
                    if verbose:
                        print(f"SignalR session {session_id[:12]} connected", file=sys.stderr, flush=True)
                    await socket.send(json.dumps({"protocol": "json", "version": 1}) + RS)
                    while time.monotonic() < deadline and not finished():
                        now = time.monotonic()
                        state_deadline = None
                        if connect_invoked_at is not None:
                            state_deadline = (
                                connect_invoked_at + 30
                                if last_state_monotonic is None
                                else last_state_monotonic + 120
                            )
                            if now >= state_deadline:
                                raise ConnectionError(
                                    "SignalR state stream missed its liveness deadline"
                                )
                        if handshake_ready and now - last_hub_ping >= 15:
                            await socket.send(json.dumps({"type": 6}) + RS)
                            last_hub_ping = now
                        waits = [30.0]
                        if handshake_ready:
                            waits.append(max(0.1, 15 - (now - last_hub_ping)))
                        if deadline != math.inf:
                            waits.append(max(0.1, deadline - now))
                        if state_deadline is not None:
                            waits.append(max(0.1, state_deadline - now))
                        timeout = min(waits)
                        try:
                            frame = await asyncio.wait_for(socket.recv(), timeout=timeout)
                        except asyncio.TimeoutError:
                            now = time.monotonic()
                            if now >= deadline:
                                break
                            if not handshake_ready:
                                raise ConnectionError(
                                    "SignalR timed out before the handshake"
                                )
                            if state_deadline is not None and now >= state_deadline:
                                raise ConnectionError(
                                    "SignalR state stream missed its liveness deadline"
                                )
                            continue
                        received_unix_ns = time.time_ns()
                        received_monotonic_ns = time.monotonic_ns()
                        received_at = datetime.fromtimestamp(
                            received_unix_ns / 1_000_000_000, timezone.utc
                        ).isoformat(timespec="milliseconds")
                        frame_index += 1
                        for message_index, (wire_record, message) in enumerate(decoder.feed_records(frame)):
                            if verbose:
                                print(
                                    f"SignalR message type={message.get('type')} "
                                    f"target={message.get('target')}",
                                    file=sys.stderr,
                                    flush=True,
                                )
                            if not handshake_ready:
                                if message.get("error"):
                                    raise ConnectionError("SignalR handshake rejected")
                                if message:
                                    raise ConnectionError("unexpected message before SignalR handshake")
                                handshake_ready = True
                            if handshake_ready and not connect_invoked:
                                invocation += 1
                                await socket.send(json.dumps({
                                    "type": 1,
                                    "invocationId": str(invocation),
                                    "target": "ConnectLoop",
                                    "arguments": ["ONLINE"],
                                }) + RS)
                                connect_invoked = True
                                connect_invoked_at = time.monotonic()
                                if verbose:
                                    print("SignalR ConnectLoop invoked", file=sys.stderr, flush=True)
                                continue
                            message_type = message.get("type")
                            if message_type == 3 and message.get("error"):
                                raise ConnectionError("ConnectLoop invocation failed")
                            if message_type == 7:
                                if message.get("allowReconnect") is True:
                                    raise ConnectionError("SignalR requested reconnect")
                                return {"events": written, "full_draws": len(complete_draws)}
                            if message_type == 6:
                                continue
                            if message_type == 1 and message.get("target") == "SendCurrentState":
                                if finished():
                                    break
                                arguments = message.get("arguments")
                                if not isinstance(arguments, list) or not arguments or not isinstance(arguments[0], dict):
                                    raise ValueError("SendCurrentState has no object state argument")
                                record = extract_state(
                                    arguments[0],
                                    locale,
                                    received_at,
                                    received_unix_ns=received_unix_ns,
                                    received_monotonic_ns=received_monotonic_ns,
                                    expected_draw_id=expected_draw_id,
                                    session_id=session_id,
                                    frame_index=frame_index,
                                )
                                record["message_index"] = message_index
                                record["hub_message_raw"] = wire_record
                                record["hub_message_sha256"] = hashlib.sha256(wire_record.encode()).hexdigest()
                                record["hub_message_canonical_sha256"] = canonical_sha256(message)
                                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                                handle.flush()
                                os.fsync(handle.fileno())
                                written += 1
                                last_state_monotonic = time.monotonic()
                                key: int | tuple[int, ...]
                                key = (
                                    record["draw_id"]
                                    if type(record.get("draw_id")) is int
                                    else tuple(record["balls"])
                                )
                                if plausible_order(record):
                                    previous = authoritative_orders.get(key)
                                    if previous is None and key not in authoritative_orders:
                                        authoritative_orders[key] = record
                                    elif (
                                        previous is not None
                                        and previous.get("balls") != record.get("balls")
                                    ):
                                        authoritative_orders[key] = None
                                authoritative = authoritative_orders.get(key)
                                if (
                                    authoritative is not None
                                    and auxiliary_state_is_bound(
                                        authoritative,
                                        record,
                                        authoritative.get("draw_id")
                                        if type(authoritative.get("draw_id")) is int
                                        else expected_draw_id,
                                    )
                                    and valid_auxiliary_values(
                                        record.get("boost"), record.get("extra"), record["balls"]
                                    )
                                ):
                                    complete_draws.add(key)
                                delay = 1.0
                                print(
                                    f"{record['received_at']} scene={record['scene']} "
                                    f"id={record['draw_id']} balls={len(record['balls'])} "
                                    f"sha256={record['raw_sha256'][:12]}",
                                    flush=True,
                                )
            except KeyboardInterrupt:
                break
            except Exception as exc:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
                suffix = "" if status is None else f" HTTP {status}"
                print(f"capture reconnect after {type(exc).__name__}{suffix}", file=sys.stderr, flush=True)
                await asyncio.sleep(min(delay, max(0.0, deadline - time.monotonic())))
                delay = min(15.0, delay * 2)
    return {"events": written, "full_draws": len(complete_draws)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    live = commands.add_parser("capture", help="append raw SignalR states to JSONL")
    live.add_argument("output", type=Path)
    live.add_argument("--locale", default="fr-ch")
    live.add_argument("--duration", type=float, default=0, help="seconds; 0 runs until interrupted")
    live.add_argument("--max-events", type=int, default=0, help="0 means unlimited")
    live.add_argument("--max-draws", type=int, default=0, help="stop after N complete DrawScene orders")
    live.add_argument(
        "--expected-draw-id", type=int,
        help="correlate a SignalR state lacking an id with one preselected REST draw",
    )
    live.add_argument("--verbose", action="store_true", help="log sanitized protocol transitions")
    inspect = commands.add_parser("inspect", help="audit an existing capture")
    inspect.add_argument("input", type=Path)
    validate = commands.add_parser("validate", help="correlate captured order with exact REST evidence")
    validate.add_argument("input", type=Path)
    validate.add_argument("--draw-id", type=int, help="required when SignalR omitted the draw id")
    validate.add_argument("--retry-seconds", type=float, default=120)
    validate.add_argument("--retry-interval", type=float, default=2)
    validate.add_argument("--output", type=Path)
    export = commands.add_parser("export", help="write chronological input for keno_break")
    export.add_argument("input", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--validation", required=True, type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "capture":
            stats = asyncio.run(capture(
                args.output,
                args.locale,
                args.duration,
                args.max_events,
                args.max_draws,
                args.expected_draw_id,
                args.verbose,
            ))
            print(
                f"recorded {stats['events']} state event(s), "
                f"{stats['full_draws']} complete DrawScene order(s) in {args.output}"
            )
        elif args.command == "inspect":
            print(json.dumps(analyze(read_jsonl(args.input)), indent=2, ensure_ascii=False))
        elif args.command == "validate":
            output = args.output or Path(str(args.input) + ".validation.json")
            if paths_alias(args.input, output):
                raise ValueError("validation output must differ from capture input")
            report = validate_capture(
                read_jsonl(args.input),
                args.draw_id,
                args.retry_seconds,
                args.retry_interval,
            )
            write_json_atomic(output, report)
            summary = {
                "output": str(output),
                "results": [
                    {
                        "draw_id": result["draw_id"],
                        "verdict": result["verdict"],
                        "checks": result["checks"],
                        "timing": result["timing"],
                    }
                    for result in report["results"]
                ],
            }
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            if any(result["verdict"] != "VERIFIED_ORDER" for result in report["results"]):
                return 3
        elif args.command == "export":
            manifest = args.output.with_suffix(args.output.suffix + ".manifest.jsonl")
            protected = (args.input, args.validation)
            if any(paths_alias(args.output, path) for path in protected):
                raise ValueError("export output must differ from capture and validation inputs")
            if any(paths_alias(manifest, path) for path in (*protected, args.output)):
                raise ValueError("export manifest must not alias an input or output")
            with args.validation.open(encoding="utf-8") as handle:
                validation = json.load(handle)
            if not isinstance(validation, dict):
                raise ValueError("validation file is not an object")
            print(json.dumps(
                export_order(read_jsonl(args.input), args.output, validation),
                indent=2,
                ensure_ascii=False,
            ))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
