from export_dotenv.formatting import ExportFormat, format_environment_values
from export_dotenv.kube.env_fetchers import EnvironmentValues


def test_json():
    vals = [
        EnvironmentValues(
            name="app",
            values={"KEY1": "value1", "KEY2": "value2"},
        )
    ]
    tested = format_environment_values(vals, name="test", output=ExportFormat.JSON)
    assert tested == (
        "[\n"
        "  {\n"
        '    "name": "app",\n'
        '    "values": {\n'
        '      "KEY1": "value1",\n'
        '      "KEY2": "value2"\n'
        "    }\n"
        "  }\n"
        "]"
    )


def test_dotenv():
    vals = [EnvironmentValues(name="app", values={"KEY1": "value1", "KEY2": "value2"})]
    tested = format_environment_values(values=vals, output=ExportFormat.ENV, name=None)
    assert tested == "KEY1=value1\nKEY2=value2"


def test_dotenv_includes_name_header():
    vals = [EnvironmentValues(name="app", values={"KEY1": "value1"})]
    tested = format_environment_values(
        values=vals,
        name="my-app",
        output=ExportFormat.ENV,
    )
    lines = tested.split("\n")
    assert lines[0].startswith("# my-app @ ")
    assert lines[1] == "KEY1=value1"


def test_dotenv_multi_container_includes_container_headers():
    vals = [
        EnvironmentValues(name="app", values={"KEY1": "value1"}),
        EnvironmentValues(name="sidecar", values={"KEY2": "value2"}),
    ]
    tested = format_environment_values(values=vals, output=ExportFormat.ENV, name=None)
    assert tested.split("\n") == [
        "# container: app",
        "KEY1=value1",
        "# container: sidecar",
        "KEY2=value2",
    ]
