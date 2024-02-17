import functools
import random
import re
import sys
import time
import traceback

from ska_helpers.logging import basic_logger

logging_logger = basic_logger(__name__, format="%(message)s")


class RetryError(Exception):
    """
    Keep track of the stack of exceptions when trying multiple times.

    Parameters
    ----------
    failures : list of dict, each with keys 'type', 'value', 'trace'.
    """

    def __init__(self, failures):
        self.failures = failures


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
    mangle_alert_words=False,
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
                call_args = list(args)
                for key, val in kwargs.items():
                    call_args.append(f"{key}={val}")
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


def retry(
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
    mangle_alert_words=False,
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
                   "exception" when issuing a logger warning message. Default: False.
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
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
    mangle_alert_words=False,
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
                   Default: False.
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
