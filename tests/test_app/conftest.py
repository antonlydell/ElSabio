# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Fixtures for testing the wiring of the ElSabio web app."""

# Standard library
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Third party
import pytest
import streamlit_passwordless as stp
from streamlit.testing.v1 import AppTest

# Local
from elsabio.app import APP_PATH
from elsabio.database import URL, SessionFactory

APP_TEST_TIMEOUT = 30


def _signed_in_user(role: stp.Role) -> stp.User:
    r"""Create a signed in user with the supplied role.

    Parameters
    ----------
    role : streamlit_passwordless.Role
        The role of the user.

    Returns
    -------
    streamlit_passwordless.User
        The signed in user.
    """

    user_id = uuid4()

    return stp.User(
        user_id=user_id,
        username=f'{role.name.lower()}@elsabio.com',
        role=role,
        sign_in=stp.UserSignIn(
            user_id=user_id,
            sign_in_timestamp=datetime(2025, 10, 1, 12, 0, 0),
            success=True,
            origin='http://localhost:8501',
            device='Firefox',
            country='SE',
            credential_nickname='ElSabio',
            credential_id='credential_id',
            sign_in_type='passkey_signin',
        ),
    )


@pytest.fixture
def viewer() -> stp.User:
    r"""A signed in user with the Viewer role."""

    return _signed_in_user(role=stp.ViewerRole)


@pytest.fixture
def user() -> stp.User:
    r"""A signed in user with the User role."""

    return _signed_in_user(role=stp.UserRole)


@pytest.fixture
def superuser() -> stp.User:
    r"""A signed in user with the SuperUser role."""

    return _signed_in_user(role=stp.SuperUserRole)


@pytest.fixture
def app(
    config_file_from_config_env_var: tuple[Path, str, dict[str, Any]],
    initialized_sqlite_db: tuple[SessionFactory, URL],
    monkeypatch: pytest.MonkeyPatch,
) -> AppTest:
    r"""An app test of the ElSabio web app.

    The app is configured by the config file of the environment variable
    ELSABIO_CONFIG_FILE, which points to an initialized database of the test
    that has no Tariff Analyzer data defined. The modules of the app are
    removed from the module cache so that the resources and the cached
    reference data of the app are rebuilt for each test.

    Returns
    -------
    streamlit.testing.v1.AppTest
        The app test of the web app.
    """

    config_file_path, config_data_str, _ = config_file_from_config_env_var
    _, db_url = initialized_sqlite_db

    assert str(db_url) in config_data_str, (
        f'Config file "{config_file_path}" does not point to test database "{db_url}"!'
    )

    for module in [name for name in sys.modules if name.startswith('elsabio.app')]:
        monkeypatch.delitem(sys.modules, module, raising=False)

    return AppTest.from_file(str(APP_PATH), default_timeout=APP_TEST_TIMEOUT)
