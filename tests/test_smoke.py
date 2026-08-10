from typer.testing import CliRunner

from local_document_converter import __version__
from local_document_converter.cli import app


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_help_command_is_available() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Convert local documents through DocumentIR" in result.stdout


def test_formats_command_lists_contract() -> None:
    result = CliRunner().invoke(app, ["formats"])

    assert result.exit_code == 0
    assert ".pdf" in result.stdout
    assert ".xlsx" in result.stdout
    assert "markdown" in result.stdout
    assert "docx" in result.stdout
    assert "json" in result.stdout
