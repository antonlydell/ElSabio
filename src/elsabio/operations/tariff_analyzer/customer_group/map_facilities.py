# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The business logic for mapping facilities to customer groups in the Tariff Analyzer module."""

# Standard library
from collections.abc import Callable
from functools import partial
from typing import Any

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.core import OperationResult
from elsabio.exceptions import ElSabioError
from elsabio.models.tariff_analyzer import (
    CustomerGroupDataFrameModel,
    CustomerGroupMappingStrategyEnum,
    FacilityContractDataFrameModel,
    FacilityContractExtendedDataFrameModel,
    FacilityCustomerGroupLinkDataFrameModel,
)
from elsabio.operations.core import UpsertDataFrames
from elsabio.operations.validate import validate_duplicate_rows

type MappingFunction = Callable[..., tuple[duckdb.DuckDBPyRelation, OperationResult]]

MAPPING_TABLE_NAME = 'facility_customer_group_link'
MIN_VALUE_PARAM = 'min_value'
MAX_VALUE_PARAM = 'max_value'


def validate_facility_customer_group_input_data_models(
    cg_model: CustomerGroupDataFrameModel, fc_model: FacilityContractDataFrameModel
) -> OperationResult:
    r"""Validate the input data models for mapping facilities to customer groups.

    Parameters
    ----------
    cg_model : elsabio.models.tariff_analyzer.CustomerGroupDataFrameModel
        The data model with the customer groups.

    fc_model : elsabio.models.tariff_analyzer.FacilityContractDataFrameModel
        The data model with the facility contracts.

    Result
    ------
    result : elsabio.core.OperationResult
        The result of the model validation.
    """

    if cg_model.empty:
        return OperationResult(ok=False, short_msg='No customer groups exist!')
    if fc_model.empty:
        return OperationResult(ok=False, short_msg='No facility contracts exist!')

    return OperationResult(ok=True)


def _validate_unmapped_facility_contracts(
    f_cg_link_rel: duckdb.DuckDBPyRelation, fc_rel: duckdb.DuckDBPyRelation
) -> tuple[pd.DataFrame, OperationResult]:
    r"""Validate the facility customer group links for facilities not mapped to customer groups.

    Parameters
    ----------
    f_cg_link_rel : duckdb.DuckDBPyRelation
        The data model with the facility customer groups links.

    fc_rel : duckdb.DuckDBPyRelation
        The data model with the facility contracts.

    Result
    ------
    df : pandas.DataFrame
        The facilities that were not mapped to a customer group.

    result : elsabio.core.OperationResult
        The result of the model validation.
    """

    c_facility_id = FacilityCustomerGroupLinkDataFrameModel.c_facility_id
    c_date_id = FacilityCustomerGroupLinkDataFrameModel.c_date_id
    c_customer_group_id = FacilityCustomerGroupLinkDataFrameModel.c_customer_group_id

    c_facility_id_fc = FacilityContractDataFrameModel.c_facility_id
    c_date_id_fc = FacilityContractDataFrameModel.c_date_id

    fc_alias = fc_rel.alias
    f_cg_link_alias = f_cg_link_rel.alias

    join_condition = (
        f'{f_cg_link_alias}.{c_facility_id} = {fc_alias}.{c_facility_id_fc}\n '
        f'AND {f_cg_link_alias}.{c_date_id} = {fc_alias}.{c_date_id_fc}'
    )
    exclude_cols = (
        f'{f_cg_link_alias}.{c_facility_id_fc}, '
        f'{f_cg_link_alias}.{c_date_id_fc}, '
        f'{f_cg_link_alias}.{c_customer_group_id}'
    )

    df = (
        fc_rel.join(other_rel=f_cg_link_rel, condition=join_condition, how='left')
        .filter(f'{f_cg_link_alias}.{c_facility_id} IS NULL')
        .select(f'* EXCLUDE({exclude_cols})')
        .order(f'{c_date_id_fc} ASC, {c_facility_id_fc} ASC')
        .to_df(date_as_object=True)
        .set_index([c_facility_id_fc, c_date_id_fc])
    )
    if (nr_unmapped := df.shape[0]) > 0:
        result = OperationResult(
            ok=False,
            short_msg=(
                f'Facility contracts ({nr_unmapped}) could not be mapped to a customer group!'
            ),
        )
    else:
        result = OperationResult(ok=True)

    return df, result


