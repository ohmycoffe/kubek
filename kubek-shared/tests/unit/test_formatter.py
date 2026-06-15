from kubek.term.formatter import MessageFormatter, RichTextBuilder
from kubek.term.style import DEFAULT_MESSAGE_STYLES


def test_highlight_uses_word_boundary_for_identifiers():
    builder = RichTextBuilder().add_message("connect to my-service now")

    builder.highlight("my-service", style="bold")

    assert "my-service" in builder.text.plain


def test_highlight_matches_literal_pattern_for_non_identifiers():
    builder = RichTextBuilder().add_message("value is 8080/tcp")

    builder.highlight("8080/tcp", style="bold")

    assert "8080/tcp" in builder.text.plain


def test_format_applies_highlights():
    formatter = MessageFormatter(styles=DEFAULT_MESSAGE_STYLES)

    text = formatter.note("hello world", highlight=["world"])

    assert "hello world" in text.plain


def test_ongoing_uses_ongoing_style():
    formatter = MessageFormatter(styles=DEFAULT_MESSAGE_STYLES)

    text = formatter.ongoing("working")

    assert "working" in text.plain
