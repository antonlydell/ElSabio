# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The business logic for tariff calculations in the Tariff Analyzer module."""

# Standard library
from collections.abc import Callable, Generator, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Literal, NamedTuple

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.core import OperationResult
from elsabio.exceptions import ElSabioError
from elsabio.models.tariff_analyzer import (
    TARIFF_PRICE_DTYPE,
    CalcStrategyEnum,
    PeriodizeStrategyEnum,
    SerieValueDataFrameModel,
    TariffCalculationDataFrameModel,
    TariffCalculationExtendedDataFrameModel,
    TariffValueFacilityDataFrameModel,
    TariffValueTotalDataFrameModel,
)
from elsabio.operations.file import read_meter_data_parquet_hive, write_parquet
from elsabio.operations.validate import validate_duplicate_rows

type StrategyFunction = Callable[..., tuple[duckdb.DuckDBPyRelation, OperationResult]]

FACILITY_TARIFF_VALUE_TABLE_NAME = 'facility_tariff_value'


class StrategyColumns(NamedTuple):
    r"""The unique columns needed to perform the calculations by strategy.

    Parameters
    ----------
    tariff_component_type : int
        The unique ID of the type of tariff component to calculate.

    calc_strategy_code : str
        The unique code of the calculation strategy to apply.

    serie_type_code : str or None
        The unique code of the meter data serie to use in the calculations.

    comparison_serie_type_code : str or None
        The unique code of the meter data serie to compare against `serie_type_code`
        when applying overshoot calculations.
    """

    tariff_component_type_id: int
    calc_strategy_code: str
    serie_type_code: str | None
    comparison_serie_type_code: str | None


class TariffCalculationResult(NamedTuple):
    r"""The result of the tariff calculations.

    Parameters
    ----------
    tariff_value_facility : duckdb.DuckDBPyRelation
        The tariff value per facility and tariff component type.

    tariff_value_total : duckdb.DuckDBPyRelation
        The total tariff value per tariff component.

    df_invalid : pd.DataFrame
        The facilities with calculated tariff values that did not pass the validation.
    """

    tariff_value_facility: duckdb.DuckDBPyRelation
    tariff_value_total: duckdb.DuckDBPyRelation
    df_invalid: pd.DataFrame


def _validate_tariff_value_facility(
    table: str, conn: duckdb.DuckDBPyConnection
) -> tuple[pd.DataFrame, OperationResult]:
    r"""Validate the result of the tariff value calculations per facility.

    Parameters
    ----------
    table : str
        The name of the temporary table where the tariff value
        per facility result is stored.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which `table` exists.

    Result
    ------
    df : pandas.DataFrame
        The facilities that did not pass the validation.

    result : elsabio.core.OperationResult
        The result of the validation.
    """

    c_tariff_id = TariffValueFacilityDataFrameModel.c_tariff_id
    c_facility_id = TariffValueFacilityDataFrameModel.c_facility_id
    c_date_id = TariffValueFacilityDataFrameModel.c_date_id
    c_tariff_component_type_id = TariffValueFacilityDataFrameModel.c_tariff_component_type_id
    c_total_value = TariffValueFacilityDataFrameModel.c_total_value
    c_price_value = TariffValueFacilityDataFrameModel.c_price_value
    c_authority_fee_value = TariffValueFacilityDataFrameModel.c_authority_fee_value

    cols = [c_tariff_id, c_facility_id, c_date_id, c_tariff_component_type_id]

    rel = conn.table(table)

    _, df = validate_duplicate_rows(
        model=rel,
        cols=cols,
        order_by=(
            (c_tariff_id, 'ASC'),
            (c_date_id, 'ASC'),
            (c_facility_id, 'ASC'),
            (c_tariff_component_type_id, 'ASC'),
        ),
        index_cols=cols,
    )
    if (nr_duplicates := df.shape[0]) > 0:
        result = OperationResult(
            ok=False,
            short_msg=(
                'Found facilities with multiple tariff components of '
                f'the same type per month and tariff ({nr_duplicates})!'
            ),
        )
        return df, result

    filter_by = (
        f'{c_total_value} IS NULL OR {c_price_value} IS NULL OR {c_authority_fee_value} IS NULL'
    )
    order_by = f'{c_tariff_id} ASC, {c_date_id} ASC, {c_facility_id} ASC'

    df = (
        rel.filter(filter_by)
        .order(order_by)
        .to_df(date_as_object=True)
        .set_index([c_facility_id, c_date_id])
    )

    if (nr_invalid := df.shape[0]) > 0:
        result = OperationResult(
            ok=False,
            short_msg=(
                f'Found tariff value records ({nr_invalid}) with missing values in columns: '
                f'"{c_total_value}" or "{c_price_value}" or "{c_authority_fee_value}"!'
            ),
        )
    else:
        result = OperationResult(ok=True)

    return df, result