def validate_duplicate_facility_customer_group_links(
    f_cg_link_rel: duckdb.DuckDBPyRelation,
) -> tuple[OperationResult, pd.DataFrame]:
    r"""Validate the facility customer group links for duplicates.

    Parameters
    ----------
    f_cg_link_rel : duckdb.DuckDBPyRelation
        The data model with the facility customer groups links within the same month.

    Result
    ------
    result : elsabio.core.OperationResult
        The result of the model validation.

    df_duplicates : pandas.DataFrame
        The facilities that were mapped to more than one customer group.
    """

    c_facility_id = FacilityCustomerGroupLinkDataFrameModel.c_facility_id
    c_date_id = FacilityCustomerGroupLinkDataFrameModel.c_date_id

    cols = [c_facility_id, c_date_id]

    _, df = validate_duplicate_rows(
        model=f_cg_link_rel,
        cols=cols,
        order_by=((c_date_id, 'ASC'), (c_facility_id, 'ASC')),
        index_cols=cols,
    )

    if (nr_duplicates := df.shape[0]) > 0:
        result = OperationResult(
            ok=False,
            short_msg=(f'Found duplicate facility customer group links ({nr_duplicates})!'),
        )
    else:
        result = OperationResult(ok=True)

    return result, df


def _create_facility_contract_filter(
    facility_type_id: int,
    customer_type_id: int | None = None,
    product_id: int | None = None,
    not_product_id: int | None = None,
) -> str:
    r"""Create the default where clause for filtering facility contracts.

    Parameters
    ----------
    facility_type_id : int
        The ID of the type of facility to filter by.

    customer_type_id : int or None, default None
        The ID of the type of customer to filter by.

    product_id : int or None, default None
        The ID of the product to filter by.

    not_product_id : int or None, default None
        The ID of the product to not associate with a contract.

    Returns
    -------
    where_clause : str
        The where clause for filtering facility contracts.
    """

    c_product_id = FacilityContractExtendedDataFrameModel.c_product_id
    c_facility_type_id = FacilityContractExtendedDataFrameModel.c_facility_type_id
    c_customer_type_id = FacilityContractExtendedDataFrameModel.c_customer_type_id

    where_clause = f'{c_facility_type_id} = {facility_type_id}'

    if not pd.isna(customer_type_id):
        where_clause = f'{where_clause}\nAND {c_customer_type_id} = {customer_type_id}'

    if not pd.isna(product_id):
        where_clause = f'{where_clause}\nAND {c_product_id} = {product_id}'

    if not pd.isna(not_product_id):
        where_clause = f'{where_clause}\nAND {c_product_id} != {not_product_id}'

    return where_clause


