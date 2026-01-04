# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Functions for working with the `CustomerGroup` related models of Tariff Analyzer."""

# Standard library
from datetime import date

# Third party
import pandas as pd
from sqlalchemy import and_, select

# Local
from elsabio.core import OperationResult
from elsabio.database.core import (
    Session,
    bulk_insert_to_table,
    bulk_update_table,
    load_sql_query_as_dataframe,
)
from elsabio.database.models.tariff_analyzer import (
    CustomerGroup,
    CustomerGroupMappingStrategy,
    FacilityCustomerGroupLink,
)
from elsabio.models.tariff_analyzer import (
    CustomerGroupDataFrameModel,
    FacilityCustomerGroupLinkDataFrameModel,
)


def load_customer_group_model(
    session: Session,
) -> tuple[CustomerGroupDataFrameModel, OperationResult]:
    r"""Load the customer groups.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.CustomerGroupDataFrameModel
        The dataset of the customer groups.

    result : elsabio.core.OperationResult
        The result of loading the customer groups from the database.
    """

    query = (
        select(
            CustomerGroup.customer_group_id.label(CustomerGroupDataFrameModel.c_customer_group_id),
            CustomerGroup.code.label(CustomerGroupDataFrameModel.c_code),
            CustomerGroup.name.label(CustomerGroupDataFrameModel.c_name),
            CustomerGroup.min_fuse_size.label(CustomerGroupDataFrameModel.c_min_fuse_size),
            CustomerGroup.max_fuse_size.label(CustomerGroupDataFrameModel.c_max_fuse_size),
            CustomerGroup.min_subscribed_power.label(
                CustomerGroupDataFrameModel.c_min_subscribed_power
            ),
            CustomerGroup.max_subscribed_power.label(
                CustomerGroupDataFrameModel.c_max_subscribed_power
            ),
            CustomerGroup.min_connection_power.label(
                CustomerGroupDataFrameModel.c_min_connection_power
            ),
            CustomerGroup.max_connection_power.label(
                CustomerGroupDataFrameModel.c_max_connection_power
            ),
            CustomerGroup.min_bound_included.label(
                CustomerGroupDataFrameModel.c_min_bound_included
            ),
            CustomerGroup.max_bound_included.label(
                CustomerGroupDataFrameModel.c_max_bound_included
            ),
            CustomerGroup.facility_type_id.label(CustomerGroupDataFrameModel.c_facility_type_id),
            CustomerGroup.customer_type_id.label(CustomerGroupDataFrameModel.c_customer_type_id),
            CustomerGroup.product_id.label(CustomerGroupDataFrameModel.c_product_id),
            CustomerGroup.not_product_id.label(CustomerGroupDataFrameModel.c_not_product_id),
            CustomerGroup.mapping_strategy_id.label(
                CustomerGroupDataFrameModel.c_mapping_strategy_id
            ),
            CustomerGroupMappingStrategy.code.label(
                CustomerGroupDataFrameModel.c_mapping_strategy_code
            ),
        )
        .join(CustomerGroup.mapping_strategy)
        .order_by(CustomerGroup.customer_group_id.asc())
    )

    df, result = load_sql_query_as_dataframe(
        query=query,
        session=session,
        dtypes=CustomerGroupDataFrameModel.dtypes,
        error_msg='Error loading customer groups from the database!',
    )

    return CustomerGroupDataFrameModel(df=df), result


def load_facility_customer_group_link_model(
    session: Session, start_date: date, end_date: date | None = None
) -> tuple[FacilityCustomerGroupLinkDataFrameModel, OperationResult]:
    r"""Load the facility customer group links.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    start_date : datetime.date
        The start date of the interval in which to load
        facility customer group links (inclusive).

    end_date : datetime.date or None
        The end date of the interval in which to load facility customer group links
        (exclusive). If None the interval is open and unbounded.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel
        The dataset of the facility customer group links.

    result : elsabio.core.OperationResult
        The result of loading the facility customer group links from the database.
    """

    if end_date is None:
        where_clause = FacilityCustomerGroupLink.date_id >= start_date
    else:
        where_clause = and_(
            FacilityCustomerGroupLink.date_id >= start_date,
            FacilityCustomerGroupLink.date_id < end_date,
        )

    query = (
        select(
            FacilityCustomerGroupLink.facility_id.label(
                FacilityCustomerGroupLinkDataFrameModel.c_facility_id
            ),
            FacilityCustomerGroupLink.date_id.label(
                FacilityCustomerGroupLinkDataFrameModel.c_date_id
            ),
            FacilityCustomerGroupLink.customer_group_id.label(
                FacilityCustomerGroupLinkDataFrameModel.c_customer_group_id
            ),
        )
        .where(where_clause)
        .order_by(
            FacilityCustomerGroupLink.date_id.asc(), FacilityCustomerGroupLink.facility_id.asc()
        )
    )

    df, result = load_sql_query_as_dataframe(
        query=query,
        session=session,
        dtypes=FacilityCustomerGroupLinkDataFrameModel.dtypes,
        parse_dates=FacilityCustomerGroupLinkDataFrameModel.parse_dates,
        error_msg='Error loading facility customer group links from the database!',
    )

    return FacilityCustomerGroupLinkDataFrameModel(df=df), result


def bulk_insert_facility_customer_group_links(
    session: Session, df: pd.DataFrame
) -> OperationResult:
    r"""Bulk insert facility customer group links.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    Returns
    -------
    elsabio.core.OperationResult
        The result of saving the new facility customer group links to the database.
    """

    return bulk_insert_to_table(
        session=session,
        table=FacilityCustomerGroupLink.__tablename__,
        df=df,
        required_cols={
            FacilityCustomerGroupLinkDataFrameModel.c_facility_id,
            FacilityCustomerGroupLinkDataFrameModel.c_date_id,
            FacilityCustomerGroupLinkDataFrameModel.c_customer_group_id,
        },
    )


def bulk_update_facility_customer_group_links(
    session: Session, df: pd.DataFrame
) -> OperationResult:
    r"""Bulk update existing facility customer group links.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    Returns
    -------
    elsabio.core.OperationResult
        The result of updating the existing facility customer group links in the database.
    """

    return bulk_update_table(
        session=session,
        model=FacilityCustomerGroupLink,
        df=df,
        required_cols={
            FacilityCustomerGroupLinkDataFrameModel.c_facility_id,
            FacilityCustomerGroupLinkDataFrameModel.c_date_id,
            FacilityCustomerGroupLinkDataFrameModel.c_customer_group_id,
        },
    )
