# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The selection state of a page, carried in the address of the page.

Carrying the selection in the address rather than in the session state makes a page
linkable, shareable and survivable across a browser refresh.
"""

# Standard library
from enum import StrEnum

# Third party
import streamlit as st


class QueryParam(StrEnum):
    r"""The query parameters that carry the selection state of a page.

    Members
    -------
    TAB
        The active tab of a page.

    TARIFF_ID
        The selected tariff.
    """

    TAB = 'tab'
    TARIFF_ID = 'tariff_id'


def get_query_param(param: QueryParam) -> str | None:
    r"""Get the value of a query parameter from the address of the current page.

    Parameters
    ----------
    param : elsabio.app.state.QueryParam
        The query parameter to get the value of.

    Returns
    -------
    str or None
        The value of `param` and None if `param` is not part of the address.
    """

    return st.query_params.get(param)


def set_query_param(param: QueryParam, value: str | int | None) -> None:
    r"""Set the value of a query parameter in the address of the current page.

    Parameters
    ----------
    param : elsabio.app.state.QueryParam
        The query parameter to set the value of.

    value : str or int or None
        The value to set. If None `param` is removed from the address of the page.
    """

    if value is None:
        st.query_params.pop(param, None)
    else:
        st.query_params[param] = str(value)
