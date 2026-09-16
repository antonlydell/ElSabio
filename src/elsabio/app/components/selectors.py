# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Selector components.

A domain expert recognizes the objects they work with by name and never by the primary key
of a database table. The selectors of this module therefore present names and return ID:s,
and they carry the selection in the address of the page rather than in the session state,
which makes a page linkable and survivable across a browser refresh.
"""

# Standard library
from collections.abc import Mapping

# Third party
import pandas as pd
import streamlit as st

# Local
from elsabio.app.state import QueryParam, get_int_query_param, set_query_param


def id_by_name(df: pd.DataFrame, name_col: str, id_col: str) -> dict[str, int]:
    r"""Create a mapping of name to ID from a DataFrame.

    The order of the rows of `df` is preserved, since it determines
    the order of the options presented by a selector.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to create the mapping from.

    name_col : str
        The name of the column of `df` that holds the names.

    id_col : str
        The name of the column of `df` that holds the ID:s.

    Returns
    -------
    dict[str, int]
        The mapping of name to ID.
    """

    return {str(name): int(id_) for name, id_ in zip(df[name_col], df[id_col], strict=True)}


def select_by_name(
    label: str,
    options: Mapping[str, int],
    query_param: QueryParam,
    help: str | None = None,  # noqa: A002
) -> int | None:
    r"""Render a selector that presents names and returns the ID of the selected name.

    The selection is carried by `query_param` in the address of the page, which is the
    source of truth: an address that selects an object that does not exist, and an address
    without `query_param`, both select the first option. Changing the selection updates the
    address before the page is rendered again, so that editing the address by hand moves
    the selection rather than the other way around.

    Parameters
    ----------
    label : str
        The label of the selector.

    options : Mapping[str, int]
        The mapping of name to ID of the objects to select among. The order of
        `options` is the order in which the names are presented.

    query_param : elsabio.app.state.QueryParam
        The query parameter that carries the selection in the address of the page.

    help : str or None, default None
        An optional tooltip that explains the selector.

    Returns
    -------
    int or None
        The ID of the selected name and None if `options` is empty.
    """

    names = list(options)
    key = f'select-by-name-{query_param}'

    if not names:
        set_query_param(query_param, None)
        return None

    name_by_id = {id_: name for name, id_ in options.items()}
    selected_id = get_int_query_param(query_param)
    selected_name = names[0] if selected_id is None else name_by_id.get(selected_id, names[0])

    if st.session_state.get(key) != selected_name:
        st.session_state[key] = selected_name

    name = st.selectbox(
        label=label,
        options=names,
        key=key,
        help=help,
        on_change=_carry_selection_in_address,
        kwargs={'key': key, 'options': options, 'query_param': query_param},
    )
    selected_id = options[name]
    set_query_param(query_param, selected_id)

    return selected_id


def _carry_selection_in_address(
    key: str, options: Mapping[str, int], query_param: QueryParam
) -> None:
    r"""Write a changed selection to the address of the page.

    Runs before the page is rendered again, so that the address is up to date by the
    time :func:`select_by_name` reads it back.

    Parameters
    ----------
    key : str
        The key of the selector in the session state.

    options : Mapping[str, int]
        The mapping of name to ID of the objects to select among.

    query_param : elsabio.app.state.QueryParam
        The query parameter that carries the selection in the address of the page.
    """

    set_query_param(query_param, options[st.session_state[key]])
