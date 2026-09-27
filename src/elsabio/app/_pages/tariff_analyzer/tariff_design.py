# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the Tariff Design page."""

# Third party
import streamlit as st

# Local
from elsabio.app._pages import REQUIRED_ROLES, Pages
from elsabio.app.auth import authorized
from elsabio.app.controllers.tariff_analyzer.tariff_design import controller
from elsabio.app.info import APP_HOME_PAGE_URL, APP_ISSUES_PAGE_URL, MAINTAINER_INFO
from elsabio.app.resources import cm, session_factory

ABOUT = f"""Create, price and calculate the tariffs of the grid company.

{MAINTAINER_INFO}
"""


@authorized(role=REQUIRED_ROLES[Pages.TARIFF_DESIGN], redirect=Pages.SIGN_IN)
def tariff_design_page() -> None:
    r"""Run the Tariff Design page of the ElSabio web app."""

    st.set_page_config(
        page_title='ElSabio - Tariff Design',
        layout='wide',
        menu_items={
            'About': ABOUT,
            'Get Help': APP_HOME_PAGE_URL,
            'Report a bug': APP_ISSUES_PAGE_URL,
        },
        initial_sidebar_state='auto',
    )

    with session_factory() as session:
        controller(session=session, timezone=cm.timezone)


if __name__ in {'__main__', '__page__'}:
    tariff_design_page()
