import pickle

from ska_helpers.utils import LazyDict


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


def test_lazy_pickle():
    x = LazyDict(load_func, 1, 2, c=3)
    xpp = pickle.loads(pickle.dumps(x))
    assert xpp == x
