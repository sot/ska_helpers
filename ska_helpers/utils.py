import functools

__all__ = ['LazyDict', 'LazyVal']


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
        if not hasattr(self, '_val'):
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


