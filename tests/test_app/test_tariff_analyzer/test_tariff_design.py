# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Wiring tests for the page `app._pages.tariff_analyzer.tariff_design`

The page is reached the way a user reaches it: the app is started from its router and the page
is selected in the navigation. A page that is not part of the navigation of the signed in user
cannot be selected, and the router then falls back to its default page, Sign in.

The one exception is :class:`TestTariffDesignPageGuard`, which runs the page without the router of
the app to prove the guard of the page itself.
"""

# Standard library
from datetime import datetime
from pathlib import Path

# Third party
import pandas as pd
import pytest
import streamlit_passwordless as stp
from streamlit.proto.WidgetStates_pb2 import WidgetState
from streamlit.testing.v1 import AppTest

# Local
from elsabio.app import APP_PATH
from elsabio.models.tariff_analyzer import TariffDataFrameModel
from tests.test_app.conftest import APP_TEST_TIMEOUT

PAGE = '_pages/tariff_analyzer/tariff_design.py'
TITLE = 'Tariff Design'
NOT_FOUND = 'The linked tariff could not be found'

# A signed in user on Sign in is offered to register a new passkey, which no other page offers.
SIGN_IN_MARKER = 'Register a new passkey'

# A stand-in for the router of the app that offers the Tariff Design page to every user,
# so that the guard of the page is the only thing that can refuse a user.
ROUTER_WITHOUT_GATE = """\
import streamlit as st

from elsabio.app._pages import Pages

