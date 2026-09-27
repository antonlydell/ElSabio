# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Wiring tests for the page `app._pages.tariff_analyzer.tariff_design`

The page is reached the way a user reaches it: the app is started from its router and the page
is selected in the navigation. A page that is not part of the navigation of the signed in user
cannot be selected, and the router then falls back to its default page.
"""

# Standard library
from datetime import datetime

# Third party
import pandas as pd
import pytest
import streamlit_passwordless as stp
from streamlit.testing.v1 import AppTest

# Local
from elsabio.models.tariff_analyzer import TariffDataFrameModel

PAGE = '_pages/tariff_analyzer/tariff_design.py'
TITLE = 'Tariff Design'
NOT_FOUND = 'The linked tariff could not be found'


def open_tariff_design(at: AppTest, user: stp.User, **query_params: str) -> AppTest:
    r"""Sign in `user` and open the Tariff Design page from the navigation of the app.

    Parameters
    ----------
    at : streamlit.testing.v1.AppTest
        The app test of the web app.

    user : streamlit_passwordless.User
        The user to sign in.

    **query_params : str
        The query parameters of the address of the page.

    Returns
    -------
    streamlit.testing.v1.AppTest
        `at` after the page has been run.
    """

    at.session_state[stp.SK_USER] = user
    at.query_params.update(query_params)

    return at.switch_page(PAGE).run()


def page_rendered(at: AppTest) -> bool:
    r"""Check if the Tariff Design page was rendered."""

    return TITLE in [t.value for t in at.title]


def warning_text(at: AppTest) -> str:
    r"""Get the text of all warnings that were rendered."""

    return ' '.join(w.value for w in at.warning)


# =================================================================================================
# Tests
# =================================================================================================


class TestTariffDesignPageAccess:
    r"""Tests of who may reach the Tariff Design page."""

    @pytest.mark.parametrize('fixture_name', ['superuser', 'admin'])
    def test_a_superuser_and_an_admin_reach_the_page_from_the_navigation(
        self, app: AppTest, fixture_name: str, request: pytest.FixtureRequest
    ) -> None:
        r"""Test that a Superuser, and an Admin by rank, reach the page from the navigation."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=request.getfixturevalue(fixture_name))

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert page_rendered(at), 'The Tariff Design page was not rendered!'

    @pytest.mark.parametrize('fixture_name', ['user', 'viewer'])
    def test_a_user_and_a_viewer_are_refused(
        self,
        app: AppTest,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        r"""Test that a User and a Viewer who open the address of the page are refused."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=request.getfixturevalue(fixture_name))

        # Verify
        # ===========================================================
        assert not page_rendered(at), 'The Tariff Design page was rendered!'


class TestTariffDesignPageWithoutTariffs:
    r"""Tests of the Tariff Design page when no tariffs are defined."""

    def test_the_missing_tariffs_are_explained(self, app: AppTest, superuser: stp.User) -> None:
        r"""Test that the page explains that there are no tariffs to work with."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'

        messages = ' '.join(i.value for i in at.info)
        assert 'No tariffs are defined yet' in messages, 'The empty state is not explained!'
        assert not at.dataframe, 'A table was rendered although there are no tariffs!'


@pytest.mark.usefixtures('tariffs')
class TestTariffList:
    r"""Tests of the list of the tariffs of the Tariff Design page."""

    def test_last_edited_is_shown_in_the_business_timezone(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that *Last edited* is converted from UTC to the business timezone.

        The business timezone of the app is America/New_York, which is 4 hours behind
        UTC in the summer and 5 hours behind UTC in the winter.
        """

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'

        df = at.dataframe[0].value
        assert df[TariffDataFrameModel.c_last_edited_at].tolist() == [
            pd.Timestamp(datetime(2026, 7, 15, 18, 30, 0)),
            pd.Timestamp(datetime(2026, 1, 10, 4, 15, 0)),
        ], 'Last edited is not shown in the business timezone!'

    def test_valid_until_is_the_last_day_the_tariff_is_valid(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that *Valid until* is inclusive and empty for an open-ended tariff."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'

        valid_until = at.dataframe[0].value[TariffDataFrameModel.c_validity_end]
        assert valid_until.iloc[0] == pd.Timestamp(2026, 12, 31), 'Valid until is not inclusive!'
        assert pd.isna(valid_until.iloc[1]), 'An open-ended tariff has a Valid until date!'


@pytest.mark.usefixtures('tariffs')
class TestTariffDesignPageSelection:
    r"""Tests of the selected tariff and the active tab carried in the address of the page."""

    @pytest.mark.parametrize('query_params', [{}, {'tariff_id': ''}], ids=['missing', 'empty'])
    def test_no_tariff_in_the_address_selects_the_first_tariff(
        self, app: AppTest, superuser: stp.User, query_params: dict[str, str]
    ) -> None:
        r"""Test that a plain visit selects the first tariff without a warning."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, **query_params)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.selectbox[0].value == 'Tariff A', 'The first tariff is not selected!'
        assert at.query_params['tariff_id'] == ['1'], 'The address was not updated!'
        assert NOT_FOUND not in warning_text(at), 'A plain visit was warned about!'

    @pytest.mark.parametrize('tariff_id', ['999', 'abc'], ids=['non-existent', 'non-integer'])
    def test_an_unknown_tariff_is_warned_about(
        self, app: AppTest, superuser: stp.User, tariff_id: str
    ) -> None:
        r"""Test that an address that names no tariff warns and selects the first tariff."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, tariff_id=tariff_id)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert NOT_FOUND in warning_text(at), 'The unknown tariff was not warned about!'
        assert at.selectbox[0].value == 'Tariff A', 'The first tariff is not selected!'
        assert at.query_params['tariff_id'] == ['1'], 'The address was not corrected!'

    def test_the_tariff_and_tab_of_the_address_are_selected(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that a bookmarked address opens with its tariff and tab selected."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, tariff_id='2', tab='price-matrix')

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.selectbox[0].value == 'Tariff B', 'The tariff of the address is not selected!'
        assert at.query_params['tariff_id'] == ['2'], 'The tariff of the address was lost!'
        assert at.query_params['tab'] == ['price-matrix'], 'The tab of the address was lost!'
        assert not warning_text(at), 'A valid address was warned about!'

    def test_changing_the_tariff_updates_the_address(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that selecting another tariff carries it in the address of the page."""

        # Setup
        # ===========================================================
        at = open_tariff_design(app, user=superuser)

        # Exercise
        # ===========================================================
        at.selectbox[0].select('Tariff B').run()

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.selectbox[0].value == 'Tariff B', 'The selected tariff was lost!'
        assert at.query_params['tariff_id'] == ['2'], 'The address was not updated!'

    def test_an_unknown_tab_falls_back_to_the_first_tab(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that an address that names no tab silently opens the first tab."""

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, tab='no-such-tab')

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.query_params['tab'] == ['details'], 'The first tab is not active!'
        assert not warning_text(at), 'An unknown tab was warned about!'
