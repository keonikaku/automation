"""Simulator selection rules.

These run on any machine, including the Linux CI runner, because the parsing
and selection logic is split from the ``xcrun`` call. The rules are the part
that used to be a hardcoded UDID, so they are the part worth testing.

Every UDID below is synthetic.
"""

from __future__ import annotations

import pytest

from shopsmart.ios import SimulatorNotFound, resolve_device, select_device

IOS_RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
TVOS_RUNTIME = "com.apple.CoreSimulator.SimRuntime.tvOS-26-0"


def device(name, udid, state="Shutdown", available=True):
    return {"name": name, "udid": udid, "state": state, "isAvailable": available}


def simctl(*devices, runtime=IOS_RUNTIME):
    return {"devices": {runtime: list(devices)}}


def test_prefers_the_named_device():
    payload = simctl(
        device("iPhone 17 Pro", "UDID-PRO"),
        device("iPhone 17", "UDID-17"),
    )
    assert select_device(payload, "iPhone 17")["udid"] == "UDID-17"


def test_prefers_a_booted_device_over_a_shutdown_one_of_the_same_name():
    payload = simctl(
        device("iPhone 17", "UDID-SHUTDOWN"),
        device("iPhone 17", "UDID-BOOTED", state="Booted"),
    )
    assert select_device(payload, "iPhone 17")["udid"] == "UDID-BOOTED"


def test_a_booted_device_wins_even_if_it_is_not_the_requested_model():
    """If a human already booted something, drive that rather than a cold boot."""
    payload = simctl(
        device("iPhone 17", "UDID-17"),
        device("iPhone Air", "UDID-AIR", state="Booted"),
    )
    assert select_device(payload, "iPhone 17")["udid"] == "UDID-AIR"


def test_falls_back_to_any_iphone_when_the_named_model_is_absent():
    payload = simctl(
        device("iPad Pro 13-inch (M5)", "UDID-IPAD"),
        device("iPhone 17e", "UDID-17E"),
    )
    assert select_device(payload, "iPhone 99")["udid"] == "UDID-17E"


def test_unavailable_devices_are_ignored():
    payload = simctl(
        device("iPhone 17", "UDID-BROKEN", available=False),
        device("iPhone 17e", "UDID-17E"),
    )
    assert select_device(payload, "iPhone 17")["udid"] == "UDID-17E"


def test_non_ios_runtimes_are_ignored():
    payload = simctl(device("Apple TV 4K", "UDID-TV"), runtime=TVOS_RUNTIME)
    with pytest.raises(SimulatorNotFound):
        select_device(payload, "iPhone 17")


def test_no_simulators_raises_an_actionable_error():
    with pytest.raises(SimulatorNotFound, match="IOS_UDID"):
        select_device({"devices": {}}, "iPhone 17")


def test_malformed_entries_do_not_crash_selection():
    payload = {"devices": {IOS_RUNTIME: ["not-a-dict", {"name": "no udid"}]}}
    with pytest.raises(SimulatorNotFound):
        select_device(payload, "iPhone 17")


def test_explicit_udid_short_circuits_discovery():
    """An explicit override must not shell out to xcrun at all."""

    def exploding_runner(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("xcrun should not be called when IOS_UDID is set")

    resolved = resolve_device(
        preferred_name="iPhone 17",
        explicit_udid="UDID-PINNED",
        runner=exploding_runner,
    )
    assert resolved["udid"] == "UDID-PINNED"
