from dataclasses import dataclass

import pytest
from kubek.kube._infrastructure.client import as_dict


async def test_converts_response_to_dict():
    @as_dict
    async def fn():
        @dataclass
        class FakeResponse:
            foo: str

            def to_dict(self):
                return {"foo": self.foo}

        return FakeResponse(foo="bar")

    assert await fn() == {"foo": "bar"}


async def test_as_dict_passes_through_plain_dict():
    @as_dict
    async def fn():
        return {"already": "a dict"}

    assert await fn() == {"already": "a dict"}


async def test_as_dict_raises_type_error_for_unsupported_type():
    @as_dict
    async def fn():
        return "not a dict"

    with pytest.raises(
        TypeError, match="Expected dict-like response, got <class 'str'>"
    ):
        await fn()
