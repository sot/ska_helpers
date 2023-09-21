# Licensed under a 3-clause BSD style license - see LICENSE.rst

import contextlib
import functools
import os
from collections import OrderedDict

__all__ = [
    "LazyDict",
    "LazyVal",
    "LRUDict",
    "lru_cache_timed",
    "temp_env_var",
    "convert_to_int_float_str",
]


def get_owner(path):
    """
    Returns the owner of a file or directory.

    Parameters:
    -----------
    path : str or pathlib.Path
        The path to the file or directory.

    Returns:
    --------
    str
        The name of the owner of the file or directory.
    """

    from pathlib import Path

    from testr import test_helper

    if test_helper.is_windows():
        import win32security

        # Suggested by copilot chat, seems to
        security_descriptor = win32security.GetFileSecurity(
            str(path), win32security.OWNER_SECURITY_INFORMATION
        )
        owner_sid = security_descriptor.GetSecurityDescriptorOwner()
        owner_name, _, _ = win32security.LookupAccountSid(None, owner_sid)
    else:
        owner_name = Path(path).owner()
    return owner_name


def _lazy_load_wrap(unbound_method):
    @functools.wraps(unbound_method)
    def wrapper(self, *args, **kwargs):
        self._load()
        return unbound_method(self, *args, **kwargs)

    return wrapper


class LazyVal:
    """Value which is lazy-initialized using supplied function ``load_func``.

    This class allows defining a module-level value that is expensive to
    initialize, where the initialization is done lazily (only when actually
    needed).

    The lazy value is accessed using the ``val`` property.

    Examples
    --------
    ::

      from ska_helpers.utils import LazyVal

      def load_func(a):
          # Some expensive function in practice
          print('Here in load_func')
          return a

      ONE = LazyVal(load_func, 1)

      print('ONE is defined but not yet loaded')
      print(ONE.val)

    Parameters
    ----------
    load_func : function
        Reference to a function that returns a dict to init this dict object
    *args
        Arguments list for ``load_func``
    **kwargs
        Keyword arguments for ``load_func``
    """

    def __init__(self, load_func, *args, **kwargs):
        self._load_func = load_func
        self._args = args
        self._kwargs = kwargs
        super().__init__()

    @property
    def val(self):
        if not hasattr(self, "_val"):
            self._val = self._load_func(*self._args, **self._kwargs)

            # Delete these so serialization always works (pickling a func can fail)
            del self._load_func
            del self._args
            del self._kwargs

        return self._val


class LazyDict(dict):
    """Dict which is lazy-initialized using supplied function ``load_func``.

    This class allows defining a module-level dict that is expensive to
    initialize, where the initialization is done lazily (only when actually
    needed).

    Examples
    --------
    ::

      from ska_helpers.utils import LazyDict

      def load_func(a, b):
          # Some expensive function in practice
          print('Here in load_func')
          return {'a': a, 'b': b}

      ONE = LazyDict(load_func, 1, 2)

      print('ONE is defined but not yet loaded')
      print(ONE['a'])

    Parameters
    ----------
    load_func : function
        Reference to a function that returns a dict to init this dict object
    *args
        Arguments list for ``load_func``
    **kwargs
        Keyword arguments for ``load_func``
    """

    def __init__(self, load_func, *args, **kwargs):
        self._load_func = load_func
        self._args = args
        self._kwargs = kwargs
        self._loaded = False
        super().__init__()

    def _load(self):
        if not self._loaded:
            self.update(self._load_func(*self._args, **self._kwargs))
            self._loaded = True

            # Delete these so serialization always works (pickling a func can fail)
            del self._load_func
            del self._args
            del self._kwargs

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            self._load()
            return super().__getitem__(item)

    __contains__ = _lazy_load_wrap(dict.__contains__)
    __eq__ = _lazy_load_wrap(dict.__eq__)
    __ge__ = _lazy_load_wrap(dict.__ge__)
    __gt__ = _lazy_load_wrap(dict.__gt__)
    __iter__ = _lazy_load_wrap(dict.__iter__)
    __le__ = _lazy_load_wrap(dict.__le__)
    __len__ = _lazy_load_wrap(dict.__len__)
    __lt__ = _lazy_load_wrap(dict.__lt__)
    __ne__ = _lazy_load_wrap(dict.__ne__)
    __repr__ = _lazy_load_wrap(dict.__repr__)
    __reversed__ = _lazy_load_wrap(dict.__reversed__)
    __sizeof__ = _lazy_load_wrap(dict.__sizeof__)
    __str__ = _lazy_load_wrap(dict.__str__)
    copy = _lazy_load_wrap(dict.copy)
    get = _lazy_load_wrap(dict.get)
    items = _lazy_load_wrap(dict.items)
    keys = _lazy_load_wrap(dict.keys)
    pop = _lazy_load_wrap(dict.pop)
    popitem = _lazy_load_wrap(dict.popitem)
    setdefault = _lazy_load_wrap(dict.setdefault)
    values = _lazy_load_wrap(dict.values)


