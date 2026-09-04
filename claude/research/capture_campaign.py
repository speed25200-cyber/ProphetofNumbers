#!/usr/bin/env python3
"""Run an auditable, resumable campaign of live Loto Express order captures.

This module deliberately delegates all wire parsing and proof decisions to
``capture_order.py``.  It only discovers the next open draw, orchestrates the
capture/inspect/validate/export sequence, and promotes results which
``capture_order.validation_index`` independently recomputes as VERIFIED_ORDER.

The campaign journal and verified manifest are append-written SHA-256 chains.
Given a separately retained chain head they expose later local modification,
but the host can rewrite a chain wholesale: this is neither externally enforced
append-only storage nor an authenticated timestamp.  Timing claims therefore
retain the clock/RTT qualification from capture_order.
The plain-text solver inputs are derived artifacts split at every draw-id gap,
so a missing capture can never be mistaken for a contiguous RNG stream.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import hashlib
import json
import os
import stat
import sys
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable

import capture_order


REST_DRAWS_URL = "https://jeux.loro.ch/api/dbg/game/lotoexpress/draws"
JOURNAL_NAME = "campaign.journal.jsonl"
MANIFEST_NAME = "verified.manifest.jsonl"
LOCK_NAME = ".campaign.lock"
FINAL_PHASES = frozenset(("CLOSED", "DRAWING", "PAYABLE", "RESULTS_AVAILABLE"))
EXPECTED_DRAW_INTERVAL_SECONDS = 5 * 60
MAX_DRAW_INTERVAL_DRIFT_SECONDS = 5


class CampaignIntegrityError(ValueError):
    """An on-disk campaign artifact no longer verifies."""


@dataclass(frozen=True)
class Candidate:
    draw_id: int
    draw_date: str
    wager_end_date: str
    wager_end_ns: int
    phase: str | None


@dataclass(frozen=True)
class CampaignConfig:
    locale: str = "fr-ch"
    capture_duration: float = 600.0
    capture_lead_seconds: float = 330.0
    discovery_interval: float = 10.0
    rest_retry_seconds: float = 180.0
    rest_retry_interval: float = 2.0
    max_draws: int = 0
    max_runtime: float = 0.0
    verbose: bool = False


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def parse_aware_iso_ns(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    try:
        return int(parsed.timestamp() * 1_000_000_000)
    except (OverflowError, OSError, ValueError):
        return None


def _strict_positive_int(value: Any) -> int | None:
    parsed = capture_order.as_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def select_next_candidate(
    payload: dict[str, Any], now_ns: int, *, grace_seconds: float = 30.0
) -> Candidate:
    """Select one open slot deterministically from the REST list response."""
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ValueError("open-draw response has no results array")
    by_id: dict[int, Candidate] = {}
    conflict_ids: set[int] = set()
    lower_bound = now_ns - int(max(0.0, grace_seconds) * 1_000_000_000)
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        draw_id = _strict_positive_int(raw.get("drawNumber"))
        draw_date = raw.get("drawDate")
        wager_end_date = raw.get("wagerEndDate")
        wager_end_ns = parse_aware_iso_ns(wager_end_date)
        if (
            draw_id is None
            or not isinstance(draw_date, str)
            or parse_aware_iso_ns(draw_date) is None
            or not isinstance(wager_end_date, str)
            or wager_end_ns is None
            or wager_end_ns < lower_bound
        ):
            continue
        phase_value = raw.get("phase")
        phase = phase_value.upper() if isinstance(phase_value, str) else None
        if phase in FINAL_PHASES or capture_order.rest_has_complete_result(
            capture_order.parse_rest_draw(raw)
        ):
            continue
        candidate = Candidate(draw_id, draw_date, wager_end_date, wager_end_ns, phase)
        previous = by_id.get(draw_id)
        if previous is not None and previous != candidate:
            conflict_ids.add(draw_id)
        else:
            by_id[draw_id] = candidate
    if conflict_ids:
        raise ValueError(f"conflicting open-draw rows for ids {sorted(conflict_ids)}")
    if not by_id:
        raise ValueError("open-draw response contains no eligible future draw")
    return min(by_id.values(), key=lambda row: (row.wager_end_ns, row.draw_id))


def discovery_url() -> str:
    query = urllib.parse.urlencode({
        "status": "OPEN",
        "size": 8,
        "_": int(time.time() * 1000),
        "l": "fr-CH",
    })
    return f"{REST_DRAWS_URL}?{query}"


def validate_discovery_evidence(
    payload: dict[str, Any], evidence: dict[str, Any]
) -> None:
    expected = urllib.parse.urlsplit(REST_DRAWS_URL)
    url = evidence.get("url")
    actual = urllib.parse.urlsplit(url) if isinstance(url, str) else None
    if (
        actual is None
        or actual.scheme != expected.scheme
        or actual.hostname != expected.hostname
        or actual.path != expected.path
    ):
        raise ValueError("open-draw evidence URL is not the official draws endpoint")
    if evidence.get("status") != 200:
        raise ValueError("open-draw discovery did not return HTTP 200")
    encoded = evidence.get("body_base64")
    if not isinstance(encoded, str):
        raise ValueError("open-draw discovery did not preserve its exact body")
    try:
        body = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("open-draw discovery body is not valid base64") from exc
    if (
        evidence.get("body_bytes") != len(body)
        or evidence.get("body_sha256") != hashlib.sha256(body).hexdigest()
    ):
        raise ValueError("open-draw discovery body hash/length mismatch")
    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("open-draw discovery exact body is not JSON") from exc
    if decoded != payload:
        raise ValueError("open-draw discovery payload differs from its exact body")


def discover_next_draw() -> tuple[Candidate, dict[str, Any], dict[str, Any]]:
    payload, evidence = capture_order.get_json_evidence(discovery_url())
    validate_discovery_evidence(payload, evidence)
    now_ns = evidence.get("server_unix_ns")
    if type(now_ns) is not int:
        now_ns = evidence.get("response_wall_ns")
    if type(now_ns) is not int or now_ns <= 0:
        raise ValueError("open-draw discovery has no usable time evidence")
    return select_next_candidate(payload, now_ns), payload, evidence


def _chain_hash(row: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in row.items() if key != "entry_sha256"}
    return capture_order.canonical_sha256(unsigned)


def read_chain(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink():
        raise CampaignIntegrityError(f"refusing symlinked chain: {path}")
    if not path.exists():
        return []
    metadata = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise CampaignIntegrityError(f"chain is not a single-link regular file: {path}")
    rows: list[dict[str, Any]] = []
    previous: str | None = None
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise CampaignIntegrityError(f"{path}:{line_number}: partial final record")
            if not line.strip():
                raise CampaignIntegrityError(f"{path}:{line_number}: blank record")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CampaignIntegrityError(
                    f"{path}:{line_number}: invalid JSON"
                ) from exc
            if not isinstance(row, dict):
                raise CampaignIntegrityError(f"{path}:{line_number}: record is not an object")
            if row.get("schema") != 1 or row.get("sequence") != len(rows):
                raise CampaignIntegrityError(f"{path}:{line_number}: invalid schema/sequence")
            if row.get("previous_entry_sha256") != previous:
                raise CampaignIntegrityError(f"{path}:{line_number}: broken hash chain")
            expected = _chain_hash(row)
            if row.get("entry_sha256") != expected:
                raise CampaignIntegrityError(f"{path}:{line_number}: entry SHA-256 mismatch")
            rows.append(row)
            previous = expected
    return rows


def append_chain(path: Path, event: str, fields: dict[str, Any]) -> dict[str, Any]:
    if not event or not isinstance(event, str):
        raise ValueError("chain event must be a non-empty string")
    reserved = {
        "schema", "sequence", "recorded_at", "event",
        "previous_entry_sha256", "entry_sha256",
    }
    if reserved.intersection(fields):
        raise ValueError("chain fields overwrite reserved metadata")
    rows = read_chain(path)
    row = {
        "schema": 1,
        "sequence": len(rows),
        "recorded_at": capture_order.utc_now(),
        "event": event,
        "previous_entry_sha256": rows[-1]["entry_sha256"] if rows else None,
        **fields,
    }
    row["entry_sha256"] = _chain_hash(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CampaignIntegrityError(f"cannot open append-only chain {path}") from exc
    encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode()
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise CampaignIntegrityError(
                f"chain is not a single-link regular file: {path}"
            )
        view = memoryview(encoded)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short append")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return row


class CampaignLock:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.descriptor: int | None = None

    def __enter__(self) -> "CampaignLock":
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / LOCK_NAME
        if path.is_symlink():
            raise CampaignIntegrityError("refusing symlinked campaign lock")
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        self.descriptor = os.open(path, flags, 0o600)
        try:
            import fcntl

            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            pass
        except BlockingIOError as exc:
            os.close(self.descriptor)
            self.descriptor = None
            raise ValueError("another campaign process already holds the lock") from exc
        return self

    def __exit__(self, *_args: Any) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None


def _relative_artifact(root: Path, path: Path) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(root.resolve(strict=False)))
    except ValueError as exc:
        raise CampaignIntegrityError("campaign artifact escapes its root") from exc


def _artifact_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CampaignIntegrityError("manifest artifact path is missing")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise CampaignIntegrityError("manifest artifact path is not relative")
    path = root / relative_path
    cursor = root
    for part in relative_path.parts:
        cursor /= part
        if cursor.is_symlink():
            raise CampaignIntegrityError("manifest artifact traverses a symlink")
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise CampaignIntegrityError("manifest artifact escapes its root") from exc
    if not path.is_file() or path.is_symlink():
        raise CampaignIntegrityError(f"manifest artifact is not a regular file: {relative}")
    if path.stat(follow_symlinks=False).st_nlink != 1:
        raise CampaignIntegrityError(f"manifest artifact has hard-link aliases: {relative}")
    return path


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignIntegrityError(f"cannot read JSON artifact {path}") from exc
    if not isinstance(value, dict):
        raise CampaignIntegrityError(f"JSON artifact is not an object: {path}")
    return value


def matching_capture_receipt(
    root: Path,
    draw_id: int,
    capture_path: Path,
    journal: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Find a campaign-written receipt for the exact current capture bytes."""
    if not capture_path.is_file() or capture_path.is_symlink():
        return None
    relative = _relative_artifact(root, capture_path)
    digest = file_sha256(capture_path)
    rows = read_chain(root / JOURNAL_NAME) if journal is None else journal
    for row in reversed(rows):
        if (
            row.get("event") in {
                "CAPTURE_FINISHED"
            }
            and row.get("draw_id") == draw_id
            and row.get("capture_path") == relative
            and row.get("capture_file_sha256") == digest
            and type(row.get("capture_record_count")) is int
            and row["capture_record_count"] >= 0
        ):
            return row
    return None


