# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The business logic for the facility data import to the Tariff Analyzer module."""

# ruff: noqa: S608

# Standard library
from typing import NamedTuple

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.core import OperationResult, has_required_columns
from elsabio.models.tariff_analyzer import (
    FacilityDataFrameModel,
    FacilityImportDataFrameModel,
    FacilityMappingDataFrameModel,
    FacilityTypeMappingDataFrameModel,
)


class FacilityUpsertDataFrames(NamedTuple):
    r"""The DataFrames with facilities to insert or update.

    Parameters
    ----------
    insert : pandas.DataFrame
        The new facilities to insert.

    update : pandas.DataFrame
        The existing facilities to update.

    missing_facility_type : pandas.DataFrame
        The facilities with a missing or unmapped facility type.
    """

    insert: pd.DataFrame
    update: pd.DataFrame
    missing_facility_type: pd.DataFrame


def create_facility_upsert_dataframes(
    import_model: duckdb.DuckDBPyRelation,
    facility_model: FacilityMappingDataFrameModel,
    facility_type_model: FacilityTypeMappingDataFrameModel,
    conn: duckdb.DuckDBPyConnection,
) -> tuple[FacilityUpsertDataFrames, OperationResult]:
    r"""Create the DataFrames for inserting new and updating existing facilities.

    Parameters
    ----------
    import_model : duckdb.DuckDBPyRelation
        The data model with the facilities to import. Should contain
        at least the columns `ean` and `facility_type_code` from the model
        :class:`elsabio.models.tariff_analyzer.FacilityImportDataFrameModel`.

    facility_model : elsabio.models.tariff_analyzer.FacilityMappingDataFrameModel
        The model with the mapping of `facility_id` to `ean`. Used to determine the
        existing facilities from `import_model` to update and the new ones to import.

    facility_type_model : elsabio.models.tariff_analyzer.FacilityTypeMappingDataFrameModel
        The model with the mapping of `facility_type_id` to `facility_type_code`. Used to
        derive the `facility_type_id` of the facilities to import or update.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which the `import_model` relation exists.

    Returns
    -------
    dfs : elsabio.operations.tariff_analyzer.FacilityUpsertDataFrames
        The DataFrames with facilities to insert or update.

    result : elsabio.core.OperationResult
        The result of the creation of the upsert DataFrames.
    """

    # Columns
    c_facility_id = FacilityMappingDataFrameModel.c_facility_id
    c_ean = FacilityDataFrameModel.c_ean
    c_ean_prod = FacilityDataFrameModel.c_ean_prod
    c_facility_type_id = FacilityDataFrameModel.c_facility_type_id
    c_name = FacilityDataFrameModel.c_name
    c_description = FacilityDataFrameModel.c_description
    c_facility_type_code_import = FacilityImportDataFrameModel.c_facility_type_code
    c_facility_type_code = FacilityTypeMappingDataFrameModel.c_code

    df_facility = facility_model.df
    result = has_required_columns(
        cols=set(df_facility.columns), required_cols={c_facility_id, c_ean}
    )
    if not result.ok:
        dfs = FacilityUpsertDataFrames(
            insert=pd.DataFrame(), update=pd.DataFrame(), missing_facility_type=pd.DataFrame()
        )
        return dfs, result

    df_facility_type = facility_type_model.df
    result = has_required_columns(
        cols=set(df_facility_type.columns),
        required_cols={c_facility_type_id, c_facility_type_code},
    )
    if not result.ok:
        dfs = FacilityUpsertDataFrames(
            insert=pd.DataFrame(), update=pd.DataFrame(), missing_facility_type=pd.DataFrame()
        )
        return dfs, result

    cols = set(import_model.columns)
    result = has_required_columns(cols=cols, required_cols={c_ean, c_facility_type_code_import})
    if not result.ok:
        dfs = FacilityUpsertDataFrames(
            insert=pd.DataFrame(), update=pd.DataFrame(), missing_facility_type=pd.DataFrame()
        )
        return dfs, result

    facility_model_name = 'facility_mapping'
    facility_model_prefix = 'm'
    import_model_name = 'import_model'
    import_model_prefix = 'i'
    facility_type_model_name = 'facility_type'
    facility_type_model_prefix = 'ft'

    dtypes = {  # To ensure compatible dtypes with SQLAlchemy
        c_ean: 'int64',
        c_ean_prod: 'int64',
        c_facility_type_code_import: 'varchar',
        c_name: 'varchar',
        c_description: 'varchar',
    }
    cols_select_list = '\n'.join(
        f', {import_model_prefix}.{col}::{dtype} AS {col}'
        for col, dtype in dtypes.items()
        if col in cols
    )

    mapping_query = f"""\
SELECT
    {facility_model_prefix}.{c_facility_id}::int64 AS {c_facility_id}
    , {facility_type_model_prefix}.{c_facility_type_id}::int8 AS {c_facility_type_id}
    {cols_select_list}

FROM {import_model_name} {import_model_prefix}

LEFT OUTER JOIN {facility_model_name} {facility_model_prefix}
    ON {facility_model_prefix}.{c_ean} = {import_model_prefix}.{c_ean}

LEFT OUTER JOIN {facility_type_model_name} {facility_type_model_prefix}
    ON {facility_type_model_prefix}.{c_facility_type_code} = {import_model_prefix}.{c_facility_type_code_import}

ORDER BY
    {import_model_prefix}.{c_ean} ASC
"""

    import_model.create_view(import_model_name)
    conn.register(view_name=facility_model_name, python_object=df_facility)
    conn.register(view_name=facility_type_model_name, python_object=df_facility_type)
    rel = conn.sql(query=mapping_query)

    df_insert = (
        rel.filter(f'{c_facility_id} IS NULL')
        .project(f'* EXCLUDE ({c_facility_id}, {c_facility_type_code_import})')
        .to_df()
    )
    df_update = (
        rel.filter(f'{c_facility_id} IS NOT NULL')
        .project(f'* EXCLUDE ({c_facility_type_code_import})')
        .to_df()
    )
    df_missing_facility_type = (
        rel.filter(f'{c_facility_type_id} IS NULL')
        .project(f'{c_facility_id}, {c_ean}, {c_facility_type_id}, {c_facility_type_code_import}')
        .to_df()
        .set_index(c_facility_id)
    )

    if (nr_missing_facility_type := df_missing_facility_type.shape[0]) > 0:
        result = OperationResult(
            ok=False,
            short_msg=(
                f'Found facilities ({nr_missing_facility_type}) with '
                'missing or invalid facility_type!'
            ),
        )
    else:
        result = OperationResult(ok=True)

    dfs = FacilityUpsertDataFrames(
        insert=df_insert, update=df_update, missing_facility_type=df_missing_facility_type
    )
    return dfs, result
