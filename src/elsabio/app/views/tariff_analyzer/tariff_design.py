# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The views of the Tariff Design page."""

# Standard library
from collections.abc import Callable
from enum import StrEnum
from typing import Self, cast
from zoneinfo import ZoneInfo

# Third party
import pandas as pd
import streamlit as st

# Local
from elsabio.app.components import ICON_INFO, bind_query_param, select_by_name
from elsabio.app.state import QueryParam
from elsabio.models.tariff_analyzer import TariffDataFrameModel

EXPLAINER = """\
A **Tariff** describes the prices that grid customers will pay for grid usage during its validity
period. It is composed of the parts described below.

A customer has a facility connected to the grid and a contract with the grid company that governs
how the facility can use the grid. **Customer Groups** are categories of facilities that share
contract characteristics such as fuse size or subscribed power. Customer groups are the basis for
how the prices of a tariff are set.

A **Tariff Cost Group** is a named part of a tariff that carries one set of prices. A customer
group belongs to at most one cost group in a tariff to avoid double counting. Several customer
groups can belong to the same cost group.

A **Tariff Component Type** describes what is charged for and how it is computed. For example a
fixed monthly fee, a price per kWh or a charge for exceeding the subscribed power. Component types
are shared by all tariffs. Each tariff selects the types it may use, which forms its **Component
Type Palette**.

A **Tariff Component** is the price of one component type within one cost group.
"""

NO_TARIFFS_DEFINED = """\
No tariffs are defined yet. Create one to start designing its content.
"""

TARIFF_NOT_FOUND = """\
The linked tariff could not be found. It may have been deleted, or the address of the page may
have been edited. The first tariff is selected as a fallback. Check that it is the one you want
to work with.
"""


class TariffDesignTab(StrEnum):
    r"""The tabs of the Tariff Design page, which are all scoped to one selected tariff.

    The value of a member is how the tab is carried in the address of the page.

    Members
    -------
    DETAILS
        The details of the tariff.

    COST_GROUPS
        The cost groups of the tariff.

    CUSTOMER_GROUP_ASSIGNMENT
        The assignment of customer groups to the cost groups of the tariff.

    PALETTE
        The component types the tariff may use.

    PRICE_MATRIX
        The prices of one component type across the cost groups of the tariff.

    PRICE_OVERVIEW
        Every price of the tariff in one read-only table.

    CALCULATE
        The calculation of the tariff and the runs it has made.
    """

    label: str
    description: str

    def __new__(cls, value: str, label: str, description: str) -> Self:
        r"""Create a tab from its address value, its label and its description."""

        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        member.description = description

        return member

    DETAILS = (
        'details',
        'Details',
        'The currency, validity period, high load period and description of the tariff.',
    )
    COST_GROUPS = (
        'cost-groups',
        'Cost groups',
        'The parts of the customer base that the tariff prices differently.',
    )
    CUSTOMER_GROUP_ASSIGNMENT = (
        'customer-group-assignment',
        'Customer group assignment',
        'Which customer groups belong to which cost group of the tariff.',
    )
    PALETTE = (
        'palette',
        'Palette',
        'The component types that the tariff may use when pricing.',
    )
    PRICE_MATRIX = (
        'price-matrix',
        'Price matrix',
        'The prices of one component type across every cost group of the tariff.',
    )
    PRICE_OVERVIEW = (
        'price-overview',
        'Price overview',
        'Every price of the tariff in one read-only table.',
    )
    CALCULATE = (
        'calculate',
        'Calculate',
        'Calculate the tariff over a period and follow the runs it has made.',
    )

    @classmethod
    def by_label(cls) -> dict[str, Self]:
        r"""Get the mapping of label to tab, in the order in which the tabs are presented."""

        return {tab.label: tab for tab in cls}


def title() -> None:
    r"""Render the title view of the Tariff Design page."""

    st.title('Tariff Design')
    st.subheader('Create, price and calculate the tariffs of the grid company')


def explainer(expanded: bool = False) -> None:
    r"""Render the view that explains how the objects of a tariff fit together.

    Parameters
    ----------
    expanded : bool, default False
        True to open the explainer and False to leave it for the reader to open.
        It is opened when there is nothing else on the page to read.
    """

    with st.expander('How a tariff fits together', icon=ICON_INFO, expanded=expanded):
        st.markdown(EXPLAINER)


