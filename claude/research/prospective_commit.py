#!/usr/bin/env python3
"""Prepare and verify a prospective exact-number prediction commitment.

The public file contains a salted SHA-256 commitment.  The private reveal binds
the exact ordered prediction, its sorted set, one future draw/cutoff, and a
fully verified recovery evidence bundle.  A local timestamp is informative,
not trusted: publish the public file or its SHA-256 through an independent
timestamped channel before ``wager_end_date``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import proof_bundle


REVEAL_SCHEMA = "org.prophetofnumbers.prospective-reveal"
COMMIT_SCHEMA = "org.prophetofnumbers.prospective-commitment"
VERSION = 1
DOMAIN = b"ProphetofNumbers prospective prediction v1\x00"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SECURITY_NOTICE = (
    "Local creation time is not a trusted timestamp; independently publish "
    "this commitment before wager_end_date."
)


class CommitmentError(ValueError):
    """A prospective prediction or commitment is invalid."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def commitment_sha256(reveal: dict[str, Any]) -> str:
    return hashlib.sha256(DOMAIN + canonical_bytes(reveal)).hexdigest()


def file_sha256(path: Path) -> str:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CommitmentError(f"not a regular evidence file: {path}")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def parse_future_cutoff(value: str, now_ns: int) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CommitmentError("wager_end_date is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CommitmentError("wager_end_date must include a timezone")
    normalized = parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds")
    if int(parsed.timestamp() * 1_000_000_000) <= now_ns:
        raise CommitmentError("target wager_end_date is not in the future")
    return normalized


def validate_prediction(numbers: list[int]) -> list[int]:
    if (
        len(numbers) != 20
        or any(type(number) is not int or not 1 <= number <= 80 for number in numbers)
        or len(set(numbers)) != 20
    ):
        raise CommitmentError("prediction must contain 20 unique integers in 1..80")
    return numbers


def write_exclusive(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, mode)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def prepare_commitment(
    public_path: Path,
    reveal_path: Path,
    *,
    draw_id: int,
    wager_end_date: str,
    prediction: list[int],
    evidence_bundle: Path,
    now_ns: int | None = None,
    salt_hex: str | None = None,
) -> dict[str, Any]:
    if type(draw_id) is not int or draw_id <= 0:
        raise CommitmentError("draw_id must be a positive integer")
    if public_path.resolve(strict=False) == reveal_path.resolve(strict=False):
        raise CommitmentError("public commitment and private reveal must differ")
    if public_path.exists() or reveal_path.exists():
        raise CommitmentError("refusing to overwrite a commitment or reveal")
    prediction = validate_prediction(prediction)
    now_ns = time.time_ns() if now_ns is None else now_ns
    cutoff = parse_future_cutoff(wager_end_date, now_ns)
    try:
        bundle_result = proof_bundle.verify_bundle(evidence_bundle)
    except (proof_bundle.EvidenceError, OSError) as exc:
        raise CommitmentError(f"evidence bundle does not verify: {exc}") from exc
    if bundle_result.get("next_draw_id") != draw_id:
        raise CommitmentError(
            "target draw_id differs from the evidence bundle's next draw"
        )
    bundle_digest = file_sha256(evidence_bundle)
    if bundle_result.get("bundle_sha256") != bundle_digest:
        raise CommitmentError("evidence bundle digest changed after verification")
    if salt_hex is None:
        salt_hex = secrets.token_hex(32)
    if not isinstance(salt_hex, str) or not HEX64.fullmatch(salt_hex):
        raise CommitmentError("salt must be exactly 256 bits of lowercase hex")
    created_at = datetime.fromtimestamp(
        now_ns / 1_000_000_000, timezone.utc
    ).isoformat(timespec="milliseconds")
    reveal = {
        "schema": REVEAL_SCHEMA,
        "version": VERSION,
        "draw_id": draw_id,
        "wager_end_date": cutoff,
        "created_at": created_at,
        "prediction_order": prediction,
        "prediction_set_sorted": sorted(prediction),
        "evidence_bundle_sha256": bundle_digest,
        "evidence_order_scope": bundle_result.get("order_scope"),
        "salt_hex": salt_hex,
    }
    digest = commitment_sha256(reveal)
    public = {
        "schema": COMMIT_SCHEMA,
        "version": VERSION,
        "hash_algorithm": "SHA-256",
        "commitment_sha256": digest,
        "draw_id": draw_id,
        "wager_end_date": cutoff,
        "created_at": created_at,
        "evidence_bundle_sha256": bundle_digest,
        "security_notice": SECURITY_NOTICE,
    }
    reveal_data = canonical_bytes(reveal) + b"\n"
    public_data = canonical_bytes(public) + b"\n"
    write_exclusive(reveal_path, reveal_data, 0o600)
    try:
        write_exclusive(public_path, public_data, 0o644)
    except Exception:
        try:
            reveal_path.unlink()
        except OSError:
            pass
        raise
    return {
        "verdict": "COMMITMENT_PREPARED",
        "commitment_sha256": digest,
        "public_file_sha256": hashlib.sha256(public_data).hexdigest(),
        "draw_id": draw_id,
        "wager_end_date": cutoff,
        "security_notice": SECURITY_NOTICE,
    }


def load_canonical_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = path.read_bytes()
        value = json.loads(data)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CommitmentError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict) or data != canonical_bytes(value) + b"\n":
        raise CommitmentError(f"{label} is not canonical JSON")
    return value