def lru_cache_timed(maxsize=128, typed=False, timeout=3600):
    """LRU cache decorator where the cache expires after ``timeout`` seconds.

    This wraps the functools.lru_cache decorator so that the entire cache gets
    cleared if the cache is older than ``timeout`` seconds.

    This is mostly copied from this gist, with no license specified:
    https://gist.github.com/helix84/05ee246d6c80bc7bacdfa6a62fbff3fa

    The cachetools package provides a way to apply the timeout per-item, if that
    is required.

    Parameters
    ----------
    maxsize : int
        functools.lru_cache maxsize parameter
    typed : bool
        functools.lru_cache typed parameter
    timeout : int, float
        Clear cache after ``timeout`` seconds from last clear
    """
    import time

    def _wrapper(func):
        next_update = time.time() - 1  # Force cache reset first time
        # Apply @lru_cache to f
        func = functools.lru_cache(maxsize=maxsize, typed=typed)(func)

        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            clear_cache_if_expired()
            return func(*args, **kwargs)

        def clear_cache_if_expired():
            nonlocal next_update
            now = time.time()
            if now >= next_update:
                func.cache_clear()
                next_update = now + timeout

        def cache_info():
            """Report cache statistics"""
            clear_cache_if_expired()
            return func.cache_info()

        _wrapped.cache_info = cache_info
        _wrapped.cache_clear = func.cache_clear
        return _wrapped

    return _wrapper


class LRUDict(OrderedDict):
    """
    Dict that maintains a fixed capacity and evicts least recently used item when full.

    Inherits from collections.OrderedDict to maintain the order of insertion.

    Examples:
    ---------
    ::

        >>> d = LRUDict(2)
        >>> d["a"] = 1
        >>> d["b"] = 2
        >>> d["c"] = 3
        >>> list(d.keys())
        ['b', 'c']
        >>> d["b"]
        2
        >>> d["a"]
        Traceback (most recent call last):
            ...
        KeyError: 'a'

    Parameters:
    -----------
    capacity : int, optional
        The maximum number of items that the dictionary can hold. Defaults to 128.
    """

    def __init__(self, capacity=128):
        super().__init__()
        self.capacity = capacity

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.capacity:
            oldest = next(iter(self))
            del self[oldest]


@contextlib.contextmanager
def temp_env_var(name, value):
    """
    A context manager that temporarily sets an environment variable.

    Example::

        >>> os.environ.get("MY_VARIABLE")
        None
        >>> with temp_env_var("MY_VARIABLE", "my_value"):
        ...     os.environ.get("MY_VARIABLE")
        ...
        'my_value'
        >>> os.environ.get("MY_VARIABLE")
        None

    :param name: str
        Name of the environment variable to set.
    :param value: str
        Value to set the environment variable to.
    """
    original_value = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if original_value is not None:
            os.environ[name] = original_value
        else:
            del os.environ[name]


def convert_to_int_float_str(val: str) -> int | float | str:
    """Convert an input string into an int, float, or string.

    This tries to convert the input string into an int using the built-in ``int()``
    function. If that fails then it tries ``float()``, and finally if that fails it
    returns the original string.

    This function is often useful when parsing text representations of structured data
    where the data types are implicit.

    Parameters
    ----------
    val : str
        The input string to convert

    Returns
    -------
    int, float, or str
        The input value as an int, float, or string.
    """
    import ast

    if not isinstance(val, str):
        raise TypeError(f"input value must be a string, not {type(val).__name__}")

    try:
        out = int(val)
    except Exception:
        try:
            out = float(val)
        except Exception:
            try:
                # Handle an input like "'string'"
                out = ast.literal_eval(val)
                if not isinstance(out, str):
                    # If this wasn't a string literal (e.g. "[1]" then raise and return
                    # the original string.
                    raise ValueError
            except Exception:
                out = val

    return out
