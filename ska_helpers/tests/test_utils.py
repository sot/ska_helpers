import pickle
import time

from ska_helpers.utils import LazyDict, LazyVal, lru_cache_timed


def load_func(a, b, c=None):
    return {'a': a, 'b': b, 'c': c}


def test_lazy_dict_basic():
    x = LazyDict(load_func, 1, 2, c=3)
    assert 'a' in x
    assert 'b' in x
    assert 'c' in x

    x = LazyDict(load_func, 1, 2, c=3)
    assert x == {'a': 1, 'b': 2, 'c': 3}

    x = LazyDict(load_func, 1, 2, c=3)
    assert len(x) == 3

    x = LazyDict(load_func, 1, 2, c=3)
    assert list(x) == ['a', 'b', 'c']

    x = LazyDict(load_func, 1, 2, c=3)
    assert list(x.values()) == [1, 2, 3]


def test_lazy_dict_pickle():
    x = LazyDict(load_func, 1, 2, c=3)
    xpp = pickle.loads(pickle.dumps(x))
    assert xpp == x


def test_lazy_val():
    x = LazyVal(load_func, 1, 2, c=3)
    xd = x.val
    assert xd == {'a': 1, 'b': 2, 'c': 3}


def test_lazy_val_pickle():
    x = LazyVal(load_func, 1, 2, c=3)
    xpp = pickle.loads(pickle.dumps(x))
    assert xpp.val == {'a': 1, 'b': 2, 'c': 3}


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
