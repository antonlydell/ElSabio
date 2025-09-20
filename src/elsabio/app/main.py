# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the ElSabio web app."""

# Standard library
from pathlib import Path

# Third party
import streamlit as st

# Local
from elsabio.app._pages import Pages

APP_PATH = Path(__file__)


def main() -> None:
    r"""The page router of the ElSabio web app."""

    pages = [st.Page(page=Pages.HOME, title='Home')]
    page = st.navigation(pages, position='top')

    page.run()


if __name__ == '__main__':
    main()
