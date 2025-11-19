import functools
import inspect
import logging
import random
import re
import sys
import time
import traceback
from dataclasses import dataclass, field

from ska_helpers.logging import basic_logger

__all__ = [
    "retry",
    "retry_call",
    "retry_func",
    "RetryError",
    "tables_open_file",
    "MockFuncFailure",
]

logging_logger = basic_logger(__name__)


class RetryError(Exception):
    """
    Keep track of the stack of exceptions when trying multiple times.

    Parameters
    ----------
    failures : list of dict, each with keys 'type', 'value', 'trace'.
    """

    def __init__(self, failures):
        self.failures = failures


@dataclass
class MockFuncFailure:
    """Mock a function ``func`` to fail ``n_fail`` times and then succeed.

    This can be used to confirm that retry logic deep inside another package (e.g.
    cheta or kadi) is working as expected. The key here is that this forces some
    failures but then returns the real function result.

    See `cheta.tests.test_comps.test_stk_ephem_timeout()` for an example usage.

    Parameters
    ----------
    func : callable
        The function to mock.
    n_fail : int, optional
        The number of times to fail before succeeding. Default is 2.
    calls : list of dict, optional
        A list to record the calls made to the function. Each call is recorded
        as a dictionary with keys 'args', 'kwargs', and 'success'. Default is an empty
        list.
    exception_cls : type, optional
        The exception class to raise on failure. Default is TimeoutError.
    """

    func: callable
    n_fail: int = 2
    calls: list[dict] = field(default_factory=list)
    exception_cls: type = TimeoutError

    def __call__(self, *args, **kwargs):
        call = {"args": args, "kwargs": kwargs}
        self.calls.append(call)

        count = len(self.calls)
        if count % (self.n_fail + 1) != 0:
            call["success"] = False
            raise self.exception_cls(
                f"mock exception {self.exception_cls.__name__} #{count}"
            )
        call["success"] = True
        return self.func(*args, **kwargs)

    @property
    def __name__(self):
        return "mock-" + self.func.__name__

    def __hash__(self) -> int:
        return id(self)


def _mangle_alert_words(msg):
    """
    Mangle alert words "warning", "error", "fatal", "fail", "exception" in a string.

    This is done by replacing "i" or "l" with "1" and "o" with "0" in the middle of
    any of these words. The intent is to avoid triggering the task schedule "check" for
    for those words. This is done with a case-insensitive regex substitution.

    Example::

        >>> mangle_alert_words("WARNING: This is a fatal Error message.")
        'WARN1NG: This is a fata1 Err0r message.'

    :param msg: the string to mangle.
    :returns: the mangled string.
    """
    for re_word, sub in (
        ("(warn)(i)(ng)", "1"),
        ("(err)(o)(r)", "0"),
        ("(fata)(l)()", "1"),
        ("(fai)(l)()", "1"),
        ("(excepti)(o)(n)", "0"),
    ):
        msg = re.sub(re_word, rf"\g<1>{sub}\3", msg, flags=re.IGNORECASE)
    return msg


