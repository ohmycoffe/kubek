from export_dotenv.formatting import ExportFormat, format_environment_values


def test_json():
    vals = {"KEY1": "value1", "KEY2": "value2"}
    tested = format_environment_values(vals, name="test", output=ExportFormat.JSON)
    assert tested == '{\n  "KEY1": "value1",\n  "KEY2": "value2"\n}'


def test_dotenv():
    vals = {"KEY1": "value1", "KEY2": "value2"}
    tested = format_environment_values(values=vals, output=ExportFormat.ENV, name=None)
    assert tested == "KEY1=value1\nKEY2=value2"


def test_dotenv_includes_name_header():
    vals = {"KEY1": "value1"}
    tested = format_environment_values(
        values=vals,
        name="my-app",
        output=ExportFormat.ENV,
    )
    lines = tested.split("\n")
    assert lines[0].startswith("# my-app @ ")
    assert lines[1] == "KEY1=value1"
