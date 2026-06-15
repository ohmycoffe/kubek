from portfwd.domain.config import GroupSpec, SpecialGroups
from portfwd.presentation.prompts import ask_for_group


def test_ask_for_group_returns_custom_when_no_groups_defined():
    """Skips the prompt and uses the interactive flow when config has no groups."""
    assert ask_for_group([]) == SpecialGroups.CUSTOM


def test_ask_for_group_prompts_when_groups_exist(monkeypatch):
    """Delegates to questionary when groups are configured."""
    group = GroupSpec(name="backend", services=[])
    asked = []

    class FakeSelect:
        def __init__(self, *args, **kwargs):
            asked.append(kwargs.get("choices"))

        def ask(self):
            return group

    monkeypatch.setattr("portfwd.presentation.prompts.questionary.select", FakeSelect)

    assert ask_for_group([group]) == group
    assert asked
