try:
    from unittest.mock import create_autospec
except ImportError:
    from mock import create_autospec  # noqa

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

import time

import pytest

from ska_helpers.retry import RetryError, retry
from ska_helpers.retry.api import retry_call


def test_retry(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2

    @retry(tries=tries, delay=delay, backoff=backoff)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(
        delay * backoff ** i for i in range(tries - 1))


def test_tries_inf():
    hit = [0]
    target = 10

    @retry(tries=float('inf'))
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target
        else:
            raise ValueError
    assert f() == target


def test_tries_minus1():
    hit = [0]
    target = 10

    @retry(tries=-1)
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target
        else:
            raise ValueError
    assert f() == target


def test_max_delay(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2
    max_delay = delay  # Never increase delay

    @retry(tries=tries, delay=delay, max_delay=max_delay, backoff=backoff)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == delay * (tries - 1)


def test_fixed_jitter(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, 'sleep', mock_sleep)

    hit = [0]

    tries = 10
    jitter = 1

    @retry(tries=tries, jitter=jitter)
    def f():
        hit[0] += 1
        1 / 0

    with pytest.raises(ZeroDivisionError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(range(tries - 1))


def test_retry_call():
    f_mock = MagicMock(side_effect=RuntimeError)
    tries = 2
    try:
        retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert f_mock.call_count == tries


def test_retry_call_2():
    side_effect = [RuntimeError, RuntimeError, 3]
    f_mock = MagicMock(side_effect=side_effect)
    tries = 5
    result = None
    try:
        result = retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert result == 3
    assert f_mock.call_count == len(side_effect)


def test_retry_call_with_args():

    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    return_value = -1
    result = None
    f_mock = MagicMock(spec=f, return_value=return_value)
    try:
        result = retry_call(f_mock, args=[return_value])
    except RuntimeError:
        pass

    assert result == return_value
    assert f_mock.call_count == 1


def test_retry_call_with_kwargs():

    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    kwargs = {'value': -1}
    result = None
    f_mock = MagicMock(spec=f, return_value=kwargs['value'])
    try:
        result = retry_call(f_mock, kwargs=kwargs)
    except RuntimeError:
        pass

    assert result == kwargs['value']
    assert f_mock.call_count == 1


def test_retry_exception():

    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    # if only one kind of exception is raised, then it is re-raised
    f_mock = MagicMock(side_effect=RuntimeError('runtime'))
    try:
        retry_call(f_mock, tries=2)
    except RuntimeError as e:
        assert str(e) == 'runtime'

    # otherwise, a RetryError is raised
    f_mock = MagicMock(side_effect=[RuntimeError('runtime'), OSError('os')])
    try:
        retry_call(f_mock, tries=2)
    except RetryError as e:
        assert len(e.failures) == 2
        for failure in e.failures:
            assert sorted(failure.keys()) == ['trace', 'type', 'value']

    f_mock = MagicMock(side_effect=[RuntimeError('runtime'), RuntimeError('runtime 2')])
    try:
        retry_call(f_mock, tries=2)
    except RetryError as e:
        assert len(e.failures) == 2