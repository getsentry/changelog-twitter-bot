import os
import pathlib
import subprocess
import sys

import pytest

import main

FUNCTION_DIR = pathlib.Path(main.__file__).resolve().parent


def import_main_with_env(env):
    return subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=FUNCTION_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("missing", main.REQUIRED_ENV_VARS)
def test_import_fails_fast_when_a_required_variable_is_missing(missing):
    env = {k: v for k, v in os.environ.items() if k != missing}

    result = import_main_with_env(env)

    assert result.returncode != 0
    assert f"Missing required environment variable: {missing}" in result.stderr


@pytest.mark.parametrize("missing", main.REQUIRED_ENV_VARS)
def test_import_treats_empty_variables_as_missing(missing):
    env = dict(os.environ, **{missing: ""})

    result = import_main_with_env(env)

    assert result.returncode != 0
    assert f"Missing required environment variable: {missing}" in result.stderr


def test_import_succeeds_with_all_variables_set():
    result = import_main_with_env(dict(os.environ))

    assert result.returncode == 0, result.stderr


def test_required_variables_match_the_secrets_wired_in_terraform():
    # The Terraform module injects these exact names as secret env vars, so a
    # rename on either side would only show up as a crash at cold start.
    terraform = (FUNCTION_DIR.parent / "changelog-twitter-poster.tf").read_text()

    for var in main.REQUIRED_ENV_VARS:
        assert var in terraform, f"{var} is not configured in changelog-twitter-poster.tf"
