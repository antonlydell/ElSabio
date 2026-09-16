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

    value = st.query_params.get(param)

    return value if value else None


def get_int_query_param(param: QueryParam) -> int | None:
    r"""Get the integer value of a query parameter from the address of the current page.

    A value that is not an integer is treated as if the query parameter was not supplied,
    since the address of a page can be edited by hand.

    Parameters
    ----------
    param : elsabio.app.state.QueryParam
        The query parameter to get the value of.

    Returns
    -------
    int or None
        The value of `param` and None if `param` is missing or not an integer.
    """

    if (value := get_query_param(param)) is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def get_enum_query_param[E: StrEnum](param: QueryParam, members: type[E], default: E) -> E:
    r"""Get the member of an enum that a query parameter names.

    A query parameter that names no member is treated as if it was not supplied,
    since the address of a page can be edited by hand.

    Parameters
    ----------
    param : elsabio.app.state.QueryParam
        The query parameter to get the value of.

    members : type[E]
        The enum to look the value of `param` up in.

    default : E
        The member to fall back on if `param` is missing or names no member.

    Returns
    -------
    E
        The member that `param` names and `default` if it names none.
    """

    if (value := get_query_param(param)) is None:
        return default

    try:
        return members(value)
    except ValueError:
        return default


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