def pending_candidates(root: Path) -> list[Candidate]:
    """Recover draws whose capture/validation transaction did not terminate."""
    verified_ids = {row["draw_id"] for row in verify_manifest(root)}
    journal = read_chain(root / JOURNAL_NAME)
    discoveries: dict[int, Candidate] = {}
    last_work: dict[int, int] = {}
    last_terminal: dict[int, int] = {}
    work_events = {
        "CAPTURE_STARTED", "CAPTURE_FINISHED",
        "INSPECTED", "VALIDATED", "DRAW_FAILED",
    }
    terminal_events = {"NOT_PROMOTED", "PROMOTED"}
    for row in journal:
        draw_id = row.get("draw_id")
        if type(draw_id) is not int:
            continue
        if row.get("event") == "DISCOVERED":
            details = row.get("candidate")
            if isinstance(details, dict):
                draw_date = details.get("draw_date")
                wager_end_date = details.get("wager_end_date")
                wager_end_ns = parse_aware_iso_ns(wager_end_date)
                phase = details.get("phase")
                if (
                    isinstance(draw_date, str)
                    and parse_aware_iso_ns(draw_date) is not None
                    and isinstance(wager_end_date, str)
                    and wager_end_ns is not None
                    and (phase is None or isinstance(phase, str))
                ):
                    discoveries[draw_id] = Candidate(
                        draw_id, draw_date, wager_end_date, wager_end_ns, phase
                    )
        if row.get("event") in work_events:
            last_work[draw_id] = row["sequence"]
        if row.get("event") in terminal_events:
            last_terminal[draw_id] = row["sequence"]
    pending = []
    for draw_id, work_sequence in last_work.items():
        if (
            draw_id in verified_ids
            or work_sequence <= last_terminal.get(draw_id, -1)
            or draw_id not in discoveries
        ):
            continue
        capture_path = root / "draws" / str(draw_id) / "capture.jsonl"
        if capture_path.is_file() and not capture_path.is_symlink():
            pending.append(discoveries[draw_id])
    return sorted(pending, key=lambda item: item.draw_id)


