#!/usr/bin/env python3
"""Create and verify a SHA-256 manifest for a recovery evidence chain.

The bundle links the exact animation capture, REST validation report, exported
ordered dataset, export manifest, recovery checkpoint, and the two source files
that interpret them.  Its printed SHA-256 becomes a prospective commitment only
if that digest is recorded independently before the result being predicted.

This is deliberately *not* a signature, trusted timestamp, or attestation of the
capture host.  SHA-256 supplies byte integrity and internal linkage; provenance
and time require an external signed publication or timestamping service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import capture_order


SCHEMA = "org.prophetofnumbers.recovery-evidence"
VERSION = 1
MAX_FILE_BYTES = 512 * 1024 * 1024
MAGIC = "KENO_BREAK_MT19937"
STATE_VERSION = 1
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
MASK64 = (1 << 64) - 1
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX8 = re.compile(r"[0-9a-f]{8}\Z")

SECURITY_MODEL = {
    "guarantee": (
        "SHA-256 byte integrity and deterministic linkage of the evidence chain "
        "when the bundle digest is independently retained"
    ),
    "not_guaranteed": (
        "origin, trusted capture time, RNG identity, identity of the executed "
        "binary, checkpoint correctness, or future prediction accuracy"
    ),
    "prospective_use": (
        "publish or externally timestamp the exact bundle_sha256 before the "
        "draw whose prediction is being tested"
    ),
    "prediction_commitment": (
        "the digest commits to a deterministic checkpoint and solver source, "
        "not to an explicit twenty-number prediction; publish an exact numbered "
        "prediction before the target draw for the final commit-reveal test"
    ),
}


class EvidenceError(ValueError):
    """The evidence chain is malformed, inconsistent, or has changed."""


@dataclass(frozen=True)
class Snapshot:
    path: Path
    data: bytes
    sha256: str

    @property
    def size(self) -> int:
        return len(self.data)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return _sha256(_canonical_bytes(value))


def _duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise EvidenceError(f"non-finite JSON value is forbidden: {value}")


def _json_value(data: bytes, label: str) -> Any:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{label} is not UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise EvidenceError(f"{label} is not strict JSON: {exc}") from exc


def _jsonl_values(data: bytes, label: str) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceError(f"{label} is not UTF-8") from exc
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(
                line,
                object_pairs_hook=_duplicate_safe_object,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, TypeError) as exc:
            raise EvidenceError(f"{label}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise EvidenceError(f"{label}:{line_number}: expected a JSON object")
        values.append(value)
    return values


def _snapshot(path: Path) -> Snapshot:
    path = Path(path)
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    except OSError as exc:
        raise EvidenceError(f"cannot open {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise EvidenceError(f"{path} is not a regular file")
        if before.st_size > MAX_FILE_BYTES:
            raise EvidenceError(f"{path} exceeds the {MAX_FILE_BYTES}-byte safety limit")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                raise EvidenceError(f"{path} changed while it was read")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise EvidenceError(f"{path} grew while it was read")
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after:
            raise EvidenceError(f"{path} changed while it was read")
    finally:
        os.close(descriptor)
    data = b"".join(chunks)
    return Snapshot(path=path, data=data, sha256=_sha256(data))


# Freeze the source bytes recognized by this process.  In particular, comparing
# against a file re-read much later would not prove that it still corresponds to
# the already-imported capture_order functions used for semantic validation.
_RECOGNIZED_IMPLEMENTATIONS = {
    "capture": _snapshot(Path(capture_order.__file__).resolve()).data,
    "solver": _snapshot(Path(__file__).resolve().parent / "keno_break.c").data,
}


def _exact_keys(value: Any, keys: Iterable[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    expected = set(keys)
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise EvidenceError(f"{label} keys differ (missing={missing}, extra={extra})")
    return value


def _fnv_byte(value: int, byte: int) -> int:
    return ((value ^ byte) * FNV_PRIME) & MASK64


def _fnv_integer(value: int, integer: int, byte_count: int) -> int:
    for shift in range(0, byte_count * 8, 8):
        value = _fnv_byte(value, (integer >> shift) & 0xFF)
    return value


def _ordered_input_fnv(draws: list[list[int]]) -> int:
    value = _fnv_integer(FNV_OFFSET, len(draws), 4)
    for draw in draws:
        for ball in draw:
            value = _fnv_integer(value, ball, 4)
    return value


def _checkpoint_checksum(fields: dict[str, int], words: list[int]) -> int:
    value = FNV_OFFSET
    for byte in MAGIC.encode("ascii"):
        value = _fnv_byte(value, byte)
    for integer in (
        STATE_VERSION,
        fields["sampler"],
        fields["mapping"],
        fields["stride"],
        fields["draws_consumed"],
        fields["holdout"],
    ):
        value = _fnv_integer(value, integer, 4)
    value = _fnv_integer(value, fields["input_fnv1a64"], 8)
    value = _fnv_integer(value, fields["mti"], 4)
    for word in words:
        value = _fnv_integer(value, word, 4)
    return value


def _decimal(line: str, label: str, minimum: int, maximum: int) -> int:
    match = re.fullmatch(re.escape(label) + r" (0|[1-9][0-9]*)", line)
    if not match:
        raise EvidenceError(f"checkpoint has a non-canonical {label} line")
    value = int(match.group(1))
    if not minimum <= value <= maximum:
        raise EvidenceError(f"checkpoint {label} is outside {minimum}..{maximum}")
    return value


def _parse_checkpoint(data: bytes, draws: list[list[int]]) -> dict[str, Any]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EvidenceError("checkpoint is not ASCII") from exc
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise EvidenceError("checkpoint is not canonical LF-terminated text")
    lines = text[:-1].split("\n")
    if len(lines) != 89:
        raise EvidenceError("checkpoint must contain exactly 89 canonical lines")
    if lines[0] != f"{MAGIC} {STATE_VERSION}" or lines[8] != "words 624":
        raise EvidenceError("checkpoint magic/version/word count is invalid")
    fields = {
        "sampler": _decimal(lines[1], "sampler", 0, 2),
        "mapping": _decimal(lines[2], "mapping", 0, 2),
        "stride": _decimal(lines[3], "stride", 20, 4096),
        "draws_consumed": _decimal(lines[4], "draws_consumed", 1, (1 << 31) - 1),
        "holdout": _decimal(lines[5], "holdout", 1, (1 << 31) - 1),
        "mti": _decimal(lines[7], "mti", 0, 624),
    }
    input_match = re.fullmatch(r"input_fnv1a64 ([0-9a-f]{16})", lines[6])
    if not input_match:
        raise EvidenceError("checkpoint input_fnv1a64 is not canonical")
    fields["input_fnv1a64"] = int(input_match.group(1), 16)
    if fields["holdout"] > fields["draws_consumed"]:
        raise EvidenceError("checkpoint holdout exceeds draws_consumed")
    if fields["holdout"] == fields["draws_consumed"]:
        raise EvidenceError("checkpoint holdout leaves no recovery-training draw")
    words: list[int] = []
    for line_number, line in enumerate(lines[9:87], 10):
        tokens = line.split(" ")
        if len(tokens) != 8 or any(not HEX8.fullmatch(token) for token in tokens):
            raise EvidenceError(
                f"checkpoint state line {line_number} must have eight lowercase words"
            )
        words.extend(int(token, 16) for token in tokens)
    if len(words) != 624 or not any(words):
        raise EvidenceError("checkpoint MT state is empty or all zero")
    checksum_match = re.fullmatch(r"checksum_fnv1a64 ([0-9a-f]{16})", lines[87])
    if not checksum_match or lines[88] != "end":
        raise EvidenceError("checkpoint checksum/end marker is invalid")
    checksum = int(checksum_match.group(1), 16)
    if checksum != _checkpoint_checksum(fields, words):
        raise EvidenceError("checkpoint FNV checksum does not match its fields/state")
    if fields["draws_consumed"] != len(draws):
        raise EvidenceError("checkpoint draws_consumed differs from ordered dataset")
    expected_mti = ((fields["stride"] * fields["draws_consumed"] - 1) % 624) + 1
    if fields["mti"] != expected_mti:
        raise EvidenceError(
            "checkpoint mti is inconsistent with stride * draws_consumed"
        )
    expected_input = _ordered_input_fnv(draws)
    if fields["input_fnv1a64"] != expected_input:
        raise EvidenceError("checkpoint input_fnv1a64 differs from ordered dataset")
    return {
        "format": MAGIC,
        "version": STATE_VERSION,
        "sampler": fields["sampler"],
        "mapping": fields["mapping"],
        "stride": fields["stride"],
        "draws_consumed": fields["draws_consumed"],
        "holdout": fields["holdout"],
        "input_fnv1a64": f"{fields['input_fnv1a64']:016x}",
        "mti": fields["mti"],
        "state_words": 624,
        "checksum_fnv1a64": f"{checksum:016x}",
        "binding_status": "FORMAT_AND_ORDERED_INPUT_CONSISTENT_ONLY",
        "claimed_position": "immediately before the first output of the next draw",
    }


def _expected_export(
    capture_data: bytes, validation_data: bytes
) -> tuple[bytes, bytes, list[dict[str, Any]], dict[str, Any]]:
    records = _jsonl_values(capture_data, "capture")
    validation = _json_value(validation_data, "validation")
    if not isinstance(validation, dict):
        raise EvidenceError("validation must be a JSON object")
    try:
        verified = capture_order.validation_index(validation, records)
    except (ValueError, KeyError, TypeError) as exc:
        raise EvidenceError(f"capture/REST validation failed: {exc}") from exc
    ids = sorted(verified)
    if not ids:
        raise EvidenceError("validation contains no VERIFIED_ORDER draw")
    if any(current != previous + 1 for previous, current in zip(ids, ids[1:])):
        raise EvidenceError("verified draw IDs are not contiguous")
    results = {
        result["draw_id"]: result
        for result in validation["results"]
        if isinstance(result, dict) and type(result.get("draw_id")) is int
    }
    ordered_rows: list[str] = []
    manifest_rows: list[str] = []
    chain_draws: list[dict[str, Any]] = []
    for draw_id in ids:
        captured = verified[draw_id]
        record = dict(captured)
        record["capture_draw_id"] = captured.get("draw_id")
        record["draw_id"] = draw_id
        record["draw_id_source"] = (
            captured.get("draw_id_source")
            if captured.get("draw_id") == draw_id
            else "validation"
        )
        record["order_scope"] = capture_order.ORDER_SCOPE
        balls = record.get("balls")
        if (
            not isinstance(balls, list)
            or len(balls) != 20
            or any(type(ball) is not int or not 1 <= ball <= 80 for ball in balls)
            or len(set(balls)) != 20
        ):
            raise EvidenceError(f"draw {draw_id} has an invalid ordered sequence")
        ordered_rows.append(" ".join(map(str, balls)) + "\n")
        kept = {
            key: record.get(key)
            for key in (
                "draw_id",
                "received_at",
                "received_unix_ns",
                "received_monotonic_ns",
                "session_id",
                "frame_index",
                "scene",
                "locale",
                "raw_sha256",
                "balls",
                "boost",
                "extra",
                "capture_draw_id",
                "draw_id_source",
                "order_scope",
            )
        }
        manifest_line = json.dumps(
            kept, ensure_ascii=False, sort_keys=True
        ) + "\n"
        manifest_rows.append(manifest_line)
        result = results[draw_id]
        animation = result["animation"]
        rest_http = result["rest"]["http"]
        chain_draws.append(
            {
                "draw_id": draw_id,
                "balls": list(balls),
                "capture_record_sha256": animation["capture_record_sha256"],
                "hub_message_sha256": captured["hub_message_sha256"],
                "state_canonical_sha256": captured["state_canonical_sha256"],
                "rest_body_sha256": rest_http["body_sha256"],
                "export_manifest_row_sha256": _sha256(manifest_line.encode("utf-8")),
            }
        )
    chain = {
        "draw_count": len(ids),
        "first_draw_id": ids[0],
        "last_draw_id": ids[-1],
        "next_draw_id": ids[-1] + 1,
        "contiguous_draw_ids": True,
        "order_scope": "ANIMATION_SEQUENCE_ONLY",
        "capture_records_canonical_sha256": validation[
            "capture_records_canonical_sha256"
        ],
        "draws_canonical_sha256": _canonical_sha256(chain_draws),
        "draws": chain_draws,
    }
    return (
        "".join(ordered_rows).encode("ascii"),
        "".join(manifest_rows).encode("utf-8"),
        [list(verified[draw_id]["balls"]) for draw_id in ids],
        chain,
    )


def _path_text(path: Path, directory: Path) -> str:
    relative = os.path.relpath(path.resolve(strict=True), directory.resolve())
    text = Path(relative).as_posix()
    if text in ("", ".") or "\x00" in text or PurePosixPath(text).is_absolute():
        raise EvidenceError(f"cannot encode evidence path: {path}")
    return text


def _descriptor(snapshot: Snapshot, directory: Path) -> dict[str, Any]:
    return {
        "path": _path_text(snapshot.path, directory),
        "bytes": snapshot.size,
        "sha256": snapshot.sha256,
    }


def _same_file(left: Path, right: Path) -> bool:
    try:
        if left.exists() and right.exists() and os.path.samefile(left, right):
            return True
    except OSError:
        pass
    return left.resolve(strict=False) == right.resolve(strict=False)


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    descriptor = -1
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            # A proof filename is immutable: an already published commitment may
            # refer to its existing bytes.  Hard-linking a complete temporary file
            # installs it atomically and, unlike replace(), never clobbers a target.
            os.link(temporary, path)
        except FileExistsError as exc:
            raise EvidenceError(
                f"bundle output already exists: {path}; choose a new proof filename"
            ) from exc
        temporary.unlink()
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def create_bundle(
    output: Path,
    *,
    capture: Path,
    validation: Path,
    ordered: Path,
    export_manifest: Path,
    checkpoint: Path,
    capture_implementation: Path,
    solver_implementation: Path,
) -> str:
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise EvidenceError(
            f"bundle output already exists: {output}; choose a new proof filename"
        )
    paths = {
        "capture": Path(capture),
        "validation": Path(validation),
        "ordered_dataset": Path(ordered),
        "export_manifest": Path(export_manifest),
        "checkpoint": Path(checkpoint),
    }
    implementation_paths = {
        "capture": Path(capture_implementation),
        "solver": Path(solver_implementation),
    }
    all_paths = list(paths.values()) + list(implementation_paths.values())
    for index, left in enumerate(all_paths):
        if _same_file(output, left):
            raise EvidenceError("bundle output must not alias an evidence input")
        for right in all_paths[index + 1 :]:
            if _same_file(left, right):
                raise EvidenceError(f"evidence inputs alias each other: {left} and {right}")
    snapshots = {role: _snapshot(path) for role, path in paths.items()}
    implementations = {
        role: _snapshot(path) for role, path in implementation_paths.items()
    }
    for role, snapshot in implementations.items():
        if snapshot.data != _RECOGNIZED_IMPLEMENTATIONS[role]:
            raise EvidenceError(
                f"{role} implementation differs from the code recognized by this verifier"
            )
    expected_ordered, expected_manifest, draws, chain = _expected_export(
        snapshots["capture"].data, snapshots["validation"].data
    )
    if snapshots["ordered_dataset"].data != expected_ordered:
        raise EvidenceError("ordered dataset is not the exact deterministic export")
    if snapshots["export_manifest"].data != expected_manifest:
        raise EvidenceError("export manifest is not the exact deterministic export")
    chain["checkpoint"] = _parse_checkpoint(snapshots["checkpoint"].data, draws)
    output_directory = output.parent
    bundle = {
        "schema": SCHEMA,
        "version": VERSION,
        "hash_algorithm": "SHA-256",
        "security_model": SECURITY_MODEL,
        "artifacts": {
            role: _descriptor(snapshot, output_directory)
            for role, snapshot in snapshots.items()
        },
        "implementations": {
            role: _descriptor(snapshot, output_directory)
            for role, snapshot in implementations.items()
        },
        "chain": chain,
    }
    data = _canonical_bytes(bundle) + b"\n"
    _write_atomic(output, data)
    return _sha256(data)


def _validated_descriptor(
    descriptor: Any, role: str, bundle_directory: Path
) -> Snapshot:
    descriptor = _exact_keys(descriptor, ("path", "bytes", "sha256"), role)
    raw_path = descriptor["path"]
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
        raise EvidenceError(f"{role}.path is invalid")
    pure = PurePosixPath(raw_path)
    if pure.is_absolute() or pure.as_posix() != raw_path or raw_path == ".":
        raise EvidenceError(f"{role}.path is not canonical relative POSIX")
    if type(descriptor["bytes"]) is not int or descriptor["bytes"] < 0:
        raise EvidenceError(f"{role}.bytes is invalid")
    if not isinstance(descriptor["sha256"], str) or not HEX64.fullmatch(
        descriptor["sha256"]
    ):
        raise EvidenceError(f"{role}.sha256 is not canonical lowercase SHA-256")
    snapshot = _snapshot(bundle_directory.joinpath(*pure.parts))
    if snapshot.size != descriptor["bytes"] or snapshot.sha256 != descriptor["sha256"]:
        raise EvidenceError(f"{role} size/SHA-256 mismatch")
    return snapshot


def verify_bundle(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    path = Path(path)
    bundle_snapshot = _snapshot(path)
    if expected_sha256 is not None:
        expected_sha256 = expected_sha256.lower()
        if not HEX64.fullmatch(expected_sha256):
            raise EvidenceError("expected bundle digest must be 64 hexadecimal characters")
        if bundle_snapshot.sha256 != expected_sha256:
            raise EvidenceError("bundle SHA-256 differs from the independent commitment")
    bundle = _json_value(bundle_snapshot.data, "bundle")
    if bundle_snapshot.data != _canonical_bytes(bundle) + b"\n":
        raise EvidenceError("bundle is not canonical JSON with one trailing LF")
    bundle = _exact_keys(
        bundle,
        (
            "schema",
            "version",
            "hash_algorithm",
            "security_model",
            "artifacts",
            "implementations",
            "chain",
        ),
        "bundle",
    )
    if (
        bundle["schema"] != SCHEMA
        or type(bundle["version"]) is not int
        or bundle["version"] != VERSION
        or bundle["hash_algorithm"] != "SHA-256"
        or bundle["security_model"] != SECURITY_MODEL
    ):
        raise EvidenceError("unsupported or weakened bundle schema/security model")
    artifacts = _exact_keys(
        bundle["artifacts"],
        ("capture", "validation", "ordered_dataset", "export_manifest", "checkpoint"),
        "artifacts",
    )
    implementations = _exact_keys(
        bundle["implementations"], ("capture", "solver"), "implementations"
    )
    snapshots = {
        role: _validated_descriptor(value, f"artifacts.{role}", path.parent)
        for role, value in artifacts.items()
    }
    implementation_snapshots = {
        role: _validated_descriptor(value, f"implementations.{role}", path.parent)
        for role, value in implementations.items()
    }
    for role, snapshot in implementation_snapshots.items():
        if snapshot.data != _RECOGNIZED_IMPLEMENTATIONS[role]:
            raise EvidenceError(
                f"implementations.{role} is not recognized by this verifier checkout"
            )
    all_snapshots = list(snapshots.values()) + list(implementation_snapshots.values())
    for index, left in enumerate(all_snapshots):
        for right in all_snapshots[index + 1 :]:
            if _same_file(left.path, right.path):
                raise EvidenceError("two bundle roles resolve to the same file")
    expected_ordered, expected_manifest, draws, expected_chain = _expected_export(
        snapshots["capture"].data, snapshots["validation"].data
    )
    if snapshots["ordered_dataset"].data != expected_ordered:
        raise EvidenceError("ordered dataset no longer matches the verified capture")
    if snapshots["export_manifest"].data != expected_manifest:
        raise EvidenceError("export manifest no longer matches the verified capture")
    expected_chain["checkpoint"] = _parse_checkpoint(
        snapshots["checkpoint"].data, draws
    )
    if _canonical_bytes(bundle["chain"]) != _canonical_bytes(expected_chain):
        raise EvidenceError("stored chain summary differs from full recomputation")
    return {
        "verdict": "CONSISTENT_EVIDENCE_CHAIN",
        "bundle_sha256": bundle_snapshot.sha256,
        "draw_count": expected_chain["draw_count"],
        "first_draw_id": expected_chain["first_draw_id"],
        "last_draw_id": expected_chain["last_draw_id"],
        "next_draw_id": expected_chain["next_draw_id"],
        "order_scope": expected_chain["order_scope"],
        "independent_digest_checked": expected_sha256 is not None,
    }


def _parser() -> argparse.ArgumentParser:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="create a deterministic evidence bundle")
    create.add_argument("output", type=Path)
    create.add_argument("--capture", required=True, type=Path)
    create.add_argument("--validation", required=True, type=Path)
    create.add_argument("--ordered", required=True, type=Path)
    create.add_argument("--export-manifest", required=True, type=Path)
    create.add_argument("--checkpoint", required=True, type=Path)
    create.add_argument(
        "--capture-implementation", type=Path, default=here / "capture_order.py"
    )
    create.add_argument(
        "--solver-implementation", type=Path, default=here / "keno_break.c"
    )
    verify = commands.add_parser("verify", help="strictly recompute the full chain")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--expect-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create":
            digest = create_bundle(
                args.output,
                capture=args.capture,
                validation=args.validation,
                ordered=args.ordered,
                export_manifest=args.export_manifest,
                checkpoint=args.checkpoint,
                capture_implementation=args.capture_implementation,
                solver_implementation=args.solver_implementation,
            )
            result = verify_bundle(args.output)
            if result["bundle_sha256"] != digest:
                raise EvidenceError("bundle changed immediately after creation")
            result["security_notice"] = SECURITY_MODEL["not_guaranteed"]
        else:
            result = verify_bundle(args.bundle, args.expect_sha256)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (EvidenceError, OSError) as exc:
        print(f"evidence error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