def no_tariffs_defined() -> None:
    r"""Render the view of the Tariff Design page when no tariffs are defined."""

    st.info(NO_TARIFFS_DEFINED, icon=ICON_INFO)


def tariff_list(model: TariffDataFrameModel, timezone: ZoneInfo) -> None:
    r"""Render the view of the list of the tariffs.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs to list.

    timezone : zoneinfo.ZoneInfo
        The configured business timezone of the app used for displaying
        the datetime columns.
    """

    st.dataframe(
        _tariff_list_for_display(model=model),
        hide_index=True,
        width='stretch',
        column_order=(
            TariffDataFrameModel.c_name,
            TariffDataFrameModel.c_currency_iso_code,
            TariffDataFrameModel.c_validity_start,
            TariffDataFrameModel.c_validity_end,
            TariffDataFrameModel.c_last_edited_at,
        ),
        column_config={
            TariffDataFrameModel.c_name: st.column_config.TextColumn(label='Tariff'),
            TariffDataFrameModel.c_currency_iso_code: st.column_config.TextColumn(label='Currency'),
            TariffDataFrameModel.c_validity_start: st.column_config.DateColumn(label='Valid from'),
            TariffDataFrameModel.c_validity_end: st.column_config.DateColumn(label='Valid until'),
            TariffDataFrameModel.c_last_edited_at: st.column_config.DatetimeColumn(
                label='Last edited', timezone=str(timezone)
            ),
        },
    )


def _tariff_list_for_display(model: TariffDataFrameModel) -> pd.DataFrame:
    r"""Prepare the dataset of the tariffs for display in the list of the tariffs.

    The date of the validity_end column of `model` is converted from exclusive to
    inclusive to make it display the last day on which the tariff is valid.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs.

    Returns
    -------
    pandas.DataFrame
        The tariffs ready for display.
    """

    df = model.df

    return df.assign(
        **{
            TariffDataFrameModel.c_validity_end: (
                df[TariffDataFrameModel.c_validity_end] - pd.Timedelta(1, unit='D')
            ),
        }
    )


def select_tariff(model: TariffDataFrameModel) -> int | None:
    r"""Render the view that selects the tariff to work with.

    The selected tariff is carried in the address of the page. An address that names
    a tariff that does not exist defaults to the first tariff and a warning is issued.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs to select among.

    Returns
    -------
    int or None
        The tariff_id of the selected tariff and None if there are no tariffs to select among.
    """

    selection = select_by_name(
        label='Tariff',
        options=model.id_by_name(),
        query_param=QueryParam.TARIFF_ID,
        help='The tariff to work with. The selected tariff is part of the address of the page.',
        not_found_msg=TARIFF_NOT_FOUND,
    )

    return None if selection is None else selection.value


def tariff_tabs() -> TariffDesignTab:
    r"""Render the tabs of the Tariff Design page, which are scoped to the selected tariff.

    The active tab is carried in the address of the page, which is the source of truth in
    the same way as for the selected tariff. An address that names an unknown tab silently
    opens the first tab, since a wrong tab carries no risk of editing the wrong tariff.
    See :func:`elsabio.app.components.bind_query_param`.

    Switching tabs reruns the page to carry the active tab in the address and only the
    content of the open tab needs to be rendered.

    Returns
    -------
    TariffDesignTab
        The tab that is active after the view has been rendered.
    """

    binding = bind_query_param(
        options=TariffDesignTab.by_label(),
        query_param=QueryParam.TAB,
        # Calling the enum with an address value resolves the tab, but mypy reads the
        # signature of the call from the custom __new__ of the members.
        parse=cast(Callable[[str], TariffDesignTab], TariffDesignTab),
    )
    containers = st.tabs(binding.labels, key=binding.key, on_change=binding.on_change)

    for container, tab in zip(containers, TariffDesignTab, strict=True):
        if container.open:
            with container:
                st.info(f'{tab.description} Not built yet.', icon=ICON_INFO)

    return binding.selection.value