def verify_manifest(root: Path) -> list[dict[str, Any]]:
    rows = read_chain(root / MANIFEST_NAME)
    journal = read_chain(root / JOURNAL_NAME)
    seen: set[int] = set()
    for row in rows:
        draw_id = row.get("draw_id")
        balls = row.get("balls")
        draw_date_ns = parse_aware_iso_ns(row.get("draw_date"))
        wager_end_ns = parse_aware_iso_ns(row.get("wager_end_date"))
        if (
            row.get("event") != "VERIFIED_ORDER"
            or row.get("order_scope") != "ANIMATION_SEQUENCE_ONLY"
            or row.get("evidence_kind") != "LIVE_SIGNALR_AND_REST"
            or type(draw_id) is not int
            or draw_id <= 0
            or draw_id in seen
            or not isinstance(balls, list)
            or len(balls) != 20
            or len(set(balls)) != 20
            or not all(type(value) is int and 1 <= value <= 80 for value in balls)
            or draw_date_ns is None
            or wager_end_ns is None
        ):
            raise CampaignIntegrityError("verified manifest contains a malformed draw")
        seen.add(draw_id)
        capture_path = _artifact_path(root, row.get("capture_path"))
        validation_path = _artifact_path(root, row.get("validation_path"))
        order_path = _artifact_path(root, row.get("order_path"))
        order_manifest_path = _artifact_path(root, row.get("order_manifest_path"))
        expected_hashes = {
            capture_path: row.get("capture_file_sha256"),
            validation_path: row.get("validation_file_sha256"),
            order_path: row.get("order_file_sha256"),
            order_manifest_path: row.get("order_manifest_file_sha256"),
        }
        for artifact, expected_hash in expected_hashes.items():
            if expected_hash != file_sha256(artifact):
                raise CampaignIntegrityError(f"artifact SHA-256 mismatch: {artifact}")
        receipt = matching_capture_receipt(root, draw_id, capture_path, journal)
        if (
            receipt is None
            or row.get("capture_receipt_entry_sha256") != receipt.get("entry_sha256")
        ):
            raise CampaignIntegrityError(
                f"draw {draw_id} has no matching live campaign capture receipt"
            )
        records = capture_order.read_jsonl(capture_path)
        if receipt.get("capture_record_count") != len(records):
            raise CampaignIntegrityError(
                f"draw {draw_id} capture receipt record count differs from artifact"
            )
        validation = _read_json_object(validation_path)
        verified = capture_order.validation_index(validation, records)
        if set(verified) != {draw_id} or verified[draw_id].get("balls") != balls:
            raise CampaignIntegrityError(
                f"draw {draw_id} no longer recomputes as VERIFIED_ORDER"
            )
        expected_line = " ".join(map(str, balls)) + "\n"
        if order_path.read_text(encoding="utf-8") != expected_line:
            raise CampaignIntegrityError(f"draw {draw_id} solver export differs from evidence")
        export_rows = capture_order.read_jsonl(order_manifest_path)
        if len(export_rows) != 1:
            raise CampaignIntegrityError(f"draw {draw_id} export manifest is not singular")
        captured_record = verified[draw_id]
        expected_export_record = dict(captured_record)
        expected_export_record["boost"] = capture_order.observed_boost(captured_record)
        expected_export_record["capture_draw_id"] = captured_record.get("draw_id")
        expected_export_record["draw_id"] = draw_id
        expected_export_record["draw_id_source"] = (
            captured_record.get("draw_id_source")
            if captured_record.get("draw_id") == draw_id else "validation"
        )
        expected_export_record["order_scope"] = capture_order.ORDER_SCOPE
        kept_keys = (
            "draw_id", "received_at", "received_unix_ns", "received_monotonic_ns",
            "session_id", "frame_index", "scene", "locale", "raw_sha256", "balls",
            "boost", "extra", "capture_draw_id", "draw_id_source",
            "order_scope",
        )
        expected_export = {key: expected_export_record.get(key) for key in kept_keys}
        if export_rows[0] != expected_export:
            raise CampaignIntegrityError(f"draw {draw_id} export manifest differs from evidence")
        result = _result_for_draw(validation, draw_id)
        if result is None:
            raise CampaignIntegrityError(f"draw {draw_id} validation result is missing")
        animation = result.get("animation")
        rest = result.get("rest")
        http = rest.get("http") if isinstance(rest, dict) else None
        if (
            not isinstance(animation, dict)
            or not isinstance(http, dict)
            or row.get("capture_record_sha256") != animation.get("capture_record_sha256")
            or row.get("rest_body_sha256") != http.get("body_sha256")
            or row.get("timing") != result.get("timing")
            or row.get("draw_date") != rest.get("draw_date")
            or row.get("wager_end_date") != rest.get("wager_end_date")
        ):
            raise CampaignIntegrityError(f"draw {draw_id} promotion summary differs from evidence")
    return rows


