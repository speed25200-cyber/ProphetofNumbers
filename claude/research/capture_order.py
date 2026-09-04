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
import hashlib
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RS = "\x1e"
NEGOTIATE_URL = (
    "https://prod.jeux-webretail.loro.ch/api/animation/"
    "negotiate?negotiateVersion=1"
)
SOURCE = "Loto Express animationhub / SendCurrentState"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


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
    scheme = "wss" if parts.scheme == "https" else "ws"
    token = urllib.parse.quote(access_token, safe="")
    query = parts.query + ("&" if parts.query else "") + "access_token=" + token
    return urllib.parse.urlunsplit(parts._replace(scheme=scheme, query=query))


async def negotiate() -> str:
    first = await asyncio.to_thread(post_json, NEGOTIATE_URL)
    azure_url = first.get("url")
    access_token = first.get("accessToken")
    if not isinstance(azure_url, str) or not isinstance(access_token, str):
        raise ValueError("first negotiation response is incomplete")
    # Azure SignalR's serverless endpoint is already a ready-to-connect client URL.
    # A second /client/negotiate round-trip produces an id that this endpoint rejects.
    return websocket_url(azure_url, access_token)


def signalr_messages(frame: str | bytes) -> Iterable[dict[str, Any]]:
    if isinstance(frame, bytes):
        frame = frame.decode("utf-8", errors="replace")
    for part in frame.split(RS):
        if not part.strip():
            continue
        try:
            value = json.loads(part)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            yield value


def locale_payload(meta: Any, preferred: str) -> tuple[str | None, dict[str, Any]]:
    if not isinstance(meta, dict):
        return None, {}
    normalized = {str(key).lower(): value for key, value in meta.items()}
    for key in (preferred.lower(), "fr-ch", "de-ch", "it-ch"):
        value = normalized.get(key)
        if isinstance(value, dict):
            return key, value
    return None, {}


def ball_value(value: Any) -> int | None:
    if isinstance(value, dict):
        for key in ("value", "number", "ball"):
            if key in value:
                return as_int(value[key])
        return None
    return as_int(value)


def extract_state(
    state: dict[str, Any], preferred_locale: str = "fr-ch", received_at: str | None = None
) -> dict[str, Any]:
    locale, localized = locale_payload(state.get("meta"), preferred_locale)
    raw_balls = localized.get("balls")
    balls = [] if not isinstance(raw_balls, list) else [ball_value(v) for v in raw_balls]
    balls = [value for value in balls if value is not None]
    canonical = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema": 1,
        "received_at": received_at or utc_now(),
        "received_unix_ns": time.time_ns(),
        "source": SOURCE,
        "scene": state.get("scene"),
        "draw_id": as_int(localized.get("id")),
        "locale": locale,
        "balls": balls,
        "boost": localized.get("boost"),
        "extra": as_int(localized.get("extra")),
        "next_draw_time": localized.get("nextDrawTime"),
        "duration": as_int(state.get("duration")),
        "start_time": as_int(state.get("startTime")),
        "end_time": as_int(state.get("endTime")),
        "progress": as_int(state.get("progress")),
        "raw_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "raw": state,
    }


def valid_full_draw(record: dict[str, Any]) -> bool:
    balls = record.get("balls")
    return (
        isinstance(record.get("draw_id"), int)
        and isinstance(balls, list)
        and len(balls) == 20
        and len(set(balls)) == 20
        and all(isinstance(value, int) and 1 <= value <= 80 for value in balls)
    )


def select_draws(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[int]]:
    selected: dict[int, dict[str, Any]] = {}
    variants: dict[int, set[tuple[int, ...]]] = {}
    for record in records:
        if not valid_full_draw(record):
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
        "first_draw_id": draws[0]["draw_id"] if draws else None,
        "last_draw_id": draws[-1]["draw_id"] if draws else None,
        "ascending_sequences": ascending,
        "descending_sequences": descending,
        "conflicting_draw_ids": conflicts,
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
            if isinstance(value, dict):
                records.append(value)
    return records


