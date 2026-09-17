"""Unit tests for the command-line interface."""

from unittest.mock import Mock, patch

from app.cli import main
from app.domain.exceptions import LanguageModelConfigurationError


@patch("app.cli.Settings")
@patch("app.cli.run_agent")
def test_main_prints_agent_answer(
    run_agent_mock: Mock,
    settings_mock: Mock,
    capsys,
) -> None:
    """The CLI should execute the supplied question and print the answer."""
    settings = settings_mock.return_value
    run_agent_mock.return_value = (
        "Email Loyalty generated the most purchases."
    )

    exit_code = main(
        ["Which", "campaign", "generated", "the", "most", "purchases?"]
    )

    assert exit_code == 0
    run_agent_mock.assert_called_once_with(
        "Which campaign generated the most purchases?",
        settings,
    )
    assert (
        capsys.readouterr().out
        == "Email Loyalty generated the most purchases.\n"
    )


@patch("app.cli.Settings")
@patch("app.cli.run_agent")
def test_main_reports_model_configuration_error(
    run_agent_mock: Mock,
    settings_mock: Mock,
    capsys,
) -> None:
    """The CLI should report missing or invalid model configuration."""
    run_agent_mock.side_effect = LanguageModelConfigurationError(
        "OPENROUTER_API_KEY is required."
    )

    exit_code = main(["Which", "campaign", "performed", "best?"])

    assert exit_code == 2
    assert (
        capsys.readouterr().out
        == "Configuration error: OPENROUTER_API_KEY is required.\n"
    )