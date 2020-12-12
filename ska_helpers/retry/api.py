import functools
import logging
import random
import time


logging_logger = logging.getLogger(__name__)


def __retry_internal(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1,
                     jitter=0, logger=logging_logger, args=None, kwargs=None):
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
    :param args: tuple, function args
    :param kwargs: dict, function kwargs
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    while _tries:
        try:
            return f(*args, **kwargs)
        except exceptions as e:
            _tries -= 1
            if not _tries:
                raise

            if logger is not None:
                call_args = list(args)
                for key, val in kwargs.items():
                    call_args.append(f'{key}={val}')
                call_args_str = ', '.join(str(arg) for arg in call_args)
                func_name = getattr(f, '__name__', 'func')
                func_call = f'{func_name}({call_args_str})'
                logger.warning(f'WARNING: {func_call} exception: {e}, retrying '
                               f'in {_delay} seconds...')

            time.sleep(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)


def retry(exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0,
          logger=logging_logger):
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
    :returns: a retry decorator.
    """

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return __retry_internal(f, exceptions, tries, delay, max_delay,
                                    backoff, jitter, logger, args=args, kwargs=kwargs)
        return wrapper

    return decorator


def retry_call(f, args=None, kwargs=None, exceptions=Exception, tries=-1, delay=0,
               max_delay=None, backoff=1, jitter=0,
               logger=logging_logger):
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
    :returns: the result of the f function.
    """
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    return __retry_internal(f, exceptions, tries, delay, max_delay,
                            backoff, jitter, logger, args=args, kwargs=kwargs)
