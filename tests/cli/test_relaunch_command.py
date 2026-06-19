"""Tests for the /relaunch slash command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from cli import HermesCLI


def test_relaunch_command_registered_cli_only():
    from hermes_cli.commands import COMMAND_REGISTRY

    cmd = next(c for c in COMMAND_REGISTRY if c.name == "relaunch")
    assert cmd.cli_only is True
    assert cmd.gateway_only is False


def test_relaunch_handler_sets_resume_args_and_preserves_inherited_flags(capsys):
    self_ = SimpleNamespace(
        session_id="20260414_220000_abc123",
        _pending_relaunch=None,
        _pending_relaunch_preserve_inherited=False,
    )

    result = HermesCLI._handle_relaunch_command(self_)

    assert result is True
    assert self_._pending_relaunch == ["--resume", "20260414_220000_abc123"]
    assert self_._pending_relaunch_preserve_inherited is True
    assert "Relaunching Hermes" in capsys.readouterr().out


def test_relaunch_handler_allows_no_session_id():
    self_ = SimpleNamespace(
        session_id=None,
        _pending_relaunch=None,
        _pending_relaunch_preserve_inherited=False,
    )

    result = HermesCLI._handle_relaunch_command(self_)

    assert result is True
    assert self_._pending_relaunch == []
    assert self_._pending_relaunch_preserve_inherited is True


def test_process_command_relaunch_requests_exit():
    cli = HermesCLI.__new__(HermesCLI)
    cli._pending_resume_sessions = None
    cli.session_id = "sess-1"
    cli._pending_relaunch = None
    cli._pending_relaunch_preserve_inherited = False

    assert cli.process_command("/relaunch") is False
    assert cli._pending_relaunch == ["--resume", "sess-1"]
    assert cli._pending_relaunch_preserve_inherited is True


def test_deferred_relaunch_uses_preserve_flag(monkeypatch):
    cli = HermesCLI.__new__(HermesCLI)
    cli._pending_relaunch = ["--resume", "sess-1"]
    cli._pending_relaunch_preserve_inherited = True
    calls = []

    def fake_relaunch(args, *, preserve_inherited):
        calls.append((args, preserve_inherited))
        raise SystemExit(0)

    monkeypatch.setattr("hermes_cli.relaunch.relaunch", fake_relaunch)

    # Exercise the same condition/dispatch used at the end of HermesCLI.run()
    # without starting prompt_toolkit.
    if getattr(cli, "_pending_relaunch", None) is not None:
        from hermes_cli.relaunch import relaunch

        try:
            relaunch(
                cli._pending_relaunch,
                preserve_inherited=getattr(cli, "_pending_relaunch_preserve_inherited", False),
            )
        except SystemExit:
            pass

    assert calls == [(["--resume", "sess-1"], True)]


def test_update_relaunch_still_disables_inherited_flags():
    self_ = SimpleNamespace(
        _app=None,
        _pending_relaunch=None,
        _pending_relaunch_preserve_inherited=True,
        _prompt_text_input_modal=lambda **_kw: "yes",
    )
    self_._normalize_slash_confirm_choice = HermesCLI._normalize_slash_confirm_choice.__get__(self_, type(self_))

    with patch("hermes_cli.config.is_managed", return_value=False):
        result = HermesCLI._handle_update_command(self_)

    assert result is True
    assert self_._pending_relaunch == ["update"]
    assert self_._pending_relaunch_preserve_inherited is False
