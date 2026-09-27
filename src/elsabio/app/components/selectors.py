# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Selector components.

A domain expert recognizes the objects they work with by name and never by the primary key
of a database table. The selectors of this module therefore present names and return ID:s,
and they carry the selection in the address of the page rather than in the session state,
which makes a page linkable and survivable across a browser refresh.

The selectors of this module are generic and module-agnostic: they know nothing about the
entities they select among. A selector that knows about the entities of a module, e.g. one that
selects a tariff, belongs to the views of that module and is built on the selectors of this module.
"""

# Standard library
from collections.abc import Mapping

# Third party
import streamlit as st

# Local
from elsabio.app.components.query_param import OnChange, Selection, query_param_widget
from elsabio.app.state import QueryParam, set_query_param


def select_by_name(
    label: str,
    options: Mapping[str, int],
    query_param: QueryParam,
    help: str | None = None,  # noqa: A002
) -> Selection[int] | None:
    r"""Render a selector that presents names and returns the ID of the selected name.

    The selector is generic and module-agnostic, so reuse it to select among any objects
    that have a name and an ID rather than writing a copy for a specific entity.

    The selection is carried by `query_param` in the address of the page, which is the
    source of truth. An address without `query_param` selects the first option, and so
    does an address that names an object that does not exist, which is reported through
    :attr:`Selection.unknown <elsabio.app.components.Selection.unknown>` for the caller
    to act on. See :func:`elsabio.app.components.query_param_widget`.

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
    elsabio.app.components.Selection[int] or None
        The ID of the selected name and if the address named an unknown ID.
        None if `options` is empty.
    """

    if not options:
        set_query_param(query_param, None)
        return None

    def selectbox(names: list[str], key: str, on_change: OnChange) -> str:
        return st.selectbox(label=label, options=names, key=key, help=help, on_change=on_change)

    _, selection = query_param_widget(widget=selectbox, options=options, query_param=query_param)

    return selection