def __retry_internal(
    f,
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
    mangle_alert_words=True,
    args=None,
    kwargs=None,
):
    """
    Executes a function and retries it if it failed.

    :param f: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :param mangle_alert_words: if True, mangle alert words "warning", "error", "fatal",
                   "exception", "fail" when issuing a logger warning message.
                   Default: False.
    :param args: tuple, function args
    :param kwargs: dict, function kwargs
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    failures = []
    while _tries:
        try:
            return f(*args, **kwargs)
        except exceptions as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace = traceback.extract_tb(exc_traceback)
            failures.append({"type": exc_type, "value": exc_value, "trace": trace})

            _tries -= 1
            if not _tries:
                exc_types = set([e["type"] for e in failures])
                exc_values = set([str(e["value"]) for e in failures])
                if len(exc_types) > 1 or len(exc_values) > 1:
                    raise RetryError(failures=failures)
                else:
                    raise

            if logger is not None:
                # Do not show kwarg values since they might include a password
                call_args = list(args) + [f"{key}=..." for key in kwargs]
                call_args_str = ", ".join(str(arg) for arg in call_args)
                func_name = getattr(f, "__name__", "func")
                func_call = f"{func_name}({call_args_str})"
                msg = (
                    f"WARNING: {func_call} exception: {e}, retrying "
                    f"in {_delay} seconds..."
                )
                if mangle_alert_words:
                    msg = _mangle_alert_words(msg)
                logger.warning(msg)

            time.sleep(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)


RETRY_DEFAULTS = {"tries": 3, "delay": 1, "backoff": 2, "mangle_alert_words": True}


@functools.cache
def retry_func(func, logger=..., **retry_kwargs):
    """Wrap function with retry decorator using reasonable defaults.

    The defaults are defined in RETRY_DEFAULTS::

        {"tries": 3, "delay": 1, "backoff": 2, "mangle_alert_words": True}

    If a logger is not provided, will attempt to get from caller's global 'logger'.

    The output is cached for performance and so that multiple calls return the same
    function.

    Parameters
    ----------
    func : callable
        Function to retry.
    logger : Logger, optional
        Logger to use. If not supplied, will attempt to get from caller's global 'logger'.
        Set logger=None to disable this.
    **retry_kwargs
        Additional keyword arguments passed to the retry decorator, including overriding
        the RETRY_DEFAULTS settings.

    Returns
    -------
    callable
        Wrapped function that will be retried.
    """
    retry_kwargs = RETRY_DEFAULTS | retry_kwargs
    if logger is ...:
        frame = inspect.currentframe().f_back  # Caller's frame
        logger = frame.f_globals.get("logger")
        del frame  # Avoid reference cycles with frames

    if isinstance(logger, logging.Logger):
        retry_kwargs = retry_kwargs | {"logger": logger}

    return retry(**retry_kwargs)(func)


def retry(
    exceptions=Exception,
    tries=3,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
    mangle_alert_words=True,
):
    """Returns a retry decorator.

    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :param mangle_alert_words: if True, mangle alert words "warning", "error", "fatal",
                   "exception" when issuing a logger warning message. Default: True.
    :returns: a retry decorator.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return __retry_internal(
                f,
                exceptions,
                tries,
                delay,
                max_delay,
                backoff,
                jitter,
                logger,
                mangle_alert_words=mangle_alert_words,
                args=args,
                kwargs=kwargs,
            )

        return wrapper

    return decorator


def retry_call(
    f,
    args=None,
    kwargs=None,
    exceptions=Exception,
    tries=3,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
    mangle_alert_words=True,
):
    """
    Calls a function and re-executes it if it failed.

    :param f: the function to execute.
    :param args: the positional arguments of the function to execute.
    :param kwargs: the named arguments of the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :param mangle_alert_words: if True, mangle alert words "warning", "error", "fatal",
                   "exception", "fail" when issuing a logger warning message.
                   Default: True.
    :returns: the result of the f function.
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    return __retry_internal(
        f,
        exceptions,
        tries,
        delay,
        max_delay,
        backoff,
        jitter,
        logger,
        mangle_alert_words=mangle_alert_words,
        args=args,
        kwargs=kwargs,
    )


def tables_open_file(*args, **kwargs):
    """Call ``tables.open_file(*args, **kwargs)`` with retry up to 3 times.

    This only catches tables.exceptions.HDF5ExtError. After an initial failure
    it will try again after 2 seconds and once more after 4 seconds.

    :param *args: args passed through to tables.open_file()
    :param mangle_alert_words: (keyword-only) if True, mangle alert words "warning",
                   "error", "fatal", "exception", "fail" when issuing a logger warning
                   message. Default: True.
    :param retry_delay: (keyword-only) initial delay between attempts. default: 2.
    :param retry_tries: (keyword-only) the maximum number of attempts. default: 3.
    :param retry_backoff: (keyword-only) multiplier applied to delay between attempts.
                     default: 2.
    :param retry_logger: (keyword-only) logger.warning(msg) will be called.
    :param **kwargs: additional kwargs passed through to tables.open_file()
    :returns: tables file handle
    """
    import tables
    import tables.exceptions

    import ska_helpers.retry

    mangle_alert_words = kwargs.pop("mangle_alert_words", True)
    retry_delay = kwargs.pop("retry_delay", 2)
    retry_tries = kwargs.pop("retry_tries", 3)
    retry_backoff = kwargs.pop("retry_backoff", 2)
    retry_logger = kwargs.pop("retry_logger", logging_logger)

    h5 = ska_helpers.retry.retry_call(
        tables.open_file,
        args=args,
        kwargs=kwargs,
        exceptions=tables.exceptions.HDF5ExtError,
        delay=retry_delay,
        tries=retry_tries,
        backoff=retry_backoff,
        logger=retry_logger,
        mangle_alert_words=mangle_alert_words,
    )
    return h5
