# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Helpers that reach into Streamlit where the public API of AppTest falls short.

The helpers depend on parts of Streamlit that are not public, e.g. private methods,
protobuf messages and the JSON layout of element configs. These may change in any
release of Streamlit. All such dependencies are gathered in this module so that an
upgrade of Streamlit breaks one place with a clear cause. Tests should use these
helpers rather than reach into Streamlit themselves.
"""

# Standard library
import json

# Third party
from streamlit.proto.WidgetStates_pb2 import WidgetState
from streamlit.runtime.state.common import user_key_from_element_id
from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.element_tree import Dataframe


def address_value(at: AppTest, query_param: str) -> str | None:
    r"""Get the value of a query parameter from the address after the app has been run.

    A query parameter that occurs once is a string in :attr:`AppTest.query_params`,
    while a repeated one is a list of strings. The value is read the way ``st.query_params``
    reads it, where a repeated query parameter yields its last value.

    Parameters
    ----------
    at : streamlit.testing.v1.AppTest
        The app test after the app has been run.

    query_param : str
        The query parameter to get the value of.

    Returns
    -------
    str or None
        The value of `query_param` and None if it is not part of the address.
    """

    value = at.query_params.get(query_param)

    if isinstance(value, list):
        return value[-1] if value else None

    return value


def switch_tab(at: AppTest, key: str, label: str) -> AppTest:
    r"""Switch to the tab with `label` of the tab bar with `key` the way the browser does.

    AppTest has no way to click a tab bar made by ``st.tabs``. Instead, this helper sends
    the message that the browser sends when a user opens a tab: a widget state that holds
    the new value of the tab bar. Streamlit then treats it as a real click. It runs the
    change callback of the tab bar and reruns the app.

    Parameters
    ----------
    at : streamlit.testing.v1.AppTest
        The app test after the app has been run.

    key : str
        The key that the tab bar was rendered with.

    label : str
        The label of the tab to switch to.

    Returns
    -------
    streamlit.testing.v1.AppTest
        `at` after the app has been run again.
    """

    # The widget id of the tab bar ends with its key, but its hash cannot be computed up front.
    tab_bar_id = next(
        (
            node.proto.tab_container.id
            for node in at.main
            if node.type == 'tab_container'
            and user_key_from_element_id(node.proto.tab_container.id) == key
        ),
        None,
    )
    assert tab_bar_id is not None, f'The app did not render the tab bar with key {key!r}!'

    widget_states = at.main.root.get_widget_states()
    widget_states.widgets.append(WidgetState(id=tab_bar_id, string_value=label))

    return at._run(widget_states)


def column_timezone(df: Dataframe, column: str) -> str | None:
    r"""Get the timezone that a datetime column of a dataframe is rendered in.

    The timezone is set by the ``timezone`` parameter of ``st.column_config.DatetimeColumn``.
    AppTest exposes the column config only as the JSON that is sent to the browser.

    Parameters
    ----------
    df : streamlit.testing.v1.element_tree.Dataframe
        The rendered dataframe.

    column : str
        The name of the datetime column.

    Returns
    -------
    str or None
        The timezone of `column` and None if `column` has no timezone configured.

    Raises
    ------
    AssertionError
        If `df` has no configuration for `column`.
    """

    column_config = json.loads(df.proto.columns)
    assert column in column_config, f'The dataframe has no config for column {column!r}!'

    timezone: str | None = column_config[column].get('type_config', {}).get('timezone')

    return timezone
