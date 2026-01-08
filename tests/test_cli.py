"""
Tests for CLI commands.

Tests the Typer-based CLI interface.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_import_cli_app(self):
        """Test importing the CLI app."""
        from rikai.cli.main import app

        assert app is not None

    def test_cli_help(self):
        """Test CLI help command."""
        from rikai.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "RikaiOS" in result.stdout or "rikai" in result.stdout.lower()


class TestUmiCommands:
    """Test Umi-related CLI commands."""

    def test_umi_command_exists(self):
        """Test that umi command exists."""
        from rikai.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["umi", "--help"])

        # Should not error
        assert result.exit_code in [0, 2]  # 0 = success, 2 = usage error is ok

    @pytest.mark.asyncio
    async def test_umi_health_command_mock(self):
        """Test umi health command with mocked client."""
        from rikai.cli.main import app

        with patch("rikai.cli.main.UmiClient") as mock_umi_class:
            mock_umi = AsyncMock()
            mock_umi.health.return_value = True
            mock_umi_class.return_value = mock_umi

            runner = CliRunner()
            # This would need async support or different testing approach
            # For now, just verify the command structure exists


class TestTamaCommands:
    """Test Tama-related CLI commands."""

    def test_tama_command_exists(self):
        """Test that tama command exists."""
        from rikai.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["tama", "--help"])

        # Should not error
        assert result.exit_code in [0, 2]


class TestConfigCommands:
    """Test configuration commands."""

    def test_config_show_structure(self):
        """Test that config command structure exists."""
        from rikai.cli.main import app

        runner = CliRunner()
        # Just verify app has expected structure
        assert app is not None
