# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The business logic for the product data import to the Tariff Analyzer module."""

# ruff: noqa: S608

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.core import OperationResult, has_required_columns
from elsabio.models.tariff_analyzer import ProductDataFrameModel, ProductMappingDataFrameModel


def create_product_upsert_dataframes(
    import_model: duckdb.DuckDBPyRelation,
    product_model: ProductMappingDataFrameModel,
    conn: duckdb.DuckDBPyConnection,
) -> tuple[pd.DataFrame, pd.DataFrame, OperationResult]:
    r"""Create the DataFrames for inserting new and updating existing products.

    Parameters
    ----------
    import_model : duckdb.DuckDBPyRelation
        The data model with the products to import. Should contain
        at least the columns `external_id` and `name` from the model
        :class:`elsabio.models.tariff_analyzer.ProductImportDataFrameModel`.

    product_model : elsabio.models.tariff_analyzer.ProductMappingDataFrameModel
        The model with the mapping of `product_id` to `external_id`. Used to determine the
        existing products from `import_model` to update and the new ones to import.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which the `import_model` relation exists.

    Returns
    -------
    df_insert : pandas.DataFrame
        The new products to insert.

    df_update : pandas.DataFrame
        The existing products to update.

    result : elsabio.core.OperationResult
        The result of the creation of the upsert DataFrames.
    """

    # Columns
    c_product_id = ProductMappingDataFrameModel.c_product_id
    c_external_id = ProductMappingDataFrameModel.c_external_id
    c_name = ProductDataFrameModel.c_name
    c_description = ProductDataFrameModel.c_description

    df_product = product_model.df
    result = has_required_columns(
        cols=set(df_product.columns), required_cols={c_product_id, c_external_id}
    )
    if not result.ok:
        return pd.DataFrame(), pd.DataFrame(), result

    cols = set(import_model.columns)
    result = has_required_columns(cols=cols, required_cols={c_external_id, c_name})
    if not result.ok:
        return pd.DataFrame(), pd.DataFrame(), result

    product_model_name = 'product_mapping'
    product_model_prefix = 'p'
    import_model_name = 'import_model'
    import_model_prefix = 'i'

    dtypes = {  # To ensure compatible dtypes with SQLAlchemy
        c_external_id: 'varchar',
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
    {product_model_prefix}.{c_product_id}::int32 AS {c_product_id}
    {cols_select_list}

FROM {import_model_name} {import_model_prefix}

LEFT OUTER JOIN {product_model_name} {product_model_prefix}
    ON {product_model_prefix}.{c_external_id} = {import_model_prefix}.{c_external_id}

ORDER BY
    {import_model_prefix}.{c_external_id} ASC
"""

    import_model.create_view(import_model_name)
    conn.register(view_name=product_model_name, python_object=df_product)
    rel = conn.sql(query=mapping_query)

    df_insert = rel.filter(f'{c_product_id} IS NULL').project(f'* EXCLUDE ({c_product_id})').to_df()
    df_update = rel.filter(f'{c_product_id} IS NOT NULL').to_df()

    return df_insert, df_update, result
