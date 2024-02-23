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
import tables

from ska_helpers.retry import RetryError, retry, tables_open_file
from ska_helpers.retry.api import _mangle_alert_words, retry_call


def test_retry(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

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
    assert mock_sleep_time[0] == sum(delay * backoff**i for i in range(tries - 1))


def test_tries_inf():
    hit = [0]
    target = 10

    @retry(tries=float("inf"))
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

    monkeypatch.setattr(time, "sleep", mock_sleep)

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

    monkeypatch.setattr(time, "sleep", mock_sleep)

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

    kwargs = {"value": -1}
    result = None
    f_mock = MagicMock(spec=f, return_value=kwargs["value"])
    try:
        result = retry_call(f_mock, kwargs=kwargs)
    except RuntimeError:
        pass

    assert result == kwargs["value"]
    assert f_mock.call_count == 1


def test_retry_exception():
    def f(value=0):
        if value < 0:
            return value
        else:
            raise RuntimeError

    # if only one kind of exception is raised, then it is re-raised
    f_mock = MagicMock(side_effect=RuntimeError("runtime"))
    try:
        retry_call(f_mock, tries=2)
    except RuntimeError as e:
        assert str(e) == "runtime"

    # otherwise, a RetryError is raised
    f_mock = MagicMock(side_effect=[RuntimeError("runtime"), OSError("os")])
    try:
        retry_call(f_mock, tries=2)
    except RetryError as e:
        assert len(e.failures) == 2
        for failure in e.failures:
            assert sorted(failure.keys()) == ["trace", "type", "value"]

    f_mock = MagicMock(side_effect=[RuntimeError("runtime"), RuntimeError("runtime 2")])
    try:
        retry_call(f_mock, tries=2)
    except RetryError as e:
        assert len(e.failures) == 2


def test_mangle_alert_words():
    # Test case 1: No alert words in the message
    msg = "This is a normal message."
    assert _mangle_alert_words(msg) == msg

    # Test case 2: Single occurrence of each alert word
    msg = "WARNING: Failing fatAL Error exception message."
    expected_output = "WARN1NG: Fai1ing fatA1 Err0r excepti0n message."
    assert _mangle_alert_words(msg) == expected_output

    # Test case 3: Multiple occurrences of alert words and special characters
    msg = "fata1 fata1 fata1WARN1NGWARN1NG!@#$%^&*()"
    expected_output = "fata1 fata1 fata1WARN1NGWARN1NG!@#$%^&*()"
    assert _mangle_alert_words(msg) == expected_output

    # Test case 4: Empty message
    msg = ""
    assert _mangle_alert_words(msg) == ""


class MockTableOpen:
    def __init__(self, n_fail):
        self.n_fail = n_fail

    def __call__(self, *args, **kwargs):
        msg = """WARNING: Fatal error exception FAILURE: HDF5 error back trace
'/proj/sot/ska3/flight/bin/cheta_update_server_archive --data-root /proj/sot/ska3/flight/data/eng_archive' returned non-zero status: 256
    driver lock request failed
  File "H5FDsec2.c", line 1002, in H5FD__sec2_lock
    unable to lock file, errno = 11, error message = 'Resource temporarily unavailable'
    tables.exceptions.HDF5ExtError: HDF5 error back trace
    """
        self.n_fail -= 1
        if self.n_fail >= 0:
            raise tables.exceptions.HDF5ExtError(msg)
        else:
            return "SUCCESS"


class MockLogger:
    """Mock logger that just prints the message.

    Insanely enough, pytest capsys does not capture logger warnings, not does caplog
    capture those warnings. There are years-old GH issues open on this and it seems like
    it won't get fixed. After wasting 1/2 hour on this I'm just going to use a print
    statement.
    """

    def warning(self, msg):
        print(msg)


def test_tables_open_file_warning_with_mangle_alert_words(monkeypatch, capsys):
    mock_table_open = MockTableOpen(2)
    monkeypatch.setattr(tables, "open_file", mock_table_open)
    logger = MockLogger()
    h5 = tables_open_file("junk.h5", retry_delay=0.01, retry_logger=logger)
    assert h5 == "SUCCESS"
    out = capsys.readouterr().out.lower()
    for word in ["warning", "error", "exception", "fatal", "fail"]:
        assert word not in out
    for word in ["warn1ng", "err0r", "excepti0n", "fata1", "fai1"]:
        assert word in out


def test_tables_open_file_warning_without_mangle_alert_words(monkeypatch, capfd):
    mock_table_open = MockTableOpen(2)
    monkeypatch.setattr(tables, "open_file", mock_table_open)
    logger = MockLogger()
    h5 = tables_open_file(
        "junk.h5", retry_delay=0.01, mangle_alert_words=False, retry_logger=logger
    )
    assert h5 == "SUCCESS"
    out = capfd.readouterr().out.lower()
    for word in ["warning", "error", "exception", "fatal", "fail"]:
        assert word in out
    for word in ["warn1ng", "err0r", "excepti0n", "fata1", "fai1"]:
        assert word not in out


def test_tables_open_file_exception_with_mangle_alert_words(monkeypatch):
    mock_table_open = MockTableOpen(5)
    monkeypatch.setattr(tables, "open_file", mock_table_open)
    with pytest.raises(tables.exceptions.HDF5ExtError) as exc:
        tables_open_file("junk.h5", retry_delay=0.01)
        for word in ["warning", "error", "exception", "fatal", "fail"]:
            assert word in str(exc.value).lower()
