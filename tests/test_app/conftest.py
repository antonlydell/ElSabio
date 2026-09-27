# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Fixtures for testing the wiring of the ElSabio web app."""

# Standard library
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Third party
import pytest
import streamlit as st
import streamlit_passwordless as stp
from streamlit.testing.v1 import AppTest

# Local
from elsabio.app import APP_PATH
from elsabio.database import URL, SessionFactory
from elsabio.database.models.tariff_analyzer import Tariff

APP_TEST_TIMEOUT = 30

# The business timezone of the app under test. It differs from the default
# timezone of the config so that a conversion from it can be told apart.
BUSINESS_TIMEZONE = 'America/New_York'


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
def admin() -> stp.User:
    r"""A signed in user with the Admin role."""

    return _signed_in_user(role=stp.AdminRole)


@pytest.fixture
def app(
    config_file_from_config_env_var: tuple[Path, str, dict[str, Any]],
    initialized_sqlite_db: tuple[SessionFactory, URL],
    monkeypatch: pytest.MonkeyPatch,
) -> AppTest:
    r"""An app test of the ElSabio web app.

    The app is configured by the config file of the environment variable
    ELSABIO_CONFIG_FILE, which points to an initialized database of the test
    that has no Tariff Analyzer data defined unless a fixture like `tariffs`
    adds it. The business timezone of the app is :data:`BUSINESS_TIMEZONE`.
    The modules of the app are removed from the module cache, and the data cache
    of Streamlit, which outlives the modules, is cleared so that the resources and
    the cached reference data of the app are rebuilt for each test.

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

    st.cache_data.clear()

    config_file_path.write_text(f"timezone = '{BUSINESS_TIMEZONE}'\n{config_data_str}")

    return AppTest.from_file(str(APP_PATH), default_timeout=APP_TEST_TIMEOUT)


@pytest.fixture
def tariffs(initialized_sqlite_db: tuple[SessionFactory, URL]) -> tuple[Tariff, Tariff]:
    r"""Two tariffs defined in the database of the app.

    The tariffs are ordered by name. The first tariff is valid for the calendar year
    of 2026 and was last updated at a known timestamp. The second tariff has never been
    updated and is valid from 2027 without an end date.

    Returns
    -------
    first : elsabio.database.models.tariff_analyzer.Tariff
        The first tariff.

    second : elsabio.database.models.tariff_analyzer.Tariff
        The second tariff.
    """

    session_factory, _ = initialized_sqlite_db

    first = Tariff(
        tariff_id=1,
        name='Tariff A',
        currency_id=1,
        validity_start=date(2026, 1, 1),
        validity_end=date(2027, 1, 1),
        created_at=datetime(2025, 11, 1, 8, 0, 0),
        updated_at=datetime(2026, 7, 15, 22, 30, 0),
    )
    second = Tariff(
        tariff_id=2,
        name='Tariff B',
        currency_id=1,
        validity_start=date(2027, 1, 1),
        validity_end=None,
        created_at=datetime(2026, 1, 10, 9, 15, 0),
        updated_at=None,
    )

    with session_factory() as session:
        session.add_all([first, second])
        session.commit()

    return first, second