def export_order(records: list[dict[str, Any]], output: Path, allow_gaps: bool) -> dict[str, Any]:
    draws, conflicts = select_draws(records)
    if not draws:
        raise ValueError("capture contains no complete 20-ball draw")
    if conflicts:
        raise ValueError(f"conflicting sequences for draw ids: {conflicts}")
    gaps = [
        (draws[i - 1]["draw_id"], draws[i]["draw_id"])
        for i in range(1, len(draws))
        if draws[i]["draw_id"] != draws[i - 1]["draw_id"] + 1
    ]
    if gaps and not allow_gaps:
        raise ValueError(f"capture has id gaps; refusing a false-contiguous export: {gaps}")
    with output.open("w", encoding="utf-8") as handle:
        for record in draws:
            handle.write(" ".join(map(str, record["balls"])) + "\n")
    manifest = output.with_suffix(output.suffix + ".manifest.jsonl")
    with manifest.open("w", encoding="utf-8") as handle:
        for record in draws:
            kept = {key: record.get(key) for key in (
                "draw_id", "received_at", "scene", "locale", "raw_sha256", "balls",
                "boost", "extra",
            )}
            handle.write(json.dumps(kept, ensure_ascii=False, sort_keys=True) + "\n")
    return {"draws": len(draws), "gaps": gaps, "output": str(output), "manifest": str(manifest)}


async def capture(output: Path, locale: str, duration: float, max_events: int) -> int:
    import websockets

    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = math.inf if duration <= 0 else time.monotonic() + duration
    written = 0
    invocation = 0
    delay = 1.0
    with output.open("a", encoding="utf-8", buffering=1) as handle:
        while time.monotonic() < deadline and (max_events <= 0 or written < max_events):
            try:
                url = await negotiate()
                async with websockets.connect(
                    url, open_timeout=25, close_timeout=5, ping_interval=15, ping_timeout=20
                ) as socket:
                    await socket.send(json.dumps({"protocol": "json", "version": 1}) + RS)
                    delay = 1.0
                    while time.monotonic() < deadline and (max_events <= 0 or written < max_events):
                        timeout = 30.0 if deadline == math.inf else max(0.1, min(30.0, deadline - time.monotonic()))
                        frame = await asyncio.wait_for(socket.recv(), timeout=timeout)
                        for message in signalr_messages(frame):
                            if not message:
                                invocation += 1
                                await socket.send(json.dumps({
                                    "type": 1,
                                    "invocationId": str(invocation),
                                    "target": "ConnectLoop",
                                    "arguments": ["ONLINE"],
                                }) + RS)
                            elif message.get("type") == 6:
                                await socket.send(json.dumps({"type": 6}) + RS)
                            elif message.get("target") == "SendCurrentState":
                                arguments = message.get("arguments")
                                if not isinstance(arguments, list) or not arguments or not isinstance(arguments[0], dict):
                                    continue
                                record = extract_state(arguments[0], locale)
                                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                                handle.flush()
                                os.fsync(handle.fileno())
                                written += 1
                                print(
                                    f"{record['received_at']} scene={record['scene']} "
                                    f"id={record['draw_id']} balls={len(record['balls'])} "
                                    f"sha256={record['raw_sha256'][:12]}",
                                    flush=True,
                                )
            except asyncio.TimeoutError:
                if time.monotonic() >= deadline:
                    break
            except KeyboardInterrupt:
                break
            except Exception as exc:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
                suffix = "" if status is None else f" HTTP {status}"
                print(f"capture reconnect after {type(exc).__name__}{suffix}", file=sys.stderr, flush=True)
                await asyncio.sleep(min(delay, max(0.0, deadline - time.monotonic())))
                delay = min(15.0, delay * 2)
    return written


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    live = commands.add_parser("capture", help="append raw SignalR states to JSONL")
    live.add_argument("output", type=Path)
    live.add_argument("--locale", default="fr-ch")
    live.add_argument("--duration", type=float, default=0, help="seconds; 0 runs until interrupted")
    live.add_argument("--max-events", type=int, default=0, help="0 means unlimited")
    inspect = commands.add_parser("inspect", help="audit an existing capture")
    inspect.add_argument("input", type=Path)
    export = commands.add_parser("export", help="write chronological input for keno_break")
    export.add_argument("input", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--allow-gaps", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "capture":
            count = asyncio.run(capture(args.output, args.locale, args.duration, args.max_events))
            print(f"recorded {count} state event(s) in {args.output}")
        elif args.command == "inspect":
            print(json.dumps(analyze(read_jsonl(args.input)), indent=2, ensure_ascii=False))
        else:
            print(json.dumps(
                export_order(read_jsonl(args.input), args.output, args.allow_gaps),
                indent=2,
                ensure_ascii=False,
            ))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