def _calc_periodization_factor(rel: duckdb.DuckDBPyRelation) -> duckdb.DuckDBPyRelation:
    r"""Calculate the periodization factor to periodize revenue/costs into monthly values.

    :attr:`elsabio.models.tariff_analyzer.PeriodizeStrategyEnum.PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH`
    is defined as "nr days in month / nr days in year".

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The tariff calculation dataset with the periodization factor column added.
    """

    c_date_id = TariffCalculationDataFrameModel.c_date_id
    c_periodize_strategy_code = TariffCalculationDataFrameModel.c_periodize_strategy_code

    periodization_factor_stmt = f"""\
    (
        CASE
            WHEN {c_periodize_strategy_code} = '{PeriodizeStrategyEnum.PER_MONTH}' THEN
                1
            WHEN {c_periodize_strategy_code} = '{PeriodizeStrategyEnum.PER_YEAR_DIVIDE_BY_12}' THEN
                1/12
            WHEN {c_periodize_strategy_code} = '{PeriodizeStrategyEnum.PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH}' THEN
                day(({c_date_id} + INTERVAL '1 month') - {c_date_id}) /
                day((date_trunc('year', {c_date_id}) + INTERVAL '1 year') - date_trunc('year', {c_date_id}))
        END
    ) AS {TariffCalculationExtendedDataFrameModel.c_periodization_factor}
"""
    return rel.select(f'*, {periodization_factor_stmt}')


def _join_serie_values(
    rel: duckdb.DuckDBPyRelation,
    serie_value_rel: duckdb.DuckDBPyRelation,
    col_name: str,
    dtype: str = TARIFF_PRICE_DTYPE,
) -> duckdb.DuckDBPyRelation:
    r"""Join a meter data serie value column to the calculation dataset.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    serie_value_rel : duckdb.DuckDBPyRelation
        The meter data serie to join to tariff calculation dataset `rel`.

    col_name : str
        The name of the serie value column when joined to `rel`.

    dtype : str, default elsabio.models.tariff_analyzer.TARIFF_PRICE_DTYPE
        The DuckDB data type of the serie value column.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The tariff calculation dataset with the joined meter data column.
    """

    c_facility_id_tc = TariffCalculationExtendedDataFrameModel.c_facility_id
    c_date_id_tc = TariffCalculationExtendedDataFrameModel.c_date_id

    c_facility_id_sv = SerieValueDataFrameModel.c_facility_id
    c_date_id_sv = SerieValueDataFrameModel.c_date_id
    c_serie_value_sv = SerieValueDataFrameModel.c_serie_value

    rel_alias = 'rel'
    sv_alias = 'serie_value'

    join_condition = (
        f'{rel_alias}.{c_facility_id_tc} = {sv_alias}.{c_facility_id_sv} '
        f'AND {rel_alias}.{c_date_id_tc} = {sv_alias}.{c_date_id_sv} '
    )
    select_cols = f'{rel_alias}.*, {sv_alias}.{c_serie_value_sv}::{dtype} AS {col_name}'

    return (
        rel.set_alias(rel_alias)
        .join(serie_value_rel.set_alias(sv_alias), condition=join_condition, how='left')
        .select(select_cols)
    )


