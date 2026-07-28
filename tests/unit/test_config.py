"""Settings resolution. Deterministic: no network, no browser, no os.environ."""

from __future__ import annotations

import pytest

from shopsmart.config import BASE_URL, Settings, as_bool, load_settings


def test_default_is_headless():
    """The default must be headless — CI has no display server."""
    assert load_settings(env={}).headless is True


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_headed_env_var_turns_the_browser_on(value):
    assert load_settings(env={"HEADED": value}).headless is False


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_falsey_headed_values_stay_headless(value):
    assert load_settings(env={"HEADED": value}).headless is True


def test_headed_flag_wins_over_the_environment():
    """An explicit --headed beats a stale exported variable."""
    assert load_settings(env={"HEADED": "0"}, headed=True).headless is False


def test_unparseable_env_value_falls_back_to_the_default():
    """A typo in a shell must not fail a run in a way that looks like a defect."""
    assert as_bool("maybe", default=True) is True
    assert as_bool("maybe", default=False) is False
    assert as_bool(None, default=True) is True


def test_video_recording_is_on_by_default_and_can_be_disabled():
    assert load_settings(env={}).record_video is True
    assert load_settings(env={"RECORD_VIDEO": "0"}).record_video is False


def test_slow_mo_defaults_to_zero_and_rejects_nonsense():
    assert load_settings(env={}).slow_mo == 0
    assert load_settings(env={"SLOW_MO": "250"}).slow_mo == 250
    assert load_settings(env={"SLOW_MO": "not-a-number"}).slow_mo == 0
    assert load_settings(env={"SLOW_MO": "-50"}).slow_mo == 0


def test_base_url_default_and_override():
    assert load_settings(env={}).base_url == BASE_URL
    assert load_settings(env={"SHOPSMART_BASE_URL": "https://staging.test"}).base_url == (
        "https://staging.test"
    )


def test_url_composition():
    assert Settings(base_url="https://example.test").url("/login") == (
        "https://example.test/login"
    )


def test_ios_udid_is_not_hardcoded_but_can_be_pinned():
    """No UDID by default — it is discovered per machine. Override is opt-in."""
    assert load_settings(env={}).ios_udid is None
    assert load_settings(env={"IOS_UDID": "ABC-123"}).ios_udid == "ABC-123"


def test_no_credential_is_read_from_the_environment():
    """The suite registers the accounts it needs; there is no secret to supply."""
    hostile = {
        "SHOPSMART_EMAIL": "someone@example.com",
        "SHOPSMART_PASSWORD": "hunter2",
    }
    settings = load_settings(env=hostile)
    assert "hunter2" not in repr(settings)
    assert "someone@example.com" not in repr(settings)
