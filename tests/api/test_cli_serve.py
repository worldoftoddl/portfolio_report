"""`portfolio-report serve` CLI 서브커맨드 테스트.

uvicorn.run은 실제 서버를 띄우므로 반드시 모킹.
"""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from portfolio_report.cli import app

runner = CliRunner()


class TestServeCommand:
    def test_default_invokes_uvicorn_with_factory(self):
        with patch("uvicorn.run") as mock_run:
            result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == "portfolio_report.api.app:create_app"
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8000
        assert kwargs["reload"] is False
        assert kwargs["factory"] is True

    def test_custom_host_port_reload(self):
        with patch("uvicorn.run") as mock_run:
            result = runner.invoke(
                app,
                ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"],
            )
        assert result.exit_code == 0, result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs["host"] == "0.0.0.0"
        assert kwargs["port"] == 9000
        assert kwargs["reload"] is True