def _calc_strategy_fixed(
    rel: duckdb.DuckDBPyRelation, **_kwargs: Any
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Calculate tariff components with a fixed price.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated tariff value per facility. Adheres to the structure
        of :class:`elsabio.models.tariff_analyzer.TariffCalculationExtendedDataFrameModel`.

    elsabio.core.OperationResult
        The result of the calculation.
    """

    c_periodization_factor = TariffCalculationExtendedDataFrameModel.c_periodization_factor

    c_total_price = TariffCalculationDataFrameModel.c_total_price
    c_price = TariffCalculationDataFrameModel.c_price
    c_authority_fee = TariffCalculationDataFrameModel.c_authority_fee

    c_total_value = TariffCalculationExtendedDataFrameModel.c_total_value
    c_price_value = TariffCalculationExtendedDataFrameModel.c_price_value
    c_authority_fee_value = TariffCalculationExtendedDataFrameModel.c_authority_fee_value
    c_serie_value = TariffCalculationExtendedDataFrameModel.c_serie_value
    c_comparison_serie_value = TariffCalculationExtendedDataFrameModel.c_comparison_serie_value
    c_overshoot_value = TariffCalculationExtendedDataFrameModel.c_overshoot_value

    select_stmt = f"""*
, {c_periodization_factor} * {c_total_price} AS {c_total_value}
, {c_periodization_factor} * {c_price} AS {c_price_value}
, {c_periodization_factor} * {c_authority_fee} AS {c_authority_fee_value}
, NULL AS {c_serie_value}
, NULL AS {c_comparison_serie_value}
, NULL AS {c_overshoot_value}
"""

    return rel.select(select_stmt), OperationResult(ok=True)


def _calc_strategy_per_unit(
    rel: duckdb.DuckDBPyRelation, serie_value_rel: duckdb.DuckDBPyRelation, **_kwargs: Any
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Calculate tariff components with a price per unit of a meter data serie.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    serie_value_rel : duckdb.DuckDBPyRelation
        The meter data serie to use for the calculation.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated tariff value per facility. Adheres to the structure
        of :class:`elsabio.models.tariff_analyzer.TariffCalculationExtendedDataFrameModel`.

    elsabio.core.OperationResult
        The result of the calculation.
    """

    c_periodization_factor = TariffCalculationExtendedDataFrameModel.c_periodization_factor

    c_total_price = TariffCalculationExtendedDataFrameModel.c_total_price
    c_price = TariffCalculationExtendedDataFrameModel.c_price
    c_authority_fee = TariffCalculationExtendedDataFrameModel.c_authority_fee

    c_total_value = TariffCalculationExtendedDataFrameModel.c_total_value
    c_price_value = TariffCalculationExtendedDataFrameModel.c_price_value
    c_authority_fee_value = TariffCalculationExtendedDataFrameModel.c_authority_fee_value
    c_serie_value = TariffCalculationExtendedDataFrameModel.c_serie_value
    c_comparison_serie_value = TariffCalculationExtendedDataFrameModel.c_comparison_serie_value
    c_overshoot_value = TariffCalculationExtendedDataFrameModel.c_overshoot_value

    rel = _join_serie_values(
        rel, serie_value_rel=serie_value_rel, col_name=c_serie_value, dtype=TARIFF_PRICE_DTYPE
    )

    select_stmt = f"""*
, {c_periodization_factor} * {c_total_price} * {c_serie_value} AS {c_total_value}
, {c_periodization_factor} * {c_price} * {c_serie_value} AS {c_price_value}
, {c_periodization_factor} * {c_authority_fee} * {c_serie_value} AS {c_authority_fee_value}
, NULL AS {c_comparison_serie_value}
, NULL AS {c_overshoot_value}
"""

    return rel.select(select_stmt), OperationResult(ok=True)


def _calc_strategy_contracted_power(
    rel: duckdb.DuckDBPyRelation, strategy: CalcStrategyEnum, **_kwargs: Any
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Calculate contracted power tariff components.

    Contracted power is defined as subscribed power or connection power.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    strategy : elsabio.models.tariff_analyzer.CalcStrategyEnum
        The subscribed or connection power strategy to apply.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated tariff value per facility. Adheres to the structure
        of :class:`elsabio.models.tariff_analyzer.TariffCalculationExtendedDataFrameModel`.

    elsabio.core.OperationResult
        The result of the calculation.

    Raises
    ------
    elsabio.ElSabioError
        If an invalid value for `strategy` is supplied.
    """

    c_periodization_factor = TariffCalculationExtendedDataFrameModel.c_periodization_factor

    c_total_price = TariffCalculationExtendedDataFrameModel.c_total_price
    c_price = TariffCalculationExtendedDataFrameModel.c_price
    c_authority_fee = TariffCalculationExtendedDataFrameModel.c_authority_fee

    c_subscribed_power = TariffCalculationExtendedDataFrameModel.c_subscribed_power
    c_connection_power = TariffCalculationExtendedDataFrameModel.c_connection_power

    c_total_value = TariffCalculationExtendedDataFrameModel.c_total_value
    c_price_value = TariffCalculationExtendedDataFrameModel.c_price_value
    c_authority_fee_value = TariffCalculationExtendedDataFrameModel.c_authority_fee_value
    c_serie_value = TariffCalculationExtendedDataFrameModel.c_serie_value
    c_comparison_serie_value = TariffCalculationExtendedDataFrameModel.c_comparison_serie_value
    c_overshoot_value = TariffCalculationExtendedDataFrameModel.c_overshoot_value

    calc_cols = {
        CalcStrategyEnum.SUBSCRIBED_POWER: c_subscribed_power,
        CalcStrategyEnum.CONNECTION_POWER: c_connection_power,
    }
    calc_col = calc_cols.get(strategy)

    if calc_col is None:
        raise ElSabioError(
            f'Invalid value "{strategy}" for strategy! Expected ({tuple(calc_cols.keys())})'
        )

    select_stmt = f"""*
, {c_periodization_factor} * {c_total_price} * {calc_col} AS {c_total_value}
, {c_periodization_factor} * {c_price} * {calc_col} AS {c_price_value}
, {c_periodization_factor} * {c_authority_fee} * {calc_col} AS {c_authority_fee_value}
, {calc_col} AS {c_serie_value}
, NULL AS {c_comparison_serie_value}
, NULL AS {c_overshoot_value}
"""

    return rel.select(select_stmt), OperationResult(ok=True)


def _calc_strategy_overshoot(
    rel: duckdb.DuckDBPyRelation,
    serie_value_rel: duckdb.DuckDBPyRelation,
    comparison_serie_value_rel: duckdb.DuckDBPyRelation,
    strategy: CalcStrategyEnum,
    **_kwargs: Any,
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Calculate overshoot tariff components.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    serie_value_rel : duckdb.DuckDBPyRelation
        The meter data serie to use for the overshoot calculations.

    comparison_serie_value_rel : duckdb.DuckDBPyRelation or None
        The optional meter data serie to compare against `serie_value_rel` to
        determine the overshoot.

    strategy : elsabio.models.tariff_analyzer.CalcStrategyEnum
        The overshoot strategy to apply.

    _kwargs : Any
        Additional keyword arguments not used by the function.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated overshoot tariff value per facility. Adheres to the structure
        of :class:`elsabio.models.tariff_analyzer.TariffCalculationExtendedDataFrameModel`.

    elsabio.core.OperationResult
        The result of the calculation.

    Raises
    ------
    elsabio.ElSabioError
        If an invalid value for `strategy` is supplied.
    """

    c_periodization_factor = TariffCalculationExtendedDataFrameModel.c_periodization_factor

    c_total_price = TariffCalculationDataFrameModel.c_total_price
    c_price = TariffCalculationDataFrameModel.c_price
    c_authority_fee = TariffCalculationDataFrameModel.c_authority_fee

    c_subscribed_power = TariffCalculationExtendedDataFrameModel.c_subscribed_power
    c_connection_power = TariffCalculationExtendedDataFrameModel.c_connection_power

    c_total_value = TariffCalculationExtendedDataFrameModel.c_total_value
    c_price_value = TariffCalculationExtendedDataFrameModel.c_price_value
    c_authority_fee_value = TariffCalculationExtendedDataFrameModel.c_authority_fee_value

    c_serie_value = TariffCalculationExtendedDataFrameModel.c_serie_value
    c_comparison_serie_value = TariffCalculationExtendedDataFrameModel.c_comparison_serie_value
    c_overshoot_limit = TariffCalculationExtendedDataFrameModel.c_overshoot_limit
    c_overshoot_value = TariffCalculationExtendedDataFrameModel.c_overshoot_value

    c_overshoot = '_overshoot'

    calc_cols = {
        CalcStrategyEnum.OVERSHOOT_SUBSCRIBED_POWER: c_subscribed_power,
        CalcStrategyEnum.OVERSHOOT_CONNECTION_POWER: c_connection_power,
        CalcStrategyEnum.OVERSHOOT_COMPARISON_METER_DATA_SERIE: c_comparison_serie_value,
    }
    calc_col = calc_cols.get(strategy)

    if calc_col is None:
        raise ElSabioError(
            f'Invalid value "{strategy}" for strategy! Expected ({tuple(calc_cols.keys())})'
        )

    rel = _join_serie_values(
        rel, serie_value_rel=serie_value_rel, col_name=c_serie_value, dtype=TARIFF_PRICE_DTYPE
    )

    if strategy == CalcStrategyEnum.OVERSHOOT_COMPARISON_METER_DATA_SERIE:
        rel = _join_serie_values(
            rel,
            serie_value_rel=comparison_serie_value_rel,
            col_name=calc_col,
            dtype=TARIFF_PRICE_DTYPE,
        )

    select_stmt = f"""*
, {c_serie_value} -  ({calc_col} * {c_overshoot_limit}) AS {c_overshoot}
, if({c_overshoot} > 0, {c_overshoot}, 0)::{TARIFF_PRICE_DTYPE} AS {c_overshoot_value}
, {c_periodization_factor} * {c_total_price} * {c_overshoot_value} AS {c_total_value}
, {c_periodization_factor} * {c_price} * {c_overshoot_value} AS {c_price_value}
, {c_periodization_factor} * {c_authority_fee} * {c_overshoot_value} AS {c_authority_fee_value}
, {calc_col} AS {c_comparison_serie_value}
"""

    return rel.select(select_stmt), OperationResult(ok=True)


calc_strategies: dict[str, StrategyFunction] = {
    CalcStrategyEnum.FIXED: _calc_strategy_fixed,
    CalcStrategyEnum.PER_UNIT: _calc_strategy_per_unit,
    CalcStrategyEnum.SUBSCRIBED_POWER: _calc_strategy_contracted_power,
    CalcStrategyEnum.CONNECTION_POWER: _calc_strategy_contracted_power,
    CalcStrategyEnum.OVERSHOOT_SUBSCRIBED_POWER: _calc_strategy_overshoot,
    CalcStrategyEnum.OVERSHOOT_CONNECTION_POWER: _calc_strategy_overshoot,
    CalcStrategyEnum.OVERSHOOT_COMPARISON_METER_DATA_SERIE: _calc_strategy_overshoot,
}


def _calc_by_strategy(
    calc_strategy_code: str,
    rel: duckdb.DuckDBPyRelation,
    serie_value_rel: duckdb.DuckDBPyRelation | None,
    comparison_serie_value_rel: duckdb.DuckDBPyRelation | None,
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Calculate the tariff values per facility by strategy.

    Parameters
    ----------
    calc_strategy_code : str
        The unique code of the calculation strategy to apply.

    rel : duckdb.DuckDBPyRelation
        The source dataset of the tariff calculations. Should adhere to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    serie_value_rel : duckdb.DuckDBPyRelation or None
        The optional meter data serie to use for the calculations.

    comparison_serie_value_rel : duckdb.DuckDBPyRelation or None
        The optional meter data serie to compare against `serie_value_rel` in
        overshoot calculations.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated tariff value per facility. Adheres to the structure of
        :class:`elsabio.models.tariff_analyzer.TariffCalculationExtendedDataFrameModel`.

    elsabio.core.OperationResult
        The result of the calculation.

    Raises
    ------
    elsabio.ElSabioError
        If an invalid value for `calc_strategy_code` is supplied.
    """

    func = calc_strategies.get(calc_strategy_code)
    if func is None:
        raise ElSabioError(
            f'Missing tariff calculation function for strategy "{calc_strategy_code}"!'
        )

    serie_value_strategies = {
        CalcStrategyEnum.PER_UNIT,
        CalcStrategyEnum.OVERSHOOT_SUBSCRIBED_POWER,
        CalcStrategyEnum.OVERSHOOT_CONNECTION_POWER,
    }
    if serie_value_rel is None and calc_strategy_code in serie_value_strategies:
        result = OperationResult(
            ok=False,
            short_msg=f'No serie value found for calc_strategy_code "{calc_strategy_code}"!',
        )
        return rel, result

    if (
        comparison_serie_value_rel is None
        and calc_strategy_code == CalcStrategyEnum.OVERSHOOT_COMPARISON_METER_DATA_SERIE
    ):
        result = OperationResult(
            ok=False,
            short_msg=f'No comparison serie value found for calc_strategy_code "{calc_strategy_code}"!',
        )
        return rel, result

    return func(
        rel=rel,
        serie_value_rel=serie_value_rel,
        comparison_serie_value_rel=comparison_serie_value_rel,
        strategy=calc_strategy_code,
    )


def get_serie_types(rel: duckdb.DuckDBPyRelation) -> tuple[str, ...]:
    r"""Get the serie types of the meter data needed for the tariff calculations.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The tariff calculation dataset. Should adhere to the structure of model
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    Returns
    -------
    tuple[str, ...]
        The unique serie types found in the calculation dataset `rel`.
    """

    c_serie_type_code = TariffCalculationDataFrameModel.c_serie_type_code
    c_comparison_serie_type_code = TariffCalculationDataFrameModel.c_comparison_serie_type_code

    serie_type_df = (
        rel.unique(c_serie_type_code)
        .union(rel.unique(c_comparison_serie_type_code))
        .unique(c_serie_type_code)
        .filter(f'{c_serie_type_code} IS NOT NULL')
        .to_df()
    )

    return tuple(serie_type_df[c_serie_type_code])


def load_meter_data(
    path: Path,
    serie_types: Sequence[str],
    start_date: date,
    end_date: date | None = None,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> tuple[dict[str, duckdb.DuckDBPyRelation], OperationResult]:
    r"""Load meter data for given serie types.

    Parameters
    ----------
    path : Path
        The path to the root of the parquet hive from which to the load meter data.

    serie_types : Sequence[str]
        The serie types to load.

    start_date : date
        The start date of the interval in which to load the meter data (inclusive).

    end_date : date or None, default None
        The end date of the interval in which to load the meter data (exclusive).
        If None the interval is open and unbounded.

    conn : duckdb.DuckDBPyConnection or None, default None
        The DuckDB connection to use for querying the parquet file(s).
        If None the global DuckDB in-memory database is used.

    Returns
    -------
    dict[str, duckdb.DuckDBPyRelation]
        The relation objects of the loaded meter data keyed by their serie type code.
        The relation objects adheres to the structure of model
        :class:`elsabio.models.tariff_analyzer.SerieValueDataFrameModel`.

    elsabio.core.OperationResult
        The result of loading the meter data.
    """

    meter_data = {}

    for serie_type_code in serie_types:
        rel, result = read_meter_data_parquet_hive(
            path=path,
            serie_type_code=serie_type_code,
            start_date=start_date,
            end_date=end_date,
            conn=conn,
        )
        if not result.ok:
            return {}, result

        meter_data[serie_type_code] = rel

    return meter_data, OperationResult(ok=True)


def _get_meter_data(
    meter_data: dict[str, duckdb.DuckDBPyRelation], serie_type_code: str | None, name: str
) -> tuple[duckdb.DuckDBPyRelation | None, OperationResult]:
    r"""Get the meter data for given serie type.

    Parameters
    ----------
    meter_data : dict[str, duckdb.DuckDBPyRelation]
        The mapping of serie type code to meter data relation object.

    serie_type_code : str or None
        The unique code of the serie type to extract from `meter_data`.
        If None no meter data need to be extracted.

    name : str
        The name of the serie type code column. Used for improved error context
        should `serie_type_code` be missing in `meter_data`.

    Returns
    -------
    duckdb.DuckDBPyRelation or None
        The relation object of the dataset with meter data.
        Adheres to the structure of model :class:`elsabio.models.tariff_analyzer.SerieValueDataFrameModel`.
        None is returned if `serie_type_code` was not found in `meter_data` or if `serie_type_code` is None.

    elsabio.core.OperationResult
        The result of retrieving the meter data.
    """

    if serie_type_code is None:
        return None, OperationResult(ok=True)

    rel = meter_data.get(serie_type_code)

    if rel is None:
        result = OperationResult(
            ok=False, short_msg=f'Missing required meter data for {name} "{serie_type_code}"'
        )
        return None, result

    return rel, OperationResult(ok=True)


def _get_strategy_rows(rel: duckdb.DuckDBPyRelation) -> Generator[StrategyColumns]:
    r"""Get the unique rows with the strategy columns needed to perform the calculations.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The tariff calculation dataset. Should adhere to the structure of model
        :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    Returns
    -------
    Generator[StrategyColumns]
        The rows with the strategy columns needed to perform the calculations.
    """

    c_tariff_component_type_id = TariffCalculationDataFrameModel.c_tariff_component_type_id

    unique_rows = (
        f'{TariffCalculationDataFrameModel.c_tariff_component_type_id}, '
        f'{TariffCalculationDataFrameModel.c_calc_strategy_code}, '
        f'{TariffCalculationDataFrameModel.c_serie_type_code}, '
        f'{TariffCalculationDataFrameModel.c_comparison_serie_type_code}'
    )
    rows = rel.unique(unique_rows).order(f'{c_tariff_component_type_id} ASC').fetchall()

    for row in rows:
        yield StrategyColumns(*row)


def create_tariff_calc_source_rel(
    model: TariffCalculationDataFrameModel, conn: duckdb.DuckDBPyConnection
) -> duckdb.DuckDBPyRelation:
    r"""Create the relation object from the input data `model` to the tariff calculations.

    Parameters
    ----------
    model : elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel
        The source model from which to create the DuckDB relation object.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which to create the relation object.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The DuckDB relation object with the input data to the tariff calculations.
    """

    select_cols = '\n'.join(
        f', {col}::{dtype} AS {col}'
        for col, dtype in TariffCalculationDataFrameModel.duckdb_dtypes.items()
    )

    select_cols = select_cols[2:]  # Remove first unwanted ", "

    return conn.from_df(model.df).select(select_cols)


def _save_tariff_value_facility_to_temp_table(rel: duckdb.DuckDBPyRelation, table: str) -> str:
    r"""Save the results per tariff component type to a table the temporary DuckDB database.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The dataset to save to the table.

    table : str
        The name of the table in which to save `rel`.

    Returns
    -------
    table : str
        The name of the table where the dataset was saved.
    """

    select_cols = '\n'.join(
        f', {col}::{dtype} AS {col}'
        for col, dtype in TariffValueFacilityDataFrameModel.duckdb_dtypes.items()
    )

    select_cols = select_cols[2:]  # Remove first unwanted ", "

    rel = rel.select(select_cols)

    try:
        rel.insert_into(table)
    except duckdb.CatalogException:
        rel.to_table(table)

    return table


def _load_tariff_value_facility(
    table: str, conn: duckdb.DuckDBPyConnection
) -> duckdb.DuckDBPyRelation:
    r"""Load the calculated tariff value per facility dataset from the temporary DuckDB database.

    Parameters
    ----------
    table : str
        The table from which to load the tariff value per facility model.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which `table` exists.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset of the calculated tariff value per facility. Adheres to model
        :class:`elsabio.models.tariff_analyzer.TariffValueFacilityDataFrameModel`.
    """

    order_by = f"""\
{TariffValueFacilityDataFrameModel.c_tariff_id}                  ASC
, {TariffValueFacilityDataFrameModel.c_date_id}                  ASC
, {TariffValueFacilityDataFrameModel.c_tariff_component_type_id} ASC
, {TariffValueFacilityDataFrameModel.c_tariff_cost_group_id}     ASC
, {TariffValueFacilityDataFrameModel.c_customer_group_id}        ASC
, {TariffValueFacilityDataFrameModel.c_facility_id}              ASC
"""

    return conn.table(table).order(order_by)


def _calc_tariff_value_total(
    table: str, conn: duckdb.DuckDBPyConnection
) -> duckdb.DuckDBPyRelation:
    r"""Calculate the total tariff value per tariff component.

    Parameters
    ----------
    table : str
        The source table from which to calculate the total tariff value per tariff component.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which `table` exists.

    Returns
    -------
    duckdb.DuckDBPyRelation
        The dataset representing the total tariff value model. Adheres to model
        :class:`elsabio.models.tariff_analyzer.TariffValueTotalDataFrameModel`.
    """

    c_tariff_id = TariffValueTotalDataFrameModel.c_tariff_id
    c_date_id = TariffValueTotalDataFrameModel.c_date_id
    c_tariff_cost_group_id = TariffValueFacilityDataFrameModel.c_tariff_cost_group_id
    c_customer_group_id = TariffValueFacilityDataFrameModel.c_customer_group_id
    c_tariff_component_type_id = TariffValueFacilityDataFrameModel.c_tariff_component_type_id
    c_tariff_component_id = TariffValueFacilityDataFrameModel.c_tariff_component_id

    c_total_value = TariffValueFacilityDataFrameModel.c_total_value
    c_price_value = TariffValueFacilityDataFrameModel.c_price_value
    c_authority_fee_value = TariffValueFacilityDataFrameModel.c_authority_fee_value

    query = f"""\
SELECT
    {TariffValueFacilityDataFrameModel.c_tariff_id} AS {c_tariff_id}
    , {TariffValueFacilityDataFrameModel.c_date_id} AS {c_date_id}
    , {TariffValueFacilityDataFrameModel.c_tariff_cost_group_id} AS {c_tariff_cost_group_id}
    , {TariffValueFacilityDataFrameModel.c_customer_group_id} AS {c_customer_group_id}
    , {TariffValueFacilityDataFrameModel.c_tariff_component_type_id} AS {c_tariff_component_type_id}
    , {TariffValueFacilityDataFrameModel.c_tariff_component_id} AS {c_tariff_component_id}
    , round(sum({TariffValueFacilityDataFrameModel.c_total_value}), 3) AS {c_total_value}
    , round(sum({TariffValueFacilityDataFrameModel.c_price_value}), 3) AS {c_price_value}
    , round(sum({TariffValueFacilityDataFrameModel.c_authority_fee_value}), 3) AS {c_authority_fee_value}

FROM {table}

GROUP BY ALL

ORDER BY
    {c_tariff_id}                  ASC
    , {c_date_id}                  ASC
    , {c_tariff_component_type_id} ASC
    , {c_tariff_cost_group_id}     ASC
    , {c_customer_group_id}        ASC
    , {c_tariff_component_id}      ASC

"""  # noqa: S608

    return conn.sql(query)


def calc_tariff_value(
    calc_rel: duckdb.DuckDBPyRelation,
    meter_data: dict[str, duckdb.DuckDBPyRelation],
    conn: duckdb.DuckDBPyConnection,
) -> tuple[TariffCalculationResult, OperationResult]:
    r"""Calculate the tariff value.

    Parameters
    ----------
    calc_model : duckdb.DuckDBPyRelation
        The data model with the input data to the tariff calculations. Should adhere to the
        structure of :class:`elsabio.models.tariff_analyzer.TariffCalculationDataFrameModel`.

    meter_data : dict[str, duckdb.DuckDBPyRelation]
        The available meter data to use in the calculations. The key is
        the serie_type_code of the underlying serie type of the meter data.

    conn : duckdb.DuckDBPyConnection
        The DuckDB connection in which to save temporary calculation results.

    Returns
    -------
    calc_result : elsabio.operations.tariff_analyzer.tariff.TariffCalculationResult
        The computed datasets from the tariff value calculations.

    result : elsabio.core.OperationResult
        The result if the calculations were successful or not.
    """

    c_tariff_component_type_id = TariffCalculationDataFrameModel.c_tariff_component_type_id
    c_serie_type_code = TariffCalculationDataFrameModel.c_serie_type_code
    c_comparison_serie_type_code = TariffCalculationDataFrameModel.c_comparison_serie_type_code

    calc_rel = _calc_periodization_factor(rel=calc_rel)

    error_msgs = []
    for row in _get_strategy_rows(rel=calc_rel):
        calc_tct_rel = calc_rel.filter(
            f'{c_tariff_component_type_id} = {row.tariff_component_type_id}'
        )

        serie_value_rel, result = _get_meter_data(
            meter_data=meter_data, serie_type_code=row.serie_type_code, name=c_serie_type_code
        )
        if not result.ok:
            error_msgs.append(result.short_msg)
            continue

        comparison_serie_value_rel, result = _get_meter_data(
            meter_data=meter_data,
            serie_type_code=row.comparison_serie_type_code,
            name=c_comparison_serie_type_code,
        )
        if not result.ok:
            error_msgs.append(result.short_msg)
            continue

        rel, result = _calc_by_strategy(
            calc_strategy_code=row.calc_strategy_code,
            rel=calc_tct_rel,
            serie_value_rel=serie_value_rel,
            comparison_serie_value_rel=comparison_serie_value_rel,
        )
        if not result.ok:
            error_msgs.append(result.short_msg)
            continue

        _save_tariff_value_facility_to_temp_table(rel=rel, table=FACILITY_TARIFF_VALUE_TABLE_NAME)

    df_invalid, result = _validate_tariff_value_facility(
        table=FACILITY_TARIFF_VALUE_TABLE_NAME, conn=conn
    )

    error_msg = ''
    if error_msgs:
        error_msg = '\n'.join(m for m in error_msgs)

    if not result.ok:
        error_msg = f'{error_msg}\n{result.short_msg}' if error_msg else result.short_msg
        result = OperationResult(ok=False, short_msg=error_msg)

    else:
        result = OperationResult(ok=True)

    tariff_value_facility_rel = _load_tariff_value_facility(
        conn=conn, table=FACILITY_TARIFF_VALUE_TABLE_NAME
    )
    tariff_value_total_rel = _calc_tariff_value_total(
        conn=conn, table=FACILITY_TARIFF_VALUE_TABLE_NAME
    )

    calc_result = TariffCalculationResult(
        tariff_value_facility=tariff_value_facility_rel,
        tariff_value_total=tariff_value_total_rel,
        df_invalid=df_invalid,
    )

    return calc_result, result


def write_tariff_value_calc_result_to_parquet(
    rel: duckdb.DuckDBPyRelation,
    path: Path,
    tariff_value_type: Literal['facility', 'total'],
    overwrite: bool = True,
) -> OperationResult:
    r"""Write the tariff value calculation result to the parquet hive.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The data model with the tariff value result to write to parquet.
        Should adhere to the structure of the models
        :class:`elsabio.models.tariff_analyzer.TariffValueFacilityDataFrameModel` or
        :class:`elsabio.models.tariff_analyzer.TariffValueTotalDataFrameModel`.

    path : pathlib.Path
        The full path to the root of the parquet hive in which t0 write the parquet files.

    tariff_value_type : Literal['facility', 'total']
        The type of tariff value model to write to the parquet hive.

    overwrite : bool, default True
        True if existing tariff value calculation results should
        be allowed to be overwritten and False otherwise.

    Returns
    -------
    result : elsabio.core.OperationResult
        The result writing the data model to the parquet hive.

    Raises
    ------
    elsabio.ElSabioError
        If an invalid value for `tariff_value_type` is supplied.
    """

    if tariff_value_type == 'facility':
        c_tariff_id = TariffValueFacilityDataFrameModel.c_tariff_id
        c_date_id = TariffValueFacilityDataFrameModel.c_date_id
    elif tariff_value_type == 'total':
        c_tariff_id = TariffValueTotalDataFrameModel.c_tariff_id
        c_date_id = TariffValueTotalDataFrameModel.c_date_id
    else:
        raise ElSabioError(
            f'Invalid value "{tariff_value_type}" for tariff_value_type! '
            "Expected ('facility', 'total')"
        )

    return write_parquet(
        rel=rel, path=path, partition_by=[c_tariff_id, c_date_id], overwrite=overwrite
    )
