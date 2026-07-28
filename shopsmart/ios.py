"""iOS Simulator discovery for the native Appium test.

The native test used to carry a hardcoded UDID, which meant it only ran on the
one Mac that UDID belonged to. Simulator UDIDs are generated per machine, so a
literal in the source is a guarantee the test is unrunnable by anyone else.

Discovery order, most specific first:

1. ``IOS_UDID`` — an explicit override, for when you know exactly which
   simulator you want.
2. A **booted** simulator matching the requested model name. If a human has
   already booted the device they want to watch, use it.
3. Any booted iOS simulator.
4. An **available** simulator matching the requested model name.
5. Any available iPhone.

Parsing is split from the ``xcrun`` call so the selection rules can be
unit-tested without a Mac, which is what lets them run in CI.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any


class SimulatorNotFound(RuntimeError):
    """No usable iOS Simulator could be discovered."""


def _ios_runtimes(devices: Mapping[str, Any]) -> Sequence[tuple[str, list[dict]]]:
    """Runtime identifier / device-list pairs, iOS runtimes only."""
    return [
        (runtime, entries)
        for runtime, entries in devices.items()
        if "iOS" in runtime and isinstance(entries, list)
    ]


def _candidates(simctl_json: Mapping[str, Any]) -> list[dict]:
    """Flatten ``simctl`` output to a list of available iOS devices."""
    devices = simctl_json.get("devices") or {}
    flat: list[dict] = []
    for runtime, entries in _ios_runtimes(devices):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("isAvailable") is False:
                continue
            if not entry.get("udid"):
                continue
            flat.append({**entry, "runtime": runtime})
    return flat


def select_device(
    simctl_json: Mapping[str, Any],
    preferred_name: str | None = None,
) -> dict:
    """Choose one simulator from parsed ``xcrun simctl list devices --json``.

    Returns the raw device dict (it carries ``udid``, ``name`` and ``state``)
    so callers can log exactly which machine-local device was picked.
    """
    devices = _candidates(simctl_json)
    if not devices:
        raise SimulatorNotFound(
            "No available iOS Simulator found. Install one via Xcode > Settings > "
            "Components, or set IOS_UDID to a specific device."
        )

    def named(pool: list[dict]) -> list[dict]:
        if not preferred_name:
            return []
        return [d for d in pool if d.get("name") == preferred_name]

    booted = [d for d in devices if d.get("state") == "Booted"]
    iphones = [d for d in devices if str(d.get("name", "")).startswith("iPhone")]

    for pool in (named(booted), booted, named(devices), iphones, devices):
        if pool:
            return pool[0]

    raise SimulatorNotFound("No available iOS Simulator found.")


def list_devices_json(runner=subprocess.run) -> dict:
    """Shell out to ``xcrun simctl`` and parse its JSON output."""
    try:
        completed = runner(
            ["xcrun", "simctl", "list", "devices", "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except FileNotFoundError as exc:  # pragma: no cover - needs a non-Mac host
        raise SimulatorNotFound(
            "xcrun is not available. The native iOS test requires macOS with Xcode."
        ) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover - needs a broken Xcode
        raise SimulatorNotFound(f"xcrun simctl failed: {exc.stderr}") from exc

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - needs a broken Xcode
        raise SimulatorNotFound("Could not parse xcrun simctl output.") from exc


def resolve_device(
    preferred_name: str | None = None,
    explicit_udid: str | None = None,
    runner=subprocess.run,
) -> dict:
    """Resolve the simulator the native test should drive."""
    if explicit_udid:
        return {"udid": explicit_udid, "name": preferred_name or "", "state": "unknown"}
    return select_device(list_devices_json(runner=runner), preferred_name)
