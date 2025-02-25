import os
from ska_helpers.shell import importenv, getenv


def test_getenv():
    # basic env setting
    envs = getenv('export TEST_ENV_VAR_A="hello"')  # default shell is bash
    assert envs["TEST_ENV_VAR_A"] == "hello"
    assert "TEST_ENV_VAR_A" not in os.environ

    envs = getenv("setenv TEST_ENV_VAR_A 'hello'", shell="csh")
    assert envs["TEST_ENV_VAR_A"] == "hello"
    assert "TEST_ENV_VAR_A" not in os.environ

    envs = getenv('export TEST_ENV_VAR_A="hello"', shell="bash")
    assert envs["TEST_ENV_VAR_A"] == "hello"
    assert "TEST_ENV_VAR_A" not in os.environ


def test_getenv_env():
    # env setting with env argument
    envs = getenv("echo", env={"TEST_ENV_VAR_A": "one"}, shell="csh")
    assert envs["TEST_ENV_VAR_A"] == "one"
    assert "TEST_ENV_VAR_A" not in os.environ

    envs = getenv("echo", env={"TEST_ENV_VAR_A": "one"}, shell="bash")
    assert envs["TEST_ENV_VAR_A"] == "one"
    assert "TEST_ENV_VAR_A" not in os.environ

    # env setting with env argument and shell command
    envs = getenv(
        "setenv TEST_ENV_VAR_A $TEST_ENV_VAR_B",
        env={"TEST_ENV_VAR_B": "one"},
        shell="csh",
    )
    assert envs["TEST_ENV_VAR_A"] == "one"
    assert "TEST_ENV_VAR_A" not in os.environ

    envs = getenv(
        "export TEST_ENV_VAR_A=$TEST_ENV_VAR_B",
        env={"TEST_ENV_VAR_B": "one"},
        shell="csh",
    )
    assert envs["TEST_ENV_VAR_A"] == "one"
    assert "TEST_ENV_VAR_A" not in os.environ


def test_getenv_clean():
    os.environ["TEST_ENV_VAR_C"] = "val"

    envs = getenv("echo", shell="csh")
    assert "TEST_ENV_VAR_C" not in envs

    envs = getenv("echo", shell="csh", clean=False)
    assert "TEST_ENV_VAR_C" in envs
    assert envs["TEST_ENV_VAR_C"] == "val"

    envs = getenv("echo", shell="bash")
    assert "TEST_ENV_VAR_C" not in envs

    envs = getenv("echo", shell="bash", clean=False)
    assert "TEST_ENV_VAR_C" in envs
    assert envs["TEST_ENV_VAR_C"] == "val"


def test_importenv():
    importenv('export TEST_ENV_VAR_C="hello"', env={"TEST_ENV_VAR_B": "world"})
    assert os.environ["TEST_ENV_VAR_C"] == "hello"
    assert os.environ["TEST_ENV_VAR_B"] == "world"

    envs = importenv("echo", env={"TEST_ENV_VAR_A": "two"}, shell="bash")
    assert envs["TEST_ENV_VAR_A"] == "two"
    assert os.environ["TEST_ENV_VAR_A"] == "two"

    envs = importenv('export TEST_ENV_VAR_A="hello"', shell="bash")
    assert envs["TEST_ENV_VAR_A"] == "hello"
    assert os.environ["TEST_ENV_VAR_A"] == "hello"
