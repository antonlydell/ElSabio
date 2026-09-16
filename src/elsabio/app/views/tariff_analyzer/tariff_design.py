# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The views of the Tariff Design page."""

# Standard library
from enum import StrEnum

# Third party
import streamlit as st

# Local
from elsabio.app.components import ICON_INFO, id_by_name, select_by_name
from elsabio.app.state import QueryParam, get_enum_query_param, set_query_param
from elsabio.models.tariff_analyzer import TariffDataFrameModel

SK_TAB = 'tariff-design-tab'

EXPLAINER = """\
A **Tariff** is a complete price sheet for grid usage, in one currency and bounded by a validity
period. Everything below belongs to one tariff.

A **Tariff Cost Group** is a named part of a tariff that carries one set of prices. **Customer
Groups** — categories of facilities that share contract characteristics such as fuse size or
subscribed power — are assigned to the cost groups, and each customer group belongs to at most one
cost group of a tariff. Assigning one to two cost groups of the same tariff would count its
facilities twice and is therefore forbidden.

A **Tariff Component Type** names what is charged for and how it is computed — a fixed monthly fee,
a price per kWh, a charge for exceeding the subscribed power. Types are defined once for the whole
installation. Each tariff selects the types it may use, its **Component Type Palette**, so that
pricing is done from a relevant shortlist rather than from every type in the installation.

A **Tariff Component** is the price itself: one component type priced within one cost group,
together with the months it is valid and its overshoot limit. It is the leaf that a calculation
multiplies.
"""

NO_TARIFFS_DEFINED = """\
No tariffs are defined yet. A tariff is the price sheet that everything else on this page hangs
off, so create one to get started. Until then there is nothing to design.
"""


class TariffDesignTab(StrEnum):
    r"""The tabs of the Tariff Design page, which are all scoped to one selected tariff.

    The value of a member is how the tab is carried in the address of the page and
    the label of a tab is derived from it.

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

    DETAILS = 'details'
    COST_GROUPS = 'cost-groups'
    CUSTOMER_GROUP_ASSIGNMENT = 'customer-group-assignment'
    PALETTE = 'palette'
    PRICE_MATRIX = 'price-matrix'
    PRICE_OVERVIEW = 'price-overview'
    CALCULATE = 'calculate'

    @property
    def label(self) -> str:
        r"""The label of the tab as it is presented to the user."""

        return self.replace('-', ' ').capitalize()


TABS_BY_LABEL: dict[str, TariffDesignTab] = {tab.label: tab for tab in TariffDesignTab}

TAB_DESCRIPTIONS: dict[TariffDesignTab, str] = {
    TariffDesignTab.DETAILS: (
        'The currency, validity period, high load period and description of the tariff.'
    ),
    TariffDesignTab.COST_GROUPS: (
        'The parts of the customer base that the tariff prices differently.'
    ),
    TariffDesignTab.CUSTOMER_GROUP_ASSIGNMENT: (
        'Which customer groups belong to which cost group of the tariff.'
    ),
    TariffDesignTab.PALETTE: 'The component types that the tariff may use when pricing.',
    TariffDesignTab.PRICE_MATRIX: (
        'The prices of one component type across every cost group of the tariff.'
    ),
    TariffDesignTab.PRICE_OVERVIEW: 'Every price of the tariff in one read-only table.',
    TariffDesignTab.CALCULATE: (
        'Calculate the tariff over a period and follow the runs it has made.'
    ),
}


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


def tariff_list(model: TariffDataFrameModel) -> None:
    r"""Render the view of the list of the tariffs.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs to list.
    """

    m = TariffDataFrameModel

    st.dataframe(
        model.df,
        hide_index=True,
        width='stretch',
        column_order=(
            m.c_name,
            m.c_currency_iso_code,
            m.c_validity_start,
            m.c_validity_end,
            m.c_last_edited_at,
        ),
        column_config={
            m.c_name: st.column_config.TextColumn(label='Tariff'),
            m.c_currency_iso_code: st.column_config.TextColumn(label='Currency'),
            m.c_validity_start: st.column_config.DateColumn(label='Valid from'),
            m.c_validity_end: st.column_config.DateColumn(label='Valid until'),
            m.c_last_edited_at: st.column_config.DatetimeColumn(label='Last edited (UTC)'),
        },
    )


def select_tariff(model: TariffDataFrameModel) -> int | None:
    r"""Render the view that selects the tariff to work with.

    The selected tariff is carried in the address of the page.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffDataFrameModel
        The dataset of the tariffs to select among.

    Returns
    -------
    int or None
        The tariff_id of the selected tariff and None if there are no tariffs to select among.
    """

    return select_by_name(
        label='Tariff',
        options=id_by_name(
            df=model.df,
            name_col=TariffDataFrameModel.c_name,
            id_col=TariffDataFrameModel.c_tariff_id,
        ),
        query_param=QueryParam.TARIFF_ID,
        help='The tariff to work with. The selected tariff is part of the address of the page.',
    )


def tariff_tabs() -> TariffDesignTab:
    r"""Render the tabs of the Tariff Design page, which are scoped to the selected tariff.

    The active tab is carried in the address of the page, which is the source of truth in
    the same way as for the selected tariff. See :func:`elsabio.app.components.select_by_name`.

    Returns
    -------
    TariffDesignTab
        The tab that is active after the view has been rendered.
    """

    active_tab = get_enum_query_param(
        param=QueryParam.TAB, members=TariffDesignTab, default=TariffDesignTab.DETAILS
    )

    if st.session_state.get(SK_TAB) != active_tab.label:
        st.session_state[SK_TAB] = active_tab.label

    tabs = st.tabs(
        [tab.label for tab in TariffDesignTab],
        default=active_tab.label,
        key=SK_TAB,
        on_change=_carry_active_tab_in_address,
    )

    for container, tab in zip(tabs, TariffDesignTab, strict=True):
        with container:
            st.info(f'{TAB_DESCRIPTIONS[tab]} Not built yet.', icon=ICON_INFO)

    active_tab = TABS_BY_LABEL[st.session_state[SK_TAB]]
    set_query_param(QueryParam.TAB, active_tab)

    return active_tab


def _carry_active_tab_in_address() -> None:
    r"""Write a changed active tab to the address of the page.

    Runs before the page is rendered again, so that the address is up to
    date by the time :func:`tariff_tabs` reads it back.
    """

    set_query_param(QueryParam.TAB, TABS_BY_LABEL[st.session_state[SK_TAB]])
