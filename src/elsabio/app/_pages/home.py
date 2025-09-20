# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the home page."""

# Third party
import streamlit as st

# Local
from elsabio.app.info import (
    APP_HOME_PAGE_URL,
    APP_ISSUES_PAGE_URL,
    MAINTAINER_INFO,
)

ABOUT = f"""\
The Simple Electricity Meter Data Analysis Platform

{MAINTAINER_INFO}
"""


def home_page() -> None:
    r"""Run the home page of the ElSabio web app."""

    st.set_page_config(
        page_title='ElSabio - Home',
        page_icon='⚡',
        layout='wide',
        menu_items={
            'About': ABOUT,
            'Get Help': APP_HOME_PAGE_URL,
            'Report a bug': APP_ISSUES_PAGE_URL,
        },
        initial_sidebar_state='auto',
    )

    st.title('ElSabio')
    st.subheader('The Simple Electricity Meter Data Analysis Platform')


if __name__ in {'__main__', '__page__'}:
    home_page()