def _map_facilities_by_product(
    fc_rel: duckdb.DuckDBPyRelation,
    customer_group_id: int,
    product_id: int | None,
    facility_type_id: int,
    customer_type_id: int | None = None,
    not_product_id: int | None = None,
    **_kwargs: Any,
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Map facilities to customer groups by `product_id`.

    Parameters
    ----------
    fc_rel : duckdb.DuckDBPyRelation
        The relation object of the facility contracts. Should adhere to
        the structure of :class:`elsabio.models.tariff_analyzer.FacilityContractExtendedDataFrameModel`.

    customer_group_id : int
        The ID of the customer group that is being mapped.

    product_id : int or None, default None
        The ID of the product of the facility contracts to associate with the
        customer group.

    facility_type_id : int
        The ID of the type of facility associated with the customer group.

    customer_type_id : int or None, default None
        The type of customer associated with the customer group.

    not_product_id : int or None, default None
        The ID of the product of the facility contracts to *not* associate with the
        customer group.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The relation object of the facilities associated with `customer_group_id`.
        Adheres to the structure of model :class:`elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel`.

    elsabio.core.OperationResult
        The result of the mapping operation.
    """

    c_customer_group_id = CustomerGroupDataFrameModel.c_customer_group_id
    c_facility_id = FacilityContractExtendedDataFrameModel.c_facility_id
    c_date_id = FacilityContractExtendedDataFrameModel.c_date_id

    if product_id is None or pd.isna(product_id):
        return fc_rel, OperationResult(
            ok=False, short_msg=f'Required product_id param is None for {customer_group_id=}'
        )

    where_clause = _create_facility_contract_filter(
        facility_type_id=facility_type_id,
        customer_type_id=customer_type_id,
        product_id=product_id,
        not_product_id=not_product_id,
    )

    select_cols = f"""
        {c_facility_id}
        , {c_date_id}
        , {customer_group_id} AS {c_customer_group_id}
"""

    return fc_rel.filter(where_clause).project(select_cols), OperationResult(ok=True)


def _map_facilities_by_column_value_in_interval(
    fc_rel: duckdb.DuckDBPyRelation,
    col: str,
    customer_group_id: int,
    facility_type_id: int,
    min_value: int | float | None,
    max_value: int | float | None,
    min_bound_included: bool,
    max_bound_included: bool,
    customer_type_id: int | None = None,
    product_id: int | None = None,
    not_product_id: int | None = None,
    **_kwargs: Any,
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Map facilities to customer groups by column value in interval.

    fc_rel : duckdb.DuckDBPyRelation
        The relation object of the facility contracts. Should adhere to
        the structure of :class:`elsabio.models.tariff_analyzer.FacilityContractExtendedDataFrameModel`.

    col : str
        The name of the column to use for mapping the facilities to the customer group.

    customer_group_id : int
        The ID of the customer group that is being mapped.

    facility_type_id : int
        The type of facilities associated with the customer group.

    min_value : int or float or None
        The minimum value of `col`.

    max_value : int or float or None
        The maximum value of `col`. If None there is no max value.

    min_bound_included : bool
        True if `min_value` is included in the interval and False otherwise.

    max_bound_included : bool
        True if `max_value` is included in the interval and False otherwise.

    customer_type_id : int or None, default None
        The type of customer associated with the customer group.

    product_id : int or None, default None
        The ID of the product of the facility contracts to associate with the
        customer group.

    not_product_id : int or None, default None
        The ID of the product of the facility contracts to *not* associate with the
        customer group.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The relation object of the facilities mapped to the customer group.
        Adheres to the structure of model :class:`elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel`.

    elsabio.core.OperationResult
        The result of the mapping operation.
    """

    c_customer_group_id = CustomerGroupDataFrameModel.c_customer_group_id
    c_facility_id = FacilityContractDataFrameModel.c_facility_id
    c_date_id = FacilityContractDataFrameModel.c_date_id

    min_operator = '>=' if min_bound_included else '>'
    max_operator = '<=' if max_bound_included else '<'

    if min_value is None or pd.isna(min_value):
        return fc_rel, OperationResult(
            ok=False, short_msg=f'Required min_value param is None for {customer_group_id=}'
        )

    where_clause = _create_facility_contract_filter(
        facility_type_id=facility_type_id,
        customer_type_id=customer_type_id,
        product_id=product_id,
        not_product_id=not_product_id,
    )

    where_clause = f'{where_clause}\n AND {col} {min_operator} {min_value}'

    if not pd.isna(max_value):
        where_clause = f'{where_clause}\n AND {col} {max_operator} {max_value}'

    select_cols = f"""
    {c_facility_id}
    , {c_date_id}
    , {customer_group_id} AS {c_customer_group_id}
"""

    return fc_rel.filter(where_clause).select(select_cols), OperationResult(ok=True)


map_facilities_by_fuse_size = partial(
    _map_facilities_by_column_value_in_interval,
    col=FacilityContractDataFrameModel.c_fuse_size,
)

map_facilities_by_subscribed_power = partial(
    _map_facilities_by_column_value_in_interval,
    col=FacilityContractDataFrameModel.c_subscribed_power,
)

map_facilities_by_connection_power = partial(
    _map_facilities_by_column_value_in_interval,
    col=FacilityContractDataFrameModel.c_connection_power,
)

mapping_strategies: dict[str, tuple[MappingFunction, dict[str, str]]] = {
    CustomerGroupMappingStrategyEnum.PRODUCT: (
        _map_facilities_by_product,
        {},
    ),
    CustomerGroupMappingStrategyEnum.FUSE_SIZE: (
        map_facilities_by_fuse_size,
        {
            MIN_VALUE_PARAM: CustomerGroupDataFrameModel.c_min_fuse_size,
            MAX_VALUE_PARAM: CustomerGroupDataFrameModel.c_max_fuse_size,
        },
    ),
    CustomerGroupMappingStrategyEnum.SUBSCRIBED_POWER: (
        map_facilities_by_subscribed_power,
        {
            MIN_VALUE_PARAM: CustomerGroupDataFrameModel.c_min_subscribed_power,
            MAX_VALUE_PARAM: CustomerGroupDataFrameModel.c_max_subscribed_power,
        },
    ),
    CustomerGroupMappingStrategyEnum.CONNECTION_POWER: (
        map_facilities_by_connection_power,
        {
            MIN_VALUE_PARAM: CustomerGroupDataFrameModel.c_min_connection_power,
            MAX_VALUE_PARAM: CustomerGroupDataFrameModel.c_max_connection_power,
        },
    ),
}


def _map_facilities_by_strategy(
    customer_group: pd.Series, fc_rel: duckdb.DuckDBPyRelation
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Map facilities to customer groups by mapping strategy.

    Parameters
    ----------
    customer_group : pandas.Series
        The customer groups to map to facilities.

    fc_rel : duckdb.DuckDBPyRelation
        The relation object of the facility contracts to map to a customer group.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The relation object of the facilities mapped to a customer group.
        Adheres to the structure of model :class:`elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel`.

    elsabio.core.OperationResult
        The result of the mapping operation.
    """

    c_customer_group_id = CustomerGroupDataFrameModel.c_customer_group_id
    c_mapping_strategy_code = CustomerGroupDataFrameModel.c_mapping_strategy_code
    c_min_bound_included = CustomerGroupDataFrameModel.c_min_bound_included
    c_max_bound_included = CustomerGroupDataFrameModel.c_max_bound_included
    c_facility_type_id = CustomerGroupDataFrameModel.c_facility_type_id
    c_customer_type_id = CustomerGroupDataFrameModel.c_customer_type_id
    c_product_id = CustomerGroupDataFrameModel.c_product_id
    c_not_product_id = CustomerGroupDataFrameModel.c_not_product_id
    c_facility_type_id = CustomerGroupDataFrameModel.c_facility_type_id

    strategy = customer_group[c_mapping_strategy_code]

    value = mapping_strategies.get(strategy)
    if value is None:
        raise ElSabioError(
            f'Missing mapping function for facility customer group mapping strategy "{strategy}"'
        )

    func, min_max_cols = value
    min_value_col = min_max_cols.get(MIN_VALUE_PARAM)
    max_value_col = min_max_cols.get(MAX_VALUE_PARAM)

    return func(
        fc_rel=fc_rel,
        customer_group_id=customer_group[c_customer_group_id],
        min_value=None if min_value_col is None else customer_group[min_value_col],
        max_value=None if max_value_col is None else customer_group[max_value_col],
        min_bound_included=customer_group[c_min_bound_included],
        max_bound_included=customer_group[c_max_bound_included],
        facility_type_id=customer_group[c_facility_type_id],
        customer_type_id=customer_group[c_customer_type_id],
        product_id=customer_group[c_product_id],
        not_product_id=customer_group[c_not_product_id],
    )


def map_facilities_to_customer_groups(
    cg_model: CustomerGroupDataFrameModel,
    fc_model: FacilityContractDataFrameModel,
    conn: duckdb.DuckDBPyConnection,
) -> tuple[duckdb.DuckDBPyRelation, pd.DataFrame, OperationResult]:
    r"""Map facilities to customer groups.

    Parameters
    ----------
    cg_model : elsabio.models.tariff_analyzer.CustomerGroupDataFrameModel
        The data model with the customer groups.

    fc_model : elsabio.models.tariff_analyzer.FacilityContractDataFrameModel
        The data model with the facility contracts.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which to save the temporary mapping result.

    Returns
    -------
    f_cg_link_rel : duckdb.DuckDBPyRelation
        The facility customer group links.
        Adheres to the structure of model :class:`elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel`.

    df_unmapped : pandas.DataFrame
        The facilities from `fc_model` that were not mapped to a customer group.

    result : elsabio.core.OperationResult
        The result of the mapping operation.
    """

    c_facility_id = FacilityCustomerGroupLinkDataFrameModel.c_facility_id
    c_date_id = FacilityCustomerGroupLinkDataFrameModel.c_date_id

    c_date_id = FacilityContractExtendedDataFrameModel.c_date_id

    fc_rel = conn.from_df(fc_model.df)

    df_cg = cg_model.df
    error_msgs = []

    for row_id in cg_model.df.index:
        cg = df_cg.loc[row_id, :].squeeze()
        rel, result = _map_facilities_by_strategy(fc_rel=fc_rel, customer_group=cg)

        if not result.ok:
            error_msgs.append(result.short_msg)
            continue

        try:
            rel.insert_into(MAPPING_TABLE_NAME)
        except duckdb.CatalogException:
            rel.to_table(MAPPING_TABLE_NAME)

    order_by = f'{c_date_id} ASC, {c_facility_id} ASC'
    f_cg_link_rel = conn.table(MAPPING_TABLE_NAME).order(order_by)

    df_unmapped, result = _validate_unmapped_facility_contracts(
        f_cg_link_rel=f_cg_link_rel, fc_rel=fc_rel
    )

    error_msg = ''
    if error_msgs:
        error_msg = '\n'.join(m for m in error_msgs)

    if not result.ok:
        error_msg = f'{error_msg}\n{result.short_msg}' if error_msg else result.short_msg

    if error_msg:
        result = OperationResult(ok=False, short_msg=error_msg)
    else:
        result = OperationResult(ok=True)

    return f_cg_link_rel, df_unmapped, result


def create_facility_customer_group_link_upsert_dataframes(
    f_cg_link_rel: duckdb.DuckDBPyRelation,
    f_cg_link_model_existing: FacilityCustomerGroupLinkDataFrameModel,
    conn: duckdb.DuckDBPyConnection,
) -> UpsertDataFrames:
    r"""Create the DataFrames for inserting new and updating existing facility customer group links.

    Parameters
    ----------
    f_cg_link_model : duckdb.DuckDBPyRelation
        The data model with the facility customer group links to import. Should adhere
        to the structure of :class:`elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel`.

    f_cg_link_model_existing : elsabio.models.tariff_analyzer.FacilityCustomerGroupLinkDataFrameModel
        The data model with the facility customer group links that already exist in the database.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which `f_cg_link_model` exists.

    Returns
    -------
    dfs : elsabio.operations.core.UpsertDataFrames
        The DataFrames with facility customer group links to insert or update.

    result : elsabio.core.OperationResult
        The result of the creation of the upsert DataFrames.
    """

    c_facility_id = FacilityCustomerGroupLinkDataFrameModel.c_facility_id
    c_date_id = FacilityCustomerGroupLinkDataFrameModel.c_date_id
    c_customer_group_id = FacilityCustomerGroupLinkDataFrameModel.c_customer_group_id

    c_to_insert = 'to_insert'
    cols = (c_facility_id, c_date_id, c_customer_group_id)

    fcgl_name = 'facility_customer_group_link_new'
    fcgl_new_prefix = 'fcgl_new'
    fcgl_existing_name = 'facility_customer_group_link_existing'
    fcgl_existing_prefix = 'fcgl_existing'

    dtypes = {  # To ensure compatible dtypes with SQLAlchemy
        c_facility_id: 'int32',
        c_date_id: 'date',
        c_customer_group_id: 'int32',
    }
    cols_select_list = '\n'.join(
        f', {fcgl_new_prefix}.{col}::{dtype} AS {col}'
        for col, dtype in dtypes.items()
        if col in cols
    )

    f_cg_link_rel.create_view(fcgl_name)
    conn.register(view_name=fcgl_existing_name, python_object=f_cg_link_model_existing.df)

    mapping_query = f"""\
SELECT
    CASE
        WHEN (
            {fcgl_existing_prefix}.{c_facility_id} IS NULL
            AND {fcgl_existing_prefix}.{c_date_id} IS NULL
        ) THEN
            true
        ELSE
            false
        END AS {c_to_insert}
    {cols_select_list}

FROM {fcgl_name} {fcgl_new_prefix}

LEFT OUTER JOIN {fcgl_existing_name} {fcgl_existing_prefix}
    ON {fcgl_existing_prefix}.{c_facility_id} = {fcgl_new_prefix}.{c_facility_id}
       AND {fcgl_existing_prefix}.{c_date_id} = {fcgl_new_prefix}.{c_date_id}

ORDER BY
    {fcgl_new_prefix}.{c_date_id}       ASC
    , {fcgl_new_prefix}.{c_facility_id} ASC
    """  # noqa: S608

    rel = conn.sql(mapping_query)

    select_cols = f'* EXCLUDE({c_to_insert})'

    df_insert = rel.filter(f'{c_to_insert} = true').select(select_cols).to_df(date_as_object=True)
    df_update = rel.filter(f'{c_to_insert} = false').select(select_cols).to_df(date_as_object=True)

    return UpsertDataFrames(insert=df_insert, update=df_update, invalid=pd.DataFrame())
