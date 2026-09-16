# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Wiring tests for the page `app._pages.tariff_analyzer.tariff_design`"""

# Third party
import pytest
import streamlit_passwordless as stp
from streamlit.testing.v1 import AppTest

PAGE = '_pages/tariff_analyzer/tariff_design.py'
TITLE = 'Tariff Design'

# =================================================================================================
# Tests
# =================================================================================================


class TestTariffDesignPageAccess:
    r"""Tests of who may reach the Tariff Design page."""

    def test_superuser_reaches_the_page_from_the_navigation(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that a Superuser can reach the Tariff Design page from the navigation."""

        # Setup
        # ===========================================================
        at = app
        at.session_state[stp.SK_USER] = superuser

        # Exercise
        # ===========================================================
        at.switch_page(PAGE).run()

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert TITLE in [t.value for t in at.title], 'The Tariff Design page was not rendered!'

    @pytest.mark.parametrize('fixture_name', ['user', 'viewer'])
    def test_a_user_and_a_viewer_are_refused(
        self,
        app: AppTest,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        r"""Test that a User and a Viewer are refused the Tariff Design page."""

        # Setup
        # ===========================================================
        at = app
        at.session_state[stp.SK_USER] = request.getfixturevalue(fixture_name)

        # Exercise
        # ===========================================================
        at.switch_page(PAGE).run()

        # Verify
        # ===========================================================
        assert TITLE not in [t.value for t in at.title], 'The Tariff Design page was rendered!'


class TestTariffDesignPageWithoutTariffs:
    r"""Tests of the Tariff Design page when no tariffs are defined."""

    def test_the_missing_tariffs_are_explained(self, app: AppTest, superuser: stp.User) -> None:
        r"""Test that the page explains that there are no tariffs to work with."""

        # Setup
        # ===========================================================
        at = app
        at.session_state[stp.SK_USER] = superuser

        # Exercise
        # ===========================================================
        at.switch_page(PAGE).run()

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'

        messages = ' '.join(i.value for i in at.info)
        assert 'No tariffs are defined yet' in messages, 'The empty state is not explained!'
        assert not at.dataframe, 'A table was rendered although there are no tariffs!'
