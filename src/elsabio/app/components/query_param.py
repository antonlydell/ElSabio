# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The binding of a selection widget to a query parameter of the address of the page.

The address of the page is the source of truth of the selection, which makes a page linkable
and survivable across a browser refresh. Every widget that carries its selection in the address
is built on :func:`query_param_widget`, so that they all read and write the address the same way.
"""

# Standard library
from collections.abc import Callable, Mapping
from typing import NamedTuple

# Third party
import streamlit as st

# Local
from elsabio.app.state import QueryParam, get_query_param, set_query_param

type OnChange = Callable[[], None]


class Selection[T](NamedTuple):
    r"""The selection of a widget that is bound to a query parameter.

    Parameters
    ----------
    value : T
        The selected value.

    unknown : bool
        True if the address named a value that could not be resolved to any of the
        options and the selection fell back to the first option. A query parameter
        that is missing from the address, or empty, is no selection rather than an unknown one.
    """

    value: T
    unknown: bool


def query_param_widget[T, W](
    widget: Callable[[list[str], str, OnChange], W],
    options: Mapping[str, T],
    query_param: QueryParam,
) -> tuple[W, Selection[T]]:
    r"""Render a selection widget that carries its selection in a query parameter.

    The widget is bound to `query_param` in four steps:

    1. Read `query_param` from the address and resolve it to an option. A value that
       resolves to no option, or a missing or empty `query_param`, selects the first option.
    2. Seed the session state of the widget with the resolved option.
    3. Render the widget with a change callback that writes a changed selection to the
       address before the page is rendered again, so that editing the address by hand
       moves the selection rather than the other way around.
    4. Write the resolved selection back to the address.

    Parameters
    ----------
    widget : Callable[[list[str], str, Callable[[], None]], W]
        A function that renders the widget from its labels, its session state key and its
        change callback, e.g. ``lambda labels, key, on_change: st.selectbox('Label', labels,
        key=key, on_change=on_change)``. It must pass the key and the change callback on to
        the widget.

    options : Mapping[str, T]
        The mapping of label to value of the options to select among, in the order in which
        they are presented. A value is carried in the address as its string representation.
        Must not be empty.

    query_param : elsabio.app.state.QueryParam
        The query parameter that carries the selection in the address of the page. It also
        derives the session state key of the widget, so one query parameter binds one widget.

    Returns
    -------
    widget : W
        The return value of `widget`.

    selection : elsabio.app.components.Selection[T]
        The selected value and if the address named a value that could not be resolved.
    """

    labels = list(options)
    label_by_param_value = {str(value): label for label, value in options.items()}
    key = f'query-param-{query_param}'

    param_value = get_query_param(query_param) or None  # An empty value is no selection.
    label = label_by_param_value.get(param_value, labels[0]) if param_value else labels[0]
    unknown = param_value is not None and param_value not in label_by_param_value

    if st.session_state.get(key) != label:
        st.session_state[key] = label

    def carry_selection_in_address() -> None:
        set_query_param(query_param, str(options[st.session_state[key]]))

    widget_output = widget(labels, key, carry_selection_in_address)

    value = options[st.session_state[key]]
    set_query_param(query_param, str(value))

    return widget_output, Selection(value=value, unknown=unknown)
