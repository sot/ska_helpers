# Licensed under a 3-clause BSD style license - see LICENSE.rst

import contextlib
import functools
import os
from collections import OrderedDict

import numpy as np

__all__ = [
    "get_owner",
    "LazyDict",
    "LazyVal",
    "LRUDict",
    "lru_cache_timed",
    "temp_env_var",
    "convert_to_int_float_str",
    "TypedDescriptor",
    "set_log_level",
]


@contextlib.contextmanager
def set_log_level(logger, level=None):
    """Set the log level of a logger and its handlers for context block.

    Parameters
    ----------
    logger : logging.Logger
        The logger object to set the level for.
    level : str, int, None, optional
        The log level to set.  This can be a string like "DEBUG", "INFO", "WARNING",
        "ERROR", "CRITICAL", or an integer value from the ``logging`` module. If level
        is None (default), the log level is not changed.
    """
    orig_levels = {}
    if level is not None:
        orig_levels[logger] = logger.level
        logger.setLevel(level)
        for handler in logger.handlers:
            orig_levels[handler] = handler.level
            handler.setLevel(level)
    try:
        yield
    finally:
        for log_obj, orig_level in orig_levels.items():
            log_obj.setLevel(orig_level)


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


def random_radec_in_cone(
    ra: float, dec: float, angle: float, size=None
) -> tuple[np.ndarray, np.ndarray]:
    """Get random sky coordinates within a cone.

    This returns a tuple of RA and Dec values within ``angle`` degrees of ``ra`` and
    ``dec``. The coordinates are uniformly distributed over the sky area.

    Parameters
    ----------
    ra : float
        RA in degrees of the center of the cone.
    dec : float
        Dec in degrees of the center of the cone.
    angle : float
        The radius of the cone in degrees.
    size : int, optional
        The number of random coordinates to generate. If not specified, a single
        coordinate is generated.

    Returns
    -------
    ra_rand : np.ndarray
        Random RA values in degrees.
    dec_rand : np.ndarray
        Random Dec values in degrees.
    """
    import chandra_aca.transform as cat
    from Quaternion import Quat

    # Convert input angles from degrees to radians
    angle_rad = np.radians(angle)

    # Generate a random azimuthal angle (phi) between 0 and 2π
    phi = np.random.uniform(0, 2 * np.pi, size=size)

    # Generate a random polar angle (theta) within the specified angle from the north pole
    u = np.random.uniform(0, 1, size=size)
    theta = np.arccos(1 - u * (1 - np.cos(angle_rad)))

    # Generate vectors around pole (dec=90)
    ra_rot = np.degrees(phi)
    dec_rot = 90 - np.degrees(theta)
    eci = cat.radec_to_eci(ra_rot, dec_rot)

    # Swap x and z axes to get vectors centered around RA=0 ad Dec=0
    eci[..., [0, 2]] = eci[..., [2, 0]]

    # Now rotate the random vectors to be centered about the desired RA and Dec.
    q = Quat([ra, dec, 0])
    eci_rot = q.transform @ eci.T
    ra_rand, dec_rand = cat.eci_to_radec(eci_rot.T)

    return ra_rand, dec_rand


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

    Notes
    -----
    An input string like "01234" is interpreted as a decimal integer and will be
    returned as the integer 1234. In some contexts a leading 0 indicates an octal number
    and to avoid confusion in Python a leading 0 is not allowed in a decimal integer
    literal.
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


class TypedDescriptor:
    """Class to create a descriptor for a dataclass attribute that is cast to a type.

    This is a base class for creating a descriptor that can be used to define an
    attribute on a dataclass that is cast to a specific type.  The type is specified by
    setting the ``cls`` class attribute on the descriptor class.

    Most commonly ``cls`` is a class like ``CxoTime`` or ``Quat``, but it could also be
    a built-in like ``int`` or ``float`` or any callable function.

    This descriptor can be used either as a base class with the ``cls`` class attribute
    set accordingly, or as a descriptor with the ``cls`` keyword argument set.

    .. warning:: This descriptor class is recommended for use within a
       `dataclass <https://docs.python.org/3/library/dataclasses.html>`_. In a normal
        class the default value **must** be set to the correct type since it will not be
        coerced to the correct type automatically.

    The default value cannot be ``list``, ``dict``, or ``set`` since these are mutable
    and are disallowed by the dataclass machinery. In most cases a ``list`` can be
    replaced by a ``tuple`` and a ``dict`` can be replaced by an ``OrderedDict``.

    Parameters
    ----------
    default : optional
        Default value for the attribute. If specified and not ``None``, it will be
        coerced to the correct type via ``cls(default)``.  If not specified, the default
        for the attribute is ``None``.
    required : bool, optional
        If ``True``, the attribute is required to be set explicitly when the object is
        created. If ``False`` the default value is used if the attribute is not set.

    Examples
    --------
    >>> from dataclasses import dataclass
    >>> from ska_helpers.utils import TypedDescriptor

    Here we make a dataclass with an attribute that is cast to an int.

    >>> @dataclass
    >>> class SomeClass:
    ...     int_val: int = TypedDescriptor(required=True, cls=int)
    >>> obj = SomeClass(10.5)
    >>> obj.int_val
    10

    Here we define a ``QuatDescriptor`` class that can be used repeatedly for any
    quaternion attribute.

    >>> from Quaternion import Quat
    >>> class QuatDescriptor(TypedDescriptor):
    ...     cls = Quat
    >>> @dataclass
    ... class MyClass:
    ...     att1: Quat = QuatDescriptor(required=True)
    ...     att2: Quat = QuatDescriptor(default=[10, 20, 30])
    ...     att3: Quat | None = QuatDescriptor()
    ...
    >>> obj = MyClass(att1=[0, 0, 0, 1])
    >>> obj.att1
    <Quat q1=0.00000000 q2=0.00000000 q3=0.00000000 q4=1.00000000>
    >>> obj.att2.equatorial
    array([10., 20., 30.])
    >>> obj.att3 is None
    True
    >>> obj.att3 = [10, 20, 30]
    >>> obj.att3.equatorial
    array([10., 20., 30.])
    """

    def __init__(self, *, default=None, required=False, cls=None):
        if cls is not None:
            self.cls = cls
        if required and default is not None:
            raise ValueError("cannot set both 'required' and 'default' arguments")
        self.required = required

        # Default is set here at the time of class creation, not at the time of
        # instantiation.  Coercing the default to the correct type is deferred until the
        # instance is created. This happens because at instance creation (if the
        # attribute value was not specified) the dataclass machinery evaluates
        # ``Class.attr`` (e.g. ``QuatDescriptor.quat``) which triggers the ``__get__``
        # method of the descriptor with ``obj=None``. That returns the default which is
        # then passed to the ``__set__`` method which does type coercion. See
        # https://docs.python.org/3/library/dataclasses.html#descriptor-typed-fields and
        # the bit about "To determine whether a field contains a default value".
        self.default = default

    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            # See long comment above about why this is returning self.default.
            return self.default

        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if self.required and value is None:
            raise ValueError(
                f"attribute {self.name[1:]!r} is required and cannot be set to None"
            )
        # None is the default value for the attribute if it is not set explicitly.
        # In this case it is not coerced to the descriptor type.
        if value is not None:
            value = self.cls(value)
        setattr(obj, self.name, value)
