# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Shared test helpers for the tariff value result of the tariff calculations."""

# Third party
import duckdb
import pandas as pd
from pandas.testing import assert_frame_equal

# Local
from elsabio.config import TariffAnalyzerConfig
from elsabio.models.tariff_analyzer import (
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)

# =================================================================================================
# Constants
# =================================================================================================

_FACILITY_SORT_COLS_BY = [
    TariffValueFacilityDataFrameModel.c_tariff_id,
    TariffValueFacilityDataFrameModel.c_date_id,
    TariffValueFacilityDataFrameModel.c_tariff_component_type_id,
    TariffValueFacilityDataFrameModel.c_tariff_cost_group_id,
    TariffValueFacilityDataFrameModel.c_customer_group_id,
    TariffValueFacilityDataFrameModel.c_facility_id,
]
_TOTAL_SORT_COLS_BY = [
    TariffValueTotalDataFrameModel.c_tariff_id,
    TariffValueTotalDataFrameModel.c_date_id,
    TariffValueTotalDataFrameModel.c_tariff_component_type_id,
    TariffValueTotalDataFrameModel.c_tariff_cost_group_id,
    TariffValueTotalDataFrameModel.c_customer_group_id,
    TariffValueTotalDataFrameModel.c_tariff_component_id,
]
_FACILITY_INDEX_COL = TariffValueFacilityDataFrameModel.c_facility_id
_TOTAL_INDEX_COL = TariffValueTotalDataFrameModel.c_tariff_id


# =================================================================================================
# Helpers
# =================================================================================================


def _load_tariff_value_result(pattern: str) -> pd.DataFrame:
    r"""Load the tariff value result.

    Parameters
    ----------
    pattern : str
        The file path glob pattern to apply when loading the tariff value result parquet files.

    Returns
    -------
    pandas.DataFrame
        The loaded tariff value result.
    """

    return duckdb.read_parquet(file_glob=pattern, hive_partitioning=True).to_df(date_as_object=True)


def assert_tariff_value_written(
    cfg: TariffAnalyzerConfig,
    df_facility_exp: pd.DataFrame,
    df_total_exp: pd.DataFrame,
) -> None:
    r"""Assert that the expected tariff value result was written to the parquet store.

    Parameters
    ----------
    cfg : elsabio.config.TariffAnalyzerConfig
        The tariff analyzer configuration used for the tariff calculations.

    df_facility_exp : pandas.DataFrame
        The expected tariff value result per facility.

    df_total_exp : pandas.DataFrame
        The expected total tariff value result.
    """

    validation_set = (
        (
            'facility',
            cfg.tariff_value_facility_dir,
            _FACILITY_SORT_COLS_BY,
            _FACILITY_INDEX_COL,
            df_facility_exp,
        ),
        (
            'total',
            cfg.tariff_value_total_dir,
            _TOTAL_SORT_COLS_BY,
            _TOTAL_INDEX_COL,
            df_total_exp,
        ),
    )
    for value in validation_set:
        value_type, path, sort_by_cols, index_col, df_exp = value

        exp_cols = df_exp.columns.to_list()
        df_exp = df_exp.sort_values(sort_by_cols).set_index(index_col)

        df = _load_tariff_value_result(pattern=str(path / '*' / '*' / '*.parquet'))

        missing_cols = set(exp_cols).difference(df.columns)
        assert not missing_cols, (
            f'Missing columns in tariff value {value_type} dataset : {missing_cols}'
        )

        df = df.loc[:, exp_cols].sort_values(sort_by_cols).set_index(index_col)

        print(f'assert {value_type=}')
        assert_frame_equal(df, df_exp, check_dtype=False, check_index_type=False)
