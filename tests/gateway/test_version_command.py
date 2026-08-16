"""Tests for gateway /version command."""

import asyncio

from jacky_cli.banner import format_banner_version_label


def test_gateway_version_command_returns_release_line():
    from gateway.run import GatewayRunner

    result = asyncio.run(GatewayRunner._handle_version_command(None, None))  # type: ignore[arg-type]
    assert result == format_banner_version_label()
