from unittest.mock import patch

from portfwd.domain.models import TargetKind
from portfwd.presentation.prompts import ask_for_kinds


@patch("portfwd.presentation.prompts.questionary.checkbox")
def test_ask_for_kinds_offers_both_kinds_prechecked(mock_checkbox):
    """Both kinds are offered as pre-checked choices."""
    mock_checkbox.return_value.ask.return_value = [TargetKind.POD, TargetKind.SERVICE]

    result = ask_for_kinds()

    assert result == [TargetKind.POD, TargetKind.SERVICE]
    choices = mock_checkbox.call_args.kwargs["choices"]
    assert {c.value for c in choices} == {TargetKind.POD, TargetKind.SERVICE}
    assert all(c.checked for c in choices)
    assert mock_checkbox.call_args.kwargs["initial_choice"] == TargetKind.SERVICE
    assert [c.value for c in choices] == [TargetKind.SERVICE, TargetKind.POD]


@patch("portfwd.presentation.prompts.questionary.checkbox")
def test_ask_for_kinds_returns_user_subset(mock_checkbox):
    """Only the kinds the user keeps checked are returned."""
    mock_checkbox.return_value.ask.return_value = [TargetKind.POD]

    assert ask_for_kinds() == [TargetKind.POD]
