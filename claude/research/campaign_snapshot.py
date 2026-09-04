#!/usr/bin/env python3
"""Create, verify, and safely restore private capture-campaign snapshots."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import capture_campaign


SCHEMA = "org.prophetofnumbers.campaign-snapshot"
VERSION = 1
MANIFEST_NAME = "_snapshot_manifest.json"
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


class SnapshotError(ValueError):
    """A campaign snapshot is unsafe, malformed, or inconsistent."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative_name(value: str) -> str:
    if not isinstance(value, str):
        raise SnapshotError("snapshot path is not a string")
    pure = PurePosixPath(value)
    if (
        not value
        or "\x00" in value
        or pure.is_absolute()
        or value != pure.as_posix()
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise SnapshotError(f"unsafe snapshot path: {value!r}")
    return value


def read_regular(path: Path) -> tuple[bytes, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SnapshotError(f"cannot open single-link regular file: {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SnapshotError(f"not a single-link regular file: {path}")
        if before.st_size > MAX_MEMBER_BYTES:
            raise SnapshotError(f"campaign file exceeds size limit: {path}")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            block = os.read(descriptor, min(1024 * 1024, remaining))
            if not block:
                raise SnapshotError(f"campaign file changed while reading: {path}")
            chunks.append(block)
            remaining -= len(block)
        if os.read(descriptor, 1):
            raise SnapshotError(f"campaign file grew while reading: {path}")
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise SnapshotError(f"campaign file changed while reading: {path}")
        return b"".join(chunks), stat.S_IMODE(before.st_mode)
    finally:
        os.close(descriptor)


def campaign_files(root: Path) -> list[tuple[str, bytes, int]]:
    files: list[tuple[str, bytes, int]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for dirname in list(dirnames):
            path = base / dirname
            if path.is_symlink():
                raise SnapshotError(f"refusing symlinked campaign directory: {path}")
        for filename in filenames:
            path = base / filename
            relative = path.relative_to(root).as_posix()
            if relative == capture_campaign.LOCK_NAME:
                continue
            if relative == MANIFEST_NAME:
                raise SnapshotError(f"reserved campaign filename exists: {relative}")
            safe_relative_name(relative)
            data, mode = read_regular(path)
            files.append((relative, data, mode))
    return sorted(files, key=lambda item: item[0])


def zip_info(name: str, mode: int = 0o600) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def create_snapshot(root: Path, output: Path) -> dict[str, Any]:
    if root.is_symlink():
        raise SnapshotError("campaign root must not be a symlink")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise SnapshotError("campaign root must be a real directory")
    if output.exists():
        raise SnapshotError("refusing to overwrite a campaign snapshot")
    try:
        output.resolve(strict=False).relative_to(root)
    except ValueError:
        pass
    else:
        raise SnapshotError("snapshot output must be outside the campaign root")
    with capture_campaign.CampaignLock(root):
        status_report = capture_campaign.status(root)
        files = campaign_files(root)
        manifest = {
            "schema": SCHEMA,
            "version": VERSION,
            "campaign_status": status_report,
            "files": [
                {"path": name, "bytes": len(data), "sha256": sha256(data), "mode": mode}
                for name, data, mode in files
            ],
        }
        manifest_data = canonical_bytes(manifest) + b"\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
        try:
            with zipfile.ZipFile(
                temporary, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as archive:
                archive.writestr(zip_info(MANIFEST_NAME), manifest_data)
                for name, data, mode in files:
                    archive.writestr(zip_info(name, mode), data)
            os.chmod(temporary, 0o600)
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            try:
                os.link(temporary, output)
            except FileExistsError as exc:
                raise SnapshotError("refusing to overwrite a campaign snapshot") from exc
            temporary.unlink()
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    verified = verify_snapshot(output)
    return {**verified, "output": str(output)}


def _manifest_from_archive(archive: zipfile.ZipFile) -> tuple[dict[str, Any], bytes]:
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise SnapshotError("snapshot contains duplicate member names")
    if MANIFEST_NAME not in names:
        raise SnapshotError("snapshot manifest is missing")
    for info in archive.infolist():
        safe_relative_name(info.filename)
        if info.is_dir() or info.file_size > MAX_MEMBER_BYTES:
            raise SnapshotError(f"invalid snapshot member: {info.filename}")
    try:
        data = archive.read(MANIFEST_NAME)
        manifest = json.loads(data)
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SnapshotError("snapshot manifest is invalid") from exc
    if not isinstance(manifest, dict) or data != canonical_bytes(manifest) + b"\n":
        raise SnapshotError("snapshot manifest is not canonical JSON")
    return manifest, data


def _verify_snapshot_bytes(
    archive_data: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(archive_data) > MAX_ARCHIVE_BYTES:
        raise SnapshotError("snapshot archive exceeds size limit")
    archive_digest = hashlib.sha256(archive_data).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_data), "r") as archive:
            manifest, _data = _manifest_from_archive(archive)
            if set(manifest) != {"schema", "version", "campaign_status", "files"}:
                raise SnapshotError("snapshot manifest fields differ from schema")
            if manifest["schema"] != SCHEMA or manifest["version"] != VERSION:
                raise SnapshotError("unsupported snapshot schema")
            rows = manifest["files"]
            if not isinstance(rows, list):
                raise SnapshotError("snapshot file table is not an array")
            expected_names = {MANIFEST_NAME}
            for row in rows:
                if not isinstance(row, dict) or set(row) != {
                    "path", "bytes", "sha256", "mode"
                }:
                    raise SnapshotError("snapshot file descriptor is malformed")
                name = safe_relative_name(row["path"])
                if name in expected_names:
                    raise SnapshotError("snapshot file table contains a duplicate path")
                if (
                    type(row["bytes"]) is not int
                    or row["bytes"] < 0
                    or type(row["mode"]) is not int
                    or not 0 <= row["mode"] <= 0o777
                    or not isinstance(row["sha256"], str)
                    or len(row["sha256"]) != 64
                    or any(character not in "0123456789abcdef" for character in row["sha256"])
                ):
                    raise SnapshotError("snapshot file descriptor values are invalid")
                data = archive.read(name)
                if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
                    raise SnapshotError(f"snapshot member hash/length mismatch: {name}")
                expected_names.add(name)
            if set(archive.namelist()) != expected_names:
                raise SnapshotError("snapshot contains an unlisted member")
    except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        raise SnapshotError(f"cannot verify snapshot: {exc}") from exc
    status_report = manifest.get("campaign_status")
    if not isinstance(status_report, dict):
        raise SnapshotError("snapshot campaign status is malformed")
    result = {
        "verdict": "VERIFIED_CAMPAIGN_SNAPSHOT",
        "archive_sha256": archive_digest,
        "files": len(rows),
        "verified_draws": status_report.get("verified_draws"),
        "journal_head_sha256": status_report.get("journal_head_sha256"),
        "manifest_head_sha256": status_report.get("manifest_head_sha256"),
    }
    return result, manifest


def verify_snapshot(path: Path) -> dict[str, Any]:
    archive_data, _mode = read_regular(path)
    result, _manifest = _verify_snapshot_bytes(archive_data)
    return result


def extract_snapshot(path: Path, destination: Path) -> dict[str, Any]:
    archive_data, _mode = read_regular(path)
    verified, verified_manifest = _verify_snapshot_bytes(archive_data)
    if destination.exists():
        raise SnapshotError("refusing to overwrite a snapshot destination")
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    temporary.mkdir(parents=True, mode=0o700)
    try:
        with zipfile.ZipFile(io.BytesIO(archive_data), "r") as archive:
            manifest, _data = _manifest_from_archive(archive)
            if manifest != verified_manifest:
                raise SnapshotError("snapshot manifest changed during extraction")
            for row in manifest["files"]:
                name = safe_relative_name(row["path"])
                target = temporary.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor = os.open(
                    target,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                )
                try:
                    data = archive.read(name)
                    view = memoryview(data)
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            raise OSError("short snapshot extraction write")
                        view = view[written:]
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        restored_status = capture_campaign.status(temporary)
        if restored_status != manifest["campaign_status"]:
            raise SnapshotError("restored campaign status differs from snapshot")
        os.rename(temporary, destination)
    except Exception:
        for root, directories, files in os.walk(temporary, topdown=False):
            for filename in files:
                (Path(root) / filename).unlink()
            for dirname in directories:
                (Path(root) / dirname).rmdir()
        try:
            temporary.rmdir()
        except FileNotFoundError:
            pass
        raise
    return {**verified, "destination": str(destination)}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("campaign", type=Path)
    create.add_argument("output", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("snapshot", type=Path)
    extract = commands.add_parser("extract")
    extract.add_argument("snapshot", type=Path)
    extract.add_argument("destination", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "create":
            result = create_snapshot(args.campaign, args.output)
        elif args.command == "verify":
            result = verify_snapshot(args.snapshot)
        else:
            result = extract_snapshot(args.snapshot, args.destination)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, SnapshotError, capture_campaign.CampaignIntegrityError) as exc:
        print(f"snapshot error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
