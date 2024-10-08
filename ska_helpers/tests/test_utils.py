import functools
import logging
import os
import pickle
import time
from dataclasses import dataclass

import agasc
import numpy as np
import pytest

import ska_helpers.logging
from ska_helpers.utils import (
    LazyDict,
    LazyVal,
    LRUDict,
    TypedDescriptor,
    convert_to_int_float_str,
    lru_cache_timed,
    random_radec_in_cone,
    set_log_level,
    temp_env_var,
)


def load_func(a, b, c=None):
    return {"a": a, "b": b, "c": c}


def test_lazy_dict_basic():
    x = LazyDict(load_func, 1, 2, c=3)
    assert "a" in x
    assert "b" in x
    assert "c" in x

    x = LazyDict(load_func, 1, 2, c=3)
    assert x == {"a": 1, "b": 2, "c": 3}

    x = LazyDict(load_func, 1, 2, c=3)
    assert len(x) == 3

    x = LazyDict(load_func, 1, 2, c=3)
    assert list(x) == ["a", "b", "c"]

    x = LazyDict(load_func, 1, 2, c=3)
    assert list(x.values()) == [1, 2, 3]


def test_lazy_dict_pickle():
    x = LazyDict(load_func, 1, 2, c=3)
    xpp = pickle.loads(pickle.dumps(x))
    assert xpp == x


def test_lazy_val():
    x = LazyVal(load_func, 1, 2, c=3)
    xd = x.val
    assert xd == {"a": 1, "b": 2, "c": 3}


def test_lazy_val_pickle():
    x = LazyVal(load_func, 1, 2, c=3)
    xpp = pickle.loads(pickle.dumps(x))
    assert xpp.val == {"a": 1, "b": 2, "c": 3}


def test_lru_cache_timed():
    @lru_cache_timed(maxsize=128, timeout=0.1)
    def test(a):
        return a + 1

    assert test.cache_info().currsize == 0
    test(1)
    assert test.cache_info().currsize == 1
    time.sleep(0.11)
    assert test.cache_info().currsize == 0
    test(1)
    assert test.cache_info().currsize == 1
    time.sleep(0.11)
    test(1)
    test(2)
    assert test.cache_info().currsize == 2
    time.sleep(0.11)
    assert test.cache_info().currsize == 0


def test_lru_dict():
    # Create an LRUDict with capacity 2
    d = LRUDict(2)

    # Add two items to the dict
    d["a"] = 1
    d["b"] = 2

    # Access the items in order
    assert d["a"] == 1
    assert d["b"] == 2

    # Add a third item to the dict
    d["c"] = 3

    # The oldest item ("a") should have been evicted
    with pytest.raises(KeyError):
        d["a"]

    # Access the remaining items in order
    assert d["b"] == 2
    assert d["c"] == 3

    # Access the items in reverse order
    assert d["c"] == 3
    assert d["b"] == 2

    # Add a fourth item to the dict
    d["d"] = 4

    # The oldest item ("c") should have been evicted
    with pytest.raises(KeyError):
        d["c"]

    # Access the remaining items in order
    assert d["b"] == 2
    assert d["d"] == 4


def test_temp_env_var():
    name = "ASDF1234_asdfsdaf_982398239324223423_a2323423424211111_adfaASDfaSDFASDF"
    # Check that the environment variable is initially unset
    assert os.environ.get(name) is None

    # Set the environment variable using the context manager
    with temp_env_var(name, "my_value"):
        assert os.environ.get(name) == "my_value"

    # Check that the environment variable is unset after the context manager exits
    assert os.environ.get(name) is None


cases = [
    (" 1 ", int, 1),
    ("1e5", float, 1e5),
    (" 01.01e5 ", float, 1.01e5),
    ("1.0a5", str, "1.0a5"),
    ("0472", int, 472),
    ("-0472", int, -472),
    (" 'test string' ", str, "test string"),
    (' "test string" ', str, "test string"),
    (" test string", str, " test string"),
    ("[1, 2, 3]", str, "[1, 2, 3]"),
]


@pytest.mark.parametrize("value, type_, expected", cases)
def test_convert_to_int_float_str(value, type_, expected):
    out = convert_to_int_float_str(value)
    assert out == expected
    assert type(out) is type_  # noqa: E721


def test_convert_to_int_float_str_err():
    with pytest.raises(TypeError, match="input value must be a string, not float"):
        convert_to_int_float_str(1.05)


class IntDescriptor(TypedDescriptor):
    cls = int


IntDescriptorFromKwargs = functools.partial(TypedDescriptor, cls=int)


@pytest.mark.parametrize("cls_descriptor", [IntDescriptor, IntDescriptorFromKwargs])
def test_int_descriptor_not_required_no_default(cls_descriptor):
    @dataclass
    class MyClass:
        val_int: int | None = cls_descriptor()

    obj = MyClass()
    assert obj.val_int is None

    obj = MyClass(val_int=10.2)
    assert isinstance(obj.val_int, int)
    assert obj.val_int == 10


@pytest.mark.parametrize("cls_descriptor", [IntDescriptor, IntDescriptorFromKwargs])
def test_int_descriptor_is_required(cls_descriptor):
    @dataclass
    class MyClass:
        val_int: int = cls_descriptor(required=True)

    obj = MyClass(10.2)
    assert obj.val_int == 10

    with pytest.raises(
        ValueError, match="attribute 'val_int' is required and cannot be set to None"
    ):
        obj.val_int = None

    with pytest.raises(
        ValueError, match="attribute 'val_int' is required and cannot be set to None"
    ):
        MyClass()


@pytest.mark.parametrize("cls_descriptor", [IntDescriptor, IntDescriptorFromKwargs])
def test_int_descriptor_has_default(cls_descriptor):
    @dataclass
    class MyClass:
        val_int: int = cls_descriptor(default=10.5)

    # Accessing the class attribute returns original default value (used by dataclass).
    assert MyClass.val_int == 10.5

    obj = MyClass()
    # Default of 10.5 is cast to int
    assert obj.val_int == 10

    obj = MyClass(val_int=3.5)
    assert obj.val_int == 3


@pytest.mark.parametrize("cls_descriptor", [IntDescriptor, IntDescriptorFromKwargs])
def test_int_descriptor_is_required_has_default_exception(cls_descriptor):
    with pytest.raises(
        ValueError, match="cannot set both 'required' and 'default' arguments"
    ):

        @dataclass
        class MyClass:
            quat: int = cls_descriptor(default=30, required=True)


def test_set_log_level():
    logger = ska_helpers.logging.basic_logger("test_utils", level="DEBUG")

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    for hdlr in logger.handlers:
        assert hdlr.level == 0

    with set_log_level(logger, "INFO"):
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        for hdlr in logger.handlers:
            assert hdlr.level == logging.INFO

    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 1
    for hdlr in logger.handlers:
        assert hdlr.level == 0


def test_random_radec_in_cone_scalar():
    np.random.seed(0)
    ra, dec = random_radec_in_cone(10, 20, angle=5)
    assert np.isclose(ra, 8.6733489)
    assert np.isclose(dec, 15.964518)


def test_random_radec_in_cone_size_values():
    np.random.seed(0)
    ra, dec = random_radec_in_cone(10, 20, angle=5, size=2)
    assert np.allclose(ra, [8.77992603, 6.18623754])
    assert np.allclose(dec, [16.29571322, 19.15880785])


def test_random_radec_in_cone_size_angle():
    np.random.seed(0)
    ra, dec = random_radec_in_cone(10, 20, angle=5, size=10000)
    assert np.all(agasc.sphere_dist(ra, dec, 10, 20) < 5)
