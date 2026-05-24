from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from kubek.kube._infrastructure.client import as_dict


def test_converts_response_to_dict():
    response = MagicMock()
    response.to_dict.return_value = {"items": []}

    @as_dict
    def fn():
        @dataclass
        class FakeResponse:
            foo: str

            def to_dict(self):
                return {"foo": self.foo}

        return FakeResponse(foo="bar")

    assert fn() == {"foo": "bar"}


def test_as_dict_passes_through_plain_dict():
    @as_dict
    def fn():
        return {"already": "a dict"}

    assert fn() == {"already": "a dict"}


def test_as_dict_raises_type_error_for_unsupported_type():
    @as_dict
    def fn():
        return "not a dict"

    with pytest.raises(
        TypeError, match="Expected dict-like response, got <class 'str'>"
    ):
        fn()
