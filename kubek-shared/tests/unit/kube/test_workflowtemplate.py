import pytest
from kubek.kube.dto.workflowtemplate.template import (
    ContainerTemplate,
    DagTemplate,
    ScriptTemplate,
    StepsTemplate,
)
from kubek.kube.dto.workflowtemplate.workflowtemplate import parse_template


def test_parse_template_returns_existing_instance():
    template = DagTemplate(name="main")

    assert parse_template(template) is template


@pytest.mark.parametrize(
    "data,expected_type",
    [
        ({"dag": {}, "name": "dag-step"}, DagTemplate),
        ({"steps": [], "name": "steps-step"}, StepsTemplate),
        ({"script": {}, "name": "script-step"}, ScriptTemplate),
        (
            {
                "container": {"name": "busybox", "image": "busybox"},
                "name": "container-step",
            },
            ContainerTemplate,
        ),
    ],
)
def test_parse_template_parses_single_template_type(data, expected_type):
    result = parse_template(data)

    assert isinstance(result, expected_type)
    assert result.name == data["name"]


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"dag": {}, "steps": [], "name": "ambiguous"},
    ],
)
def test_parse_template_raises_for_invalid_shape(data):
    with pytest.raises(ValueError):
        parse_template(data)


def test_parse_template_defaults_unnamed_container_to_main():
    """Argo makes ``container.name`` optional and runs it as the ``main`` container."""
    result = parse_template(
        {
            "container": {"image": "busybox", "command": ["echo", "hi"]},
            "name": "container-step",
        }
    )

    assert isinstance(result, ContainerTemplate)
    assert result.container.name == "main"


def test_parse_template_keeps_explicit_container_name():
    result = parse_template(
        {
            "container": {"name": "busybox", "image": "busybox"},
            "name": "container-step",
        }
    )

    assert isinstance(result, ContainerTemplate)
    assert result.container.name == "busybox"
