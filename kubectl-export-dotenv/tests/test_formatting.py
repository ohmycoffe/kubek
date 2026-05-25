from export_dotenv.formatting import ExportFormat, format_environment_values


def test_json():
    vals = {"KEY1": "value1", "KEY2": "value2"}
    tested = format_environment_values(vals, name="test", output=ExportFormat.JSON)
    assert tested == '{\n  "KEY1": "value1",\n  "KEY2": "value2"\n}'


def test_dotenv():
    vals = {"KEY1": "value1", "KEY2": "value2"}
    tested = format_environment_values(values=vals, output=ExportFormat.ENV, name=None)
    assert tested == "KEY1=value1\nKEY2=value2"
