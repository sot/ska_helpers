import functools

__all__ = ['LazyDict']


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

    The lazy value is accessed using the ``get`` method.

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

    def get(self):
        if not self._loaded:
            self.val = self._load_func(*self._args, **self._kwargs)
            self._loaded = True

            # Delete these so pickling always works (pickling a func can fail)
            del self._load_func
            del self._args
            del self._kwargs

        return self.val


class LazyDict(dict):
    """Dict which is lazy-initialized using supplied function ``load_func``.

    This class allows defining a module-level dict that is expensive to
    initialize, where the initialization is done lazily (only when actually
    needed).

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

            # Delete these so pickling always works (pickling a func can fail)
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