def verify_commitment(public_path: Path, reveal_path: Path) -> dict[str, Any]:
    public = load_canonical_object(public_path, "public commitment")
    reveal = load_canonical_object(reveal_path, "private reveal")
    if set(public) != {
        "schema", "version", "hash_algorithm", "commitment_sha256", "draw_id",
        "wager_end_date", "created_at", "evidence_bundle_sha256", "security_notice",
    }:
        raise CommitmentError("public commitment fields differ from schema")
    if set(reveal) != {
        "schema", "version", "draw_id", "wager_end_date", "created_at",
        "prediction_order", "prediction_set_sorted", "evidence_bundle_sha256",
        "evidence_order_scope", "salt_hex",
    }:
        raise CommitmentError("private reveal fields differ from schema")
    if (
        public["schema"] != COMMIT_SCHEMA
        or reveal["schema"] != REVEAL_SCHEMA
        or type(public["version"]) is not int
        or type(reveal["version"]) is not int
        or public["version"] != VERSION
        or reveal["version"] != VERSION
        or public["hash_algorithm"] != "SHA-256"
        or public["security_notice"] != SECURITY_NOTICE
    ):
        raise CommitmentError("unsupported commitment schema")
    if type(reveal.get("draw_id")) is not int or reveal["draw_id"] <= 0:
        raise CommitmentError("reveal draw_id is invalid")
    if (
        not isinstance(reveal.get("evidence_bundle_sha256"), str)
        or not HEX64.fullmatch(reveal["evidence_bundle_sha256"])
        or reveal.get("evidence_order_scope") != "ANIMATION_SEQUENCE_ONLY"
    ):
        raise CommitmentError("reveal evidence binding is invalid")
    for field in ("created_at", "wager_end_date"):
        value = reveal.get(field)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise CommitmentError(f"reveal {field} is not ISO-8601") from exc
        if parsed.tzinfo is None:
            raise CommitmentError(f"reveal {field} has no timezone")
    prediction = reveal.get("prediction_order")
    if not isinstance(prediction, list):
        raise CommitmentError("prediction_order is not an array")
    validate_prediction(prediction)
    if reveal.get("prediction_set_sorted") != sorted(prediction):
        raise CommitmentError("sorted prediction differs from prediction order")
    if not isinstance(reveal.get("salt_hex"), str) or not HEX64.fullmatch(
        reveal["salt_hex"]
    ):
        raise CommitmentError("reveal salt is invalid")
    linked = (
        "draw_id", "wager_end_date", "created_at", "evidence_bundle_sha256"
    )
    if any(public.get(key) != reveal.get(key) for key in linked):
        raise CommitmentError("public metadata differs from reveal")
    digest = commitment_sha256(reveal)
    if public.get("commitment_sha256") != digest:
        raise CommitmentError("prediction commitment does not match reveal")
    return {
        "verdict": "REVEAL_MATCHES_COMMITMENT",
        "commitment_sha256": digest,
        "draw_id": reveal["draw_id"],
        "wager_end_date": reveal["wager_end_date"],
        "prediction_order": prediction,
        "prediction_set_sorted": reveal["prediction_set_sorted"],
        "evidence_bundle_sha256": reveal["evidence_bundle_sha256"],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("public", type=Path)
    prepare.add_argument("reveal", type=Path)
    prepare.add_argument("--draw-id", required=True, type=int)
    prepare.add_argument("--wager-end-date", required=True)
    prepare.add_argument("--prediction", required=True, nargs=20, type=int)
    prepare.add_argument("--evidence-bundle", required=True, type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("public", type=Path)
    verify.add_argument("reveal", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_commitment(
                args.public,
                args.reveal,
                draw_id=args.draw_id,
                wager_end_date=args.wager_end_date,
                prediction=args.prediction,
                evidence_bundle=args.evidence_bundle,
            )
        else:
            result = verify_commitment(args.public, args.reveal)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (CommitmentError, OSError) as exc:
        print(f"commitment error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
