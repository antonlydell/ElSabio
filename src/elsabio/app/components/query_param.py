# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The binding of a single choice component to a query parameter of the address of the page.

The address of the page is the source of truth of the choice, which makes a page linkable
and survivable across a browser refresh. Every component that carries its choice in the
address is bound with :func:`bind_query_param`, so that they all read and write the address
the same way.

A binding is used in three steps, in this order::

    binding = bind_query_param(options=options, query_param=QueryParam.TARIFF_ID, parse=int)
    st.selectbox('Tariff', binding.labels, key=binding.key, on_change=binding.on_change)
    selection = binding.selection()

The component must be rendered with the key and the change callback of the binding, or the
choice will not follow the user. Any single choice component that accepts ``key`` and
``on_change`` can be bound, e.g. ``st.selectbox``, ``st.radio``, ``st.segmented_control``,
``st.pills`` and ``st.tabs``.
"""

# Standard library
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import NamedTuple

# Third party
import streamlit as st

# Local
from elsabio.app.state import QueryParam, get_query_param, set_query_param


class Selection[T](NamedTuple):
    r"""The choice of a component that is bound to a query parameter.

    Parameters
    ----------
    value : T
        The chosen value.

    unknown : bool
        True if the address named a value that could not be resolved to any of the
        options and the choice fell back to the first option. A query parameter that
        is missing from the address, or empty, is no choice rather than an unknown one.
    """

    value: T
    unknown: bool


@dataclass(frozen=True)
class QueryParamBinding[T]:
    r"""A single choice component bound to a query parameter of the address of the page.

    Created by :func:`bind_query_param`, which has read the address and seeded the
    session state of the component. See the module documentation for how to use it.

    Parameters
    ----------
    options : Mapping[str, T]
        The mapping of label to value of the options to choose among.

    query_param : elsabio.app.state.QueryParam
        The query parameter that carries the choice in the address of the page.

    key : str
        The session state key to render the component with.

    unknown : bool
        True if the address named a value that could not be resolved to any of the options.
    """

    options: Mapping[str, T]
    query_param: QueryParam
    key: str
    unknown: bool

    @property
    def labels(self) -> list[str]:
        r"""The labels of the options to render the component with, in order."""

        return list(self.options)

    def on_change(self) -> None:
        r"""Write a changed choice to the address before the page is rendered again.

        The change callback to render the component with, so that the address is up to date
        by the time :func:`bind_query_param` reads it on the next run of the page.
        """

        set_query_param(self.query_param, str(self.options[st.session_state[self.key]]))

    def selection(self) -> Selection[T]:
        r"""Get the choice of the rendered component and write it back to the address.

        Writing it back puts the choice in the address on a plain visit and corrects an
        address that named an unknown value or a known value in a non-standard form.

        Returns
        -------
        elsabio.app.components.Selection[T]
            The chosen value and if the address named a value that could not be resolved.
        """

        value = self.options[st.session_state[self.key]]
        set_query_param(self.query_param, str(value))

        return Selection(value=value, unknown=self.unknown)


def bind_query_param[T](
    options: Mapping[str, T], query_param: QueryParam, parse: Callable[[str], T]
) -> QueryParamBinding[T]:
    r"""Bind a single choice component to a query parameter of the address of the page.

    Reads `query_param` from the address, resolves it to an option and seeds the
    session state of the component with it. Render the component with the key and the
    change callback of the returned binding and then call its
    :meth:`~QueryParamBinding.selection`.

    Parameters
    ----------
    options : Mapping[str, T]
        The mapping of label to value of the options to choose among, in the order in
        which they are presented. A value is carried in the address as its string
        representation. Must not be empty.

    query_param : elsabio.app.state.QueryParam
        The query parameter that carries the choice in the address of the page. It also
        derives the session state key of the component, so one query parameter binds
        one component of a page.

    parse : Callable[[str], T]
        The function that parses the value of `query_param` into the value of an option,
        e.g. ``int`` or a lookup of an enum member. It should raise :exc:`ValueError` if the value
        cannot be parsed.

    Returns
    -------
    elsabio.app.components.QueryParamBinding[T]
        The binding to render the component with.
    """

    value, unknown = resolve_query_param(
        param_value=get_query_param(query_param), values=list(options.values()), parse=parse
    )
    label = next(label for label, option in options.items() if option == value)
    key = f'query-param-{query_param}'

    if st.session_state.get(key) != label:
        st.session_state[key] = label

    return QueryParamBinding(options=options, query_param=query_param, key=key, unknown=unknown)


def resolve_query_param[T](
    param_value: str | None, values: list[T], parse: Callable[[str], T]
) -> tuple[T, bool]:
    r"""Resolve the value of a query parameter to one of the values of the options.

    A missing or empty value is no choice and resolves to the first value. A value that
    cannot be parsed, or that parses into a value that is not among `values`, is unknown
    and also resolves to the first value.

    Parameters
    ----------
    param_value : str or None
        The value of the query parameter and None if it is missing from the address.

    values : list[T]
        The values of the options, in order. Must not be empty.

    parse : Callable[[str], T]
        The function that parses `param_value` into a value.

    Returns
    -------
    value : T
        The resolved value.

    unknown : bool
        True if `param_value` could not be resolved to any of `values`.

    Examples
    --------
    >>> resolve_query_param(param_value='02', values=[1, 2], parse=int)
    (2, False)
    >>> resolve_query_param(param_value='999', values=[1, 2], parse=int)
    (1, True)
    >>> resolve_query_param(param_value='abc', values=[1, 2], parse=int)
    (1, True)
    >>> resolve_query_param(param_value='', values=[1, 2], parse=int)
    (1, False)
    """

    first = values[0]

    if not param_value:
        return first, False

    try:
        value = parse(param_value)
    except ValueError:
        return first, True

    return (value, False) if value in values else (first, True)
