from __future__ import annotations

import re
from typing import Self

from rich.style import Style
from rich.text import Text

from kubek.term.style import MessageSpec, MessageStyles


class RichTextBuilder:
    def __init__(self) -> None:
        self.__text = Text()

    def add_prefix(self, prefix: str, style: Style | str | None = None) -> Self:
        self.__text.append(prefix, style=style or "")
        return self

    def add_message(self, message: str, style: Style | str | None = None) -> Self:
        self.__text.append(message, style=style or "")
        return self

    def highlight(self, pattern: str, style: Style | str) -> Self:
        if pattern.isidentifier():
            regex = rf"\b{re.escape(pattern)}\b"
        else:
            regex = re.escape(pattern)

        self.__text.highlight_regex(regex, style or "")
        return self

    @property
    def text(self) -> Text:
        return self.__text


class MessageFormatter:
    def __init__(self, styles: MessageStyles) -> None:
        self.__styles = styles

    def note(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.info, highlight=highlight)

    def caution(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.warning, highlight=highlight)

    def problem(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.error, highlight=highlight)

    def success(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.success, highlight=highlight)

    def muted(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.muted, highlight=highlight)

    def ongoing(self, message: str, highlight: list[str] | None = None) -> Text:
        return self.format(message, spec=self.__styles.ongoing, highlight=highlight)

    @staticmethod
    def format(
        message: str,
        *,
        spec: MessageSpec,
        highlight: list[str] | None = None,
    ) -> Text:
        builder = RichTextBuilder()

        if spec.prefix:
            builder.add_prefix(spec.prefix.msg, style=spec.prefix.style)

        builder.add_message(message, style=spec.message_style)

        if highlight:
            for pattern in highlight:
                builder.highlight(pattern, style=spec.highlight_style)

        return builder.text