pages = [st.Page(page=Pages.TARIFF_DESIGN, default=True), st.Page(page=Pages.SIGN_IN)]
st.navigation(pages, position='hidden').run()
"""


@pytest.fixture
def page_without_router(app: AppTest, tmp_path: Path) -> AppTest:  # noqa: ARG001
    r"""An app test that runs the Tariff Design page without the router of the app.

    The page is run from :data:`ROUTER_WITHOUT_GATE`, which does not leave the page out of the
    navigation of any user. The pages of the app are linked next to the stand-in router, so that
    the page and its redirect to Sign in resolve their pages as they do in the app. `app` is
    requested for the environment of the app, i.e. its config, database and fresh modules.

    Returns
    -------
    streamlit.testing.v1.AppTest
        The app test of the Tariff Design page.
    """

    (tmp_path / '_pages').symlink_to(APP_PATH.parent / '_pages', target_is_directory=True)
    router_path = tmp_path / 'router.py'
    router_path.write_text(ROUTER_WITHOUT_GATE)

    return AppTest.from_file(str(router_path), default_timeout=APP_TEST_TIMEOUT)


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


def landed_on_sign_in(at: AppTest) -> bool:
    r"""Check if the signed in user landed on the Sign in page."""

    return any(SIGN_IN_MARKER in m.value for m in at.markdown)


def switch_tab(at: AppTest, label: str) -> AppTest:
    r"""Switch to the tab of the Tariff Design page with `label` the way the browser does.

    AppTest cannot interact with ``st.tabs``, so the widget state that the browser sends when
    the user opens a tab is added to the widget states of the page, which runs the change
    callback of the tab bar in the same way as a click by the user.

    Parameters
    ----------
    at : streamlit.testing.v1.AppTest
        The app test of the web app after the Tariff Design page has been run.

    label : str
        The label of the tab to switch to.

    Returns
    -------
    streamlit.testing.v1.AppTest
        `at` after the page has been run again.
    """

    tab_bar = next(node for node in at.main if node.type == 'tab_container')
    widget_states = at.main.root.get_widget_states()
    widget_states.widgets.append(WidgetState(id=tab_bar.proto.tab_container.id, string_value=label))

    return at._run(widget_states)


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
    def test_a_user_and_a_viewer_land_on_sign_in(
        self,
        app: AppTest,
        fixture_name: str,
        request: pytest.FixtureRequest,
    ) -> None:
        r"""Test that a User and a Viewer who open the address of the page land on Sign in.

        AppTest does not expose the entries of the navigation, so landing on Sign in, the
        default page of the router, is the proof that the page is not among them.
        """

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=request.getfixturevalue(fixture_name))

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert not page_rendered(at), 'The Tariff Design page was rendered!'
        assert landed_on_sign_in(at), 'The user did not land on Sign in!'


class TestTariffDesignPageGuard:
    r"""Tests of the guard of the Tariff Design page itself, without the router of the app."""

    @pytest.mark.parametrize('fixture_name', ['user', 'viewer'])
    def test_a_user_and_a_viewer_are_redirected_to_sign_in(
        self, page_without_router: AppTest, fixture_name: str, request: pytest.FixtureRequest
    ) -> None:
        r"""Test that the page redirects a User and a Viewer to Sign in."""

        # Setup
        # ===========================================================
        at = page_without_router
        at.session_state[stp.SK_USER] = request.getfixturevalue(fixture_name)

        # Exercise
        # ===========================================================
        at.run()

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert not page_rendered(at), 'The Tariff Design page was rendered!'
        assert landed_on_sign_in(at), 'The user was not redirected to Sign in!'

    def test_a_superuser_gets_the_page(
        self, page_without_router: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that the page lets a Superuser through.

        It proves that the refusal of a User and a Viewer comes from the guard of the page
        and not from how the page is run without the router.
        """

        # Setup
        # ===========================================================
        at = page_without_router
        at.session_state[stp.SK_USER] = superuser

        # Exercise
        # ===========================================================
        at.run()

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert page_rendered(at), 'The Tariff Design page was not rendered!'
        assert not landed_on_sign_in(at), 'The Superuser was redirected to Sign in!'


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

    def test_a_tariff_id_with_a_leading_zero_selects_the_tariff(
        self, app: AppTest, superuser: stp.User
    ) -> None:
        r"""Test that an address that names a tariff in a non-standard form selects it.

        The address is corrected to the standard form without a warning, since it
        names the right tariff.
        """

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, tariff_id='02')

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.selectbox[0].value == 'Tariff B', 'The tariff of the address is not selected!'
        assert at.query_params['tariff_id'] == ['2'], 'The address was not corrected!'
        assert not warning_text(at), 'A known tariff was warned about!'

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

    def test_switching_tabs_updates_the_address(self, app: AppTest, superuser: stp.User) -> None:
        r"""Test that switching to another tab and back carries the open tab in the address."""

        # Setup
        # ===========================================================
        at = open_tariff_design(app, user=superuser)

        # Exercise
        # ===========================================================
        switch_tab(at, label='Palette')

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.query_params['tab'] == ['palette'], 'The address does not name the new tab!'

        messages = ' '.join(i.value for i in at.info)
        assert 'The component types that the tariff may use' in messages, 'The tab is not open!'

        # Exercise
        # ===========================================================
        switch_tab(at, label='Details')

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'
        assert at.query_params['tab'] == ['details'], 'The address does not name the first tab!'

    @pytest.mark.parametrize(
        ('query_params', 'open_tab', 'closed_tab'),
        [
            ({}, 'The currency, validity period', 'The prices of one component type'),
            (
                {'tab': 'price-matrix'},
                'The prices of one component type',
                'The currency, validity period',
            ),
        ],
        ids=['default-tab', 'tab-of-the-address'],
    )
    def test_only_the_open_tab_is_rendered(
        self,
        app: AppTest,
        superuser: stp.User,
        query_params: dict[str, str],
        open_tab: str,
        closed_tab: str,
    ) -> None:
        r"""Test that the content of a tab is only rendered while the tab is open.

        Switching tabs reruns the page, so rendering only the open tab keeps a rerun
        from doing the work of every tab.
        """

        # Exercise
        # ===========================================================
        at = open_tariff_design(app, user=superuser, **query_params)

        # Verify
        # ===========================================================
        assert not at.exception, f'The page raised an exception! {at.exception}'

        messages = ' '.join(i.value for i in at.info)
        assert open_tab in messages, 'The open tab was not rendered!'
        assert closed_tab not in messages, 'A closed tab was rendered!'

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