def contiguous_segments(rows: Iterable[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: row["draw_id"])
    segments: list[list[dict[str, Any]]] = []
    for row in ordered:
        contiguous = False
        if segments:
            previous = segments[-1][-1]
            previous_ns = parse_aware_iso_ns(previous.get("draw_date"))
            current_ns = parse_aware_iso_ns(row.get("draw_date"))
            if previous_ns is None or current_ns is None:
                raise CampaignIntegrityError("verified row has no usable draw chronology")
            interval_seconds = (current_ns - previous_ns) / 1_000_000_000
            contiguous = (
                row["draw_id"] == previous["draw_id"] + 1
                and abs(interval_seconds - EXPECTED_DRAW_INTERVAL_SECONDS)
                <= MAX_DRAW_INTERVAL_DRIFT_SECONDS
            )
        if not segments or not contiguous:
            segments.append([row])
        else:
            segments[-1].append(row)
    return segments


def boundary_from_previous(
    previous: dict[str, Any] | None, current: dict[str, Any]
) -> dict[str, Any] | None:
    if previous is None:
        return None
    previous_id = previous["draw_id"]
    current_id = current["draw_id"]
    previous_ns = parse_aware_iso_ns(previous.get("draw_date"))
    current_ns = parse_aware_iso_ns(current.get("draw_date"))
    gap_seconds = (
        None if previous_ns is None or current_ns is None
        else round((current_ns - previous_ns) / 1_000_000_000, 3)
    )
    reasons = []
    if current_id != previous_id + 1:
        reasons.append("DRAW_ID_GAP")
    if (
        gap_seconds is None
        or abs(gap_seconds - EXPECTED_DRAW_INTERVAL_SECONDS)
        > MAX_DRAW_INTERVAL_DRIFT_SECONDS
    ):
        reasons.append("TIME_GAP_OR_SESSION_BOUNDARY")
    return {
        "previous_draw_id": previous_id,
        "current_draw_id": current_id,
        "draw_time_gap_seconds": gap_seconds,
        "reasons": reasons,
    }


def rebuild_datasets(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    datasets_dir = root / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    index_segments: list[dict[str, Any]] = []
    previous_segment_last: dict[str, Any] | None = None
    for segment in contiguous_segments(rows):
        first_id = segment[0]["draw_id"]
        last_id = segment[-1]["draw_id"]
        stem = f"ordered-{first_id}-{last_id}"
        data_path = datasets_dir / f"{stem}.txt"
        evidence_path = datasets_dir / f"{stem}.manifest.jsonl"
        capture_order.write_text_atomic(data_path, "".join(
            " ".join(map(str, row["balls"])) + "\n" for row in segment
        ))
        capture_order.write_text_atomic(evidence_path, "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in segment
        ))
        index_segments.append({
            "first_draw_id": first_id,
            "last_draw_id": last_id,
            "draws": len(segment),
            "data": _relative_artifact(root, data_path),
            "manifest": _relative_artifact(root, evidence_path),
            "data_sha256": file_sha256(data_path),
            "manifest_sha256": file_sha256(evidence_path),
            "boundary_from_previous": boundary_from_previous(
                previous_segment_last, segment[0]
            ),
        })
        previous_segment_last = segment[-1]
    index = {
        "schema": 1,
        "generated_at": capture_order.utc_now(),
        "verified_draws": len(rows),
        "continuity_rule": {
            "draw_id_step": 1,
            "expected_seconds": EXPECTED_DRAW_INTERVAL_SECONDS,
            "maximum_drift_seconds": MAX_DRAW_INTERVAL_DRIFT_SECONDS,
        },
        "segments": index_segments,
    }
    capture_order.write_json_atomic(datasets_dir / "index.json", index)
    return index


def _target_drawscene_present(records: Iterable[dict[str, Any]], draw_id: int) -> bool:
    return any(
        record.get("draw_id") == draw_id
        and capture_order.valid_ball_sequence(record)
        and str(record.get("scene") or "").lower() == "drawscene"
        for record in records
    )


def _result_for_draw(report: dict[str, Any], draw_id: int) -> dict[str, Any] | None:
    results = report.get("results")
    if not isinstance(results, list):
        return None
    matching = [
        result for result in results
        if isinstance(result, dict) and result.get("draw_id") == draw_id
    ]
    return matching[0] if len(matching) == 1 else None


def _promotion_fields(
    root: Path,
    draw_id: int,
    balls: list[int],
    capture_path: Path,
    validation_path: Path,
    order_path: Path,
    order_manifest_path: Path,
    result: dict[str, Any],
    capture_receipt: dict[str, Any],
) -> dict[str, Any]:
    animation = result.get("animation") if isinstance(result.get("animation"), dict) else {}
    rest = result.get("rest") if isinstance(result.get("rest"), dict) else {}
    http = rest.get("http") if isinstance(rest.get("http"), dict) else {}
    return {
        "draw_id": draw_id,
        "balls": balls,
        "evidence_kind": "LIVE_SIGNALR_AND_REST",
        # VERIFIED_ORDER means the order in which the public animation exposed
        # the 20 matching balls.  It is not yet proof that this is raw RNG order.
        "order_scope": "ANIMATION_SEQUENCE_ONLY",
        "draw_date": rest.get("draw_date"),
        "wager_end_date": rest.get("wager_end_date"),
        "capture_path": _relative_artifact(root, capture_path),
        "validation_path": _relative_artifact(root, validation_path),
        "order_path": _relative_artifact(root, order_path),
        "order_manifest_path": _relative_artifact(root, order_manifest_path),
        "capture_file_sha256": file_sha256(capture_path),
        "capture_receipt_entry_sha256": capture_receipt.get("entry_sha256"),
        "validation_file_sha256": file_sha256(validation_path),
        "order_file_sha256": file_sha256(order_path),
        "order_manifest_file_sha256": file_sha256(order_manifest_path),
        "capture_record_sha256": animation.get("capture_record_sha256"),
        "rest_body_sha256": http.get("body_sha256"),
        "timing": result.get("timing"),
    }


async def process_draw(
    root: Path,
    candidate: Candidate,
    config: CampaignConfig,
    *,
    capture_func: Callable[..., Awaitable[dict[str, int]]] = capture_order.capture,
    validate_func: Callable[..., dict[str, Any]] = capture_order.validate_capture,
) -> str:
    """Return VERIFIED_ORDER, a validation verdict, or NO_OBSERVATION."""
    manifest_path = root / MANIFEST_NAME
    current_manifest = verify_manifest(root)
    if any(row["draw_id"] == candidate.draw_id for row in current_manifest):
        rebuild_datasets(root, current_manifest)
        return "ALREADY_VERIFIED"

    draw_dir = root / "draws" / str(candidate.draw_id)
    draw_dir.mkdir(parents=True, exist_ok=True)
    capture_path = draw_dir / "capture.jsonl"
    inspection_path = draw_dir / "inspection.json"
    validation_path = draw_dir / "validation.json"
    order_path = draw_dir / "ordered.txt"
    order_manifest_path = order_path.with_suffix(order_path.suffix + ".manifest.jsonl")
    if capture_path.is_symlink() or (
        capture_path.exists()
        and (
            not capture_path.is_file()
            or capture_path.stat(follow_symlinks=False).st_nlink != 1
        )
    ):
        raise CampaignIntegrityError("capture path is not a single-link regular file")
    records = capture_order.read_jsonl(capture_path) if capture_path.exists() else []

    if not _target_drawscene_present(records, candidate.draw_id):
        append_chain(root / JOURNAL_NAME, "CAPTURE_STARTED", {
            "draw_id": candidate.draw_id,
            "wager_end_date": candidate.wager_end_date,
            "capture_path": _relative_artifact(root, capture_path),
        })
        stats = await capture_func(
            capture_path,
            config.locale,
            config.capture_duration,
            0,
            1,
            candidate.draw_id,
            config.verbose,
        )
        captured_records = capture_order.read_jsonl(capture_path) if capture_path.exists() else []
        append_chain(root / JOURNAL_NAME, "CAPTURE_FINISHED", {
            "draw_id": candidate.draw_id,
            "stats": stats,
            "capture_path": _relative_artifact(root, capture_path),
            "capture_file_sha256": file_sha256(capture_path),
            "capture_record_count": len(captured_records),
        })
        records = captured_records

    capture_receipt = matching_capture_receipt(
        root, candidate.draw_id, capture_path
    )
    if capture_receipt is None:
        raise CampaignIntegrityError(
            "capture has no matching receipt from this live campaign; refusing preloaded evidence"
        )
    if capture_receipt.get("capture_record_count") != len(records):
        raise CampaignIntegrityError("capture receipt record count differs from artifact")

    inspection = capture_order.analyze(records)
    capture_order.write_json_atomic(inspection_path, inspection)
    append_chain(root / JOURNAL_NAME, "INSPECTED", {
        "draw_id": candidate.draw_id,
        "inspection_path": _relative_artifact(root, inspection_path),
        "inspection": inspection,
    })
    if not _target_drawscene_present(records, candidate.draw_id):
        append_chain(root / JOURNAL_NAME, "NOT_PROMOTED", {
            "draw_id": candidate.draw_id,
            "reason": "NO_AUTHORITATIVE_OBSERVATION",
        })
        return "NO_OBSERVATION"

    report = await asyncio.to_thread(
        validate_func,
        records,
        candidate.draw_id,
        config.rest_retry_seconds,
        config.rest_retry_interval,
    )
    capture_order.write_json_atomic(validation_path, report)
    result = _result_for_draw(report, candidate.draw_id)
    verdict = result.get("verdict") if result is not None else "MALFORMED_VALIDATION"
    append_chain(root / JOURNAL_NAME, "VALIDATED", {
        "draw_id": candidate.draw_id,
        "validation_path": _relative_artifact(root, validation_path),
        "validation_file_sha256": file_sha256(validation_path),
        "verdict": verdict,
    })

    # The saved label is not trusted: validation_index replays every capture and
    # exact REST body before returning this draw.
    verified = capture_order.validation_index(report, records)
    if set(verified) != {candidate.draw_id}:
        append_chain(root / JOURNAL_NAME, "NOT_PROMOTED", {
            "draw_id": candidate.draw_id,
            "reason": "NOT_RECOMPUTED_VERIFIED_ORDER",
            "verdict": verdict,
        })
        return str(verdict)

    verified_rest = result.get("rest") if isinstance(result, dict) else None
    if (
        not isinstance(verified_rest, dict)
        or parse_aware_iso_ns(verified_rest.get("draw_date")) is None
        or parse_aware_iso_ns(verified_rest.get("wager_end_date")) is None
    ):
        raise CampaignIntegrityError(
            "validated REST chronology is not timezone-aware; refusing promotion"
        )
    export_summary = capture_order.export_order(records, order_path, report)
    if export_summary.get("draws") != 1 or not order_manifest_path.is_file():
        raise CampaignIntegrityError("single-draw export did not produce exact artifacts")
    balls = verified[candidate.draw_id].get("balls")
    if not isinstance(balls, list):
        raise CampaignIntegrityError("verified record lost its ordered balls")
    fields = _promotion_fields(
        root, candidate.draw_id, balls, capture_path, validation_path,
        order_path, order_manifest_path, result, capture_receipt,
    )
    # Re-read under the campaign-wide lock immediately before the unique append.
    current_manifest = verify_manifest(root)
    if not any(row["draw_id"] == candidate.draw_id for row in current_manifest):
        append_chain(manifest_path, "VERIFIED_ORDER", fields)
    current_manifest = verify_manifest(root)
    index = rebuild_datasets(root, current_manifest)
    append_chain(root / JOURNAL_NAME, "PROMOTED", {
        "draw_id": candidate.draw_id,
        "manifest_entry": next(
            row["entry_sha256"] for row in current_manifest
            if row["draw_id"] == candidate.draw_id
        ),
        "dataset_segments": len(index["segments"]),
    })
    return "VERIFIED_ORDER"


def _discovery_journal_fields(
    candidate: Candidate, payload: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    public_evidence = capture_order.public_http_evidence(evidence)
    encoded = evidence.get("body_base64")
    if not isinstance(encoded, str):
        # Tests and alternate transports can still provide the exact JSON object;
        # production get_json_evidence always supplies the original bytes.
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        encoded = base64.b64encode(body).decode("ascii")
        public_evidence = {
            **public_evidence,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_bytes": len(body),
        }
    return {
        "draw_id": candidate.draw_id,
        "candidate": {
            "draw_date": candidate.draw_date,
            "wager_end_date": candidate.wager_end_date,
            "phase": candidate.phase,
        },
        "rest_http": public_evidence,
        "rest_body_base64": encoded,
    }


async def _sleep_bounded(seconds: float) -> None:
    await asyncio.sleep(max(0.1, min(300.0, seconds)))


async def run_campaign(
    root: Path,
    config: CampaignConfig,
    *,
    discover_func: Callable[[], tuple[Candidate, dict[str, Any], dict[str, Any]]] = discover_next_draw,
    process_func: Callable[[Path, Candidate, CampaignConfig], Awaitable[str]] = process_draw,
) -> dict[str, Any]:
    if config.max_draws < 0 or config.max_runtime < 0:
        raise ValueError("campaign limits cannot be negative")
    if config.capture_duration <= 0 or config.discovery_interval <= 0:
        raise ValueError("capture duration and discovery interval must be positive")
    started = time.monotonic()
    completed: set[int] = set()
    outcomes: dict[int, str] = {}
    last_discovery_signature: tuple[int, Any] | None = None
    waiting_logged_for: tuple[int, Any] | None = None
    with CampaignLock(root):
        verify_manifest(root)
        read_chain(root / JOURNAL_NAME)
        append_chain(root / JOURNAL_NAME, "CAMPAIGN_STARTED", {
            "configuration": {
                "locale": config.locale,
                "capture_duration": config.capture_duration,
                "capture_lead_seconds": config.capture_lead_seconds,
                "rest_retry_seconds": config.rest_retry_seconds,
                "max_draws": config.max_draws,
                "max_draws_semantics": "DISTINCT_CANDIDATES_WITH_TERMINAL_OUTCOME",
                "max_runtime": config.max_runtime,
            }
        })
        while config.max_draws == 0 or len(completed) < config.max_draws:
            if config.max_runtime and time.monotonic() - started >= config.max_runtime:
                break
            resumable = [
                item for item in pending_candidates(root)
                if item.draw_id not in completed
            ]
            if resumable:
                candidate = resumable[0]
                append_chain(root / JOURNAL_NAME, "RESUMING_PENDING_DRAW", {
                    "draw_id": candidate.draw_id,
                })
                try:
                    outcome = await process_func(root, candidate, config)
                except CampaignIntegrityError:
                    raise
                except (OSError, ValueError) as exc:
                    append_chain(root / JOURNAL_NAME, "DRAW_FAILED", {
                        "draw_id": candidate.draw_id,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    })
                    await _sleep_bounded(config.discovery_interval)
                    continue
                completed.add(candidate.draw_id)
                outcomes[candidate.draw_id] = outcome
                if config.max_draws == 0 or len(completed) < config.max_draws:
                    await _sleep_bounded(config.discovery_interval)
                continue
            try:
                candidate, payload, evidence = await asyncio.to_thread(discover_func)
            except (OSError, ValueError) as exc:
                append_chain(root / JOURNAL_NAME, "DISCOVERY_FAILED", {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
                await _sleep_bounded(config.discovery_interval)
                continue
            discovery_signature = (candidate.draw_id, evidence.get("body_sha256"))
            if discovery_signature != last_discovery_signature:
                append_chain(
                    root / JOURNAL_NAME,
                    "DISCOVERED",
                    _discovery_journal_fields(candidate, payload, evidence),
                )
                last_discovery_signature = discovery_signature
            already_verified = any(
                row["draw_id"] == candidate.draw_id for row in verify_manifest(root)
            )
            if already_verified or candidate.draw_id in completed:
                await _sleep_bounded(config.discovery_interval)
                continue
            now_ns = evidence.get("server_unix_ns")
            if type(now_ns) is not int:
                now_ns = evidence.get("response_wall_ns")
            if type(now_ns) is not int:
                now_ns = time.time_ns()
            wait_seconds = (
                candidate.wager_end_ns - now_ns
            ) / 1_000_000_000 - max(0.0, config.capture_lead_seconds)
            if wait_seconds > 0:
                if waiting_logged_for != discovery_signature:
                    append_chain(root / JOURNAL_NAME, "WAITING_FOR_CAPTURE_WINDOW", {
                        "draw_id": candidate.draw_id,
                        "wait_seconds": round(wait_seconds, 3),
                    })
                    waiting_logged_for = discovery_signature
                idle_poll = max(config.discovery_interval, 300.0)
                await _sleep_bounded(min(wait_seconds, idle_poll))
                continue
            waiting_logged_for = None
            try:
                outcome = await process_func(root, candidate, config)
            except CampaignIntegrityError:
                raise
            except (OSError, ValueError) as exc:
                outcome = f"ERROR:{type(exc).__name__}"
                append_chain(root / JOURNAL_NAME, "DRAW_FAILED", {
                    "draw_id": candidate.draw_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })
                outcomes[candidate.draw_id] = outcome
                await _sleep_bounded(config.discovery_interval)
                continue
            completed.add(candidate.draw_id)
            outcomes[candidate.draw_id] = outcome
            if config.max_draws == 0 or len(completed) < config.max_draws:
                await _sleep_bounded(config.discovery_interval)
        manifest = verify_manifest(root)
        index = rebuild_datasets(root, manifest)
        stopped = append_chain(root / JOURNAL_NAME, "CAMPAIGN_STOPPED", {
            "completed_draws": len(completed),
            "outcomes": {str(key): value for key, value in sorted(outcomes.items())},
            "verified_draws": len(manifest),
        })
        return {
            "completed_draws": len(completed),
            "outcomes": outcomes,
            "verified_draws": len(manifest),
            "segments": index["segments"],
            "journal_head_sha256": stopped["entry_sha256"],
            "manifest_head_sha256": (
                manifest[-1]["entry_sha256"] if manifest else None
            ),
        }


def status(root: Path) -> dict[str, Any]:
    # Readers do not take the campaign's lifetime-exclusive writer lock: status
    # must remain usable while an unlimited campaign is running. Each chain row
    # is appended in one write; a reader that catches that tiny window fails
    # closed and can retry without changing any artifact.
    journal = read_chain(root / JOURNAL_NAME)
    manifest = verify_manifest(root)
    segments = contiguous_segments(manifest)
    summary_segments = []
    previous: dict[str, Any] | None = None
    for segment in segments:
        summary_segments.append({
            "first_draw_id": segment[0]["draw_id"],
            "last_draw_id": segment[-1]["draw_id"],
            "first_draw_date": segment[0]["draw_date"],
            "last_draw_date": segment[-1]["draw_date"],
            "draws": len(segment),
            "boundary_from_previous": boundary_from_previous(previous, segment[0]),
        })
        previous = segment[-1]
    return {
        "journal_events": len(journal),
        "verified_draws": len(manifest),
        "verified_draw_ids": sorted(row["draw_id"] for row in manifest),
        "journal_head_sha256": journal[-1]["entry_sha256"] if journal else None,
        "manifest_head_sha256": manifest[-1]["entry_sha256"] if manifest else None,
        "segments": summary_segments,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="capture and validate consecutive live draws")
    run.add_argument("output", type=Path, help="campaign directory")
    run.add_argument("--locale", default="fr-ch")
    run.add_argument("--capture-duration", type=float, default=600)
    run.add_argument("--capture-lead-seconds", type=float, default=330)
    run.add_argument("--discovery-interval", type=float, default=10)
    run.add_argument("--rest-retry-seconds", type=float, default=180)
    run.add_argument("--rest-retry-interval", type=float, default=2)
    run.add_argument(
        "--max-draws", type=int, default=0,
        help=(
            "maximum distinct candidates reaching a terminal outcome; "
            "transport retries do not count, 0 runs until interrupted"
        ),
    )
    run.add_argument("--max-runtime", type=float, default=0, help="seconds; 0 is unlimited")
    run.add_argument("--verbose", action="store_true")
    inspect = commands.add_parser("status", help="verify chains and summarize a campaign")
    inspect.add_argument("output", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "run":
            config = CampaignConfig(
                locale=args.locale,
                capture_duration=args.capture_duration,
                capture_lead_seconds=args.capture_lead_seconds,
                discovery_interval=args.discovery_interval,
                rest_retry_seconds=args.rest_retry_seconds,
                rest_retry_interval=args.rest_retry_interval,
                max_draws=args.max_draws,
                max_runtime=args.max_runtime,
                verbose=args.verbose,
            )
            result = asyncio.run(run_campaign(args.output, config))
        else:
            result = status(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except KeyboardInterrupt:
        print("campaign interrupted", file=sys.stderr)
        return 130
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
