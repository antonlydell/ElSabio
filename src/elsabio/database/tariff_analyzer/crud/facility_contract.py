# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Functions for working with the `FacilityContract` model of Tariff Analyzer."""

# Standard library
from collections.abc import Sequence
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
from elsabio.database.models.tariff_analyzer import Facility, FacilityContract, FacilityType
from elsabio.models.tariff_analyzer import (
    FacilityContractDataFrameModel,
    FacilityContractExtendedDataFrameModel,
    FacilityContractMappingDataFrameModel,
)


def load_facility_contract_mapping_model(
    session: Session, date_ids: Sequence[date]
) -> tuple[FacilityContractMappingDataFrameModel, OperationResult]:
    r"""Load the facility contract mapping model for locating existing facility contracts.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    date_ids : Sequence[datetime.date]
        The months in which to load facility contracts.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.FacilityContractMappingDataFrameModel
        The dataset of the facility contract mappings.

    result : elsabio.core.OperationResult
        The result of loading the facility contract mapping model from the database.
    """

    query = (
        select(
            FacilityContract.facility_id.label(FacilityContractMappingDataFrameModel.c_facility_id),
            FacilityContract.date_id.label(FacilityContractMappingDataFrameModel.c_date_id),
        )
        .where(FacilityContract.date_id.in_(date_ids))
        .order_by(FacilityContract.date_id.asc(), FacilityContract.facility_id.asc())
    )

    df, result = load_sql_query_as_dataframe(
        query=query,
        session=session,
        dtypes=FacilityContractMappingDataFrameModel.dtypes,
        parse_dates=FacilityContractMappingDataFrameModel.parse_dates,
        error_msg='Error loading facility contracts from the database!',
    )

    return FacilityContractMappingDataFrameModel(df=df), result


def load_facility_contract_extended_model(
    session: Session, start_date: date, end_date: date | None = None
) -> tuple[FacilityContractExtendedDataFrameModel, OperationResult]:
    r"""Load facility contracts in specified interval.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    start_date : datetime.date
        The start date of the interval in which to load facility contracts (inclusive).

    end_date : datetime.date or None
        The end date of the interval in which to load facility contracts
        (exclusive). If None the interval is open and unbounded.

    Returns
    -------
    model : elsabio.models.tariff_analyzer.FacilityContractExtendedDataFrameModel
        The extended dataset with facility contracts.

    result : elsabio.core.OperationResult
        The result of loading the extended facility contract model from the database.
    """

    if end_date is None:
        where_clause = FacilityContract.date_id >= start_date
    else:
        where_clause = and_(
            FacilityContract.date_id >= start_date,
            FacilityContract.date_id < end_date,
        )

    query = (
        select(
            FacilityContract.facility_id.label(
                FacilityContractExtendedDataFrameModel.c_facility_id
            ),
            FacilityContract.date_id.label(FacilityContractExtendedDataFrameModel.c_date_id),
            FacilityContract.fuse_size.label(FacilityContractExtendedDataFrameModel.c_fuse_size),
            FacilityContract.subscribed_power.label(
                FacilityContractExtendedDataFrameModel.c_subscribed_power
            ),
            FacilityContract.connection_power.label(
                FacilityContractExtendedDataFrameModel.c_connection_power
            ),
            FacilityContract.account_nr.label(FacilityContractExtendedDataFrameModel.c_account_nr),
            FacilityType.facility_type_id.label(
                FacilityContractExtendedDataFrameModel.c_facility_type_id
            ),
            FacilityContract.customer_type_id.label(
                FacilityContractExtendedDataFrameModel.c_customer_type_id
            ),
            FacilityContract.product_id.label(FacilityContractExtendedDataFrameModel.c_product_id),
        )
        .join(FacilityContract.facility)
        .join(Facility.facility_type)
        .where(where_clause)
        .order_by(FacilityContract.date_id.asc(), FacilityContract.facility_id.asc())
    )

    df, result = load_sql_query_as_dataframe(
        query=query,
        session=session,
        dtypes=FacilityContractExtendedDataFrameModel.dtypes,
        parse_dates=FacilityContractExtendedDataFrameModel.parse_dates,
        error_msg='Error loading facility contracts from the database!',
    )

    return FacilityContractExtendedDataFrameModel(df=df), result


def bulk_insert_facility_contracts(session: Session, df: pd.DataFrame) -> OperationResult:
    r"""Bulk insert facility contracts into the facility_contract table.

    Parameters
    ----------
    conn : elsabio.db.Session
        An open session to the database.

    Returns
    -------
    elsabio.core.OperationResult
        The result of saving the new facilities to the database.
    """

    return bulk_insert_to_table(
        session=session,
        table=FacilityContract.__tablename__,
        df=df,
        required_cols={
            FacilityContractDataFrameModel.c_date_id,
            FacilityContractDataFrameModel.c_customer_type_id,
        },
    )


def bulk_update_facility_contracts(session: Session, df: pd.DataFrame) -> OperationResult:
    r"""Bulk update existing facility contracts.

    Parameters
    ----------
    conn : elsabio.db.Session
        An open session to the database.

    Returns
    -------
    elsabio.core.OperationResult
        The result of updating the existing facility contracts in the database.
    """

    return bulk_update_table(
        session=session,
        model=FacilityContract,
        df=df,
        required_cols={
            FacilityContractDataFrameModel.c_facility_id,
            FacilityContractDataFrameModel.c_date_id,
            FacilityContractDataFrameModel.c_customer_type_id,
        },
    )
