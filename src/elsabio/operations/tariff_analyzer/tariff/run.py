# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The orchestration of a tariff calculation run in the Tariff Analyzer module."""

# Standard library
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Literal, NamedTuple

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.config import TariffAnalyzerConfig
from elsabio.core import OperationResult
from elsabio.database import SessionFactory
from elsabio.database.tariff_analyzer import load_tariff_calculation_model, load_tariff_ids
from elsabio.operations.file import write_csv

from .calc import (
    calc_tariff_value,
    create_tariff_calc_source_rel,
    get_serie_types,
    load_meter_data,
    write_tariff_value_calc_result_to_parquet,
)

TARIFF_CALC_ERROR_FILENAME = 'tariff_calc_error.csv'


class TariffCalcRunOutcome(NamedTuple):
    r"""The outcome of a tariff calculation run.

    Parameters
    ----------
    tariff_ids : tuple[int, ...], default ()
        The tariff_id:s of the tariffs that the run calculated. Empty if the
        run was aborted before the tariffs to calculate could be resolved.

    completed : bool, default False
        True if the run reached the stage of writing its result and False if it was
        aborted before that. A completed run is not necessarily a successful one: it
        may have produced invalid values for some facilities, in which case the
        accompanying :class:`elsabio.core.OperationResult` is not ok, and a result
        that could not be written is reported in `write_errors`.

    df_invalid : pandas.DataFrame or None, default None
        The facilities with calculated tariff values that did not pass the validation.
        None if all facilities passed the validation.

    error_file : pathlib.Path or None, default None
        The full path to the csv file that `df_invalid` was written to.
        None if there were no facilities that failed the validation.

    write_errors : tuple[elsabio.core.OperationResult, ...], default ()
        The results of the writes that failed without aborting the run.
    """

    tariff_ids: tuple[int, ...] = ()
    completed: bool = False
    df_invalid: pd.DataFrame | None = None
    error_file: Path | None = None
    write_errors: tuple[OperationResult, ...] = ()


def _write_tariff_values(
    calc_result_rels: tuple[
        tuple[Literal['facility', 'total'], duckdb.DuckDBPyRelation, Path], ...
    ],
) -> tuple[OperationResult, ...]:
    r"""Write the calculated tariff values to the parquet store.

    A tariff value type that cannot be written does not abort the run,
    since the other tariff value type may still be written successfully.

    Parameters
    ----------
    calc_result_rels : tuple[tuple[Literal['facility', 'total'], duckdb.DuckDBPyRelation, pathlib.Path], ...]
        The tariff value type, its calculated relation object and the path
        to the root of the parquet hive to write the relation object to.

    Returns
    -------
    write_errors : tuple[elsabio.core.OperationResult, ...]
        The results of the tariff value types that could not be written.
    """

    write_errors: list[OperationResult] = []

    for tariff_value_type, rel, path in calc_result_rels:
        result = write_tariff_value_calc_result_to_parquet(
            rel=rel, path=path, tariff_value_type=tariff_value_type
        )
        if not result.ok:
            write_errors.append(
                OperationResult(
                    ok=False,
                    short_msg=(
                        f'Unable to write calculation result tariff value '
                        f'{tariff_value_type} to parquet hive! \n{result.short_msg}'
                    ),
                    long_msg=result.long_msg,
                    code=result.code,
                )
            )

    return tuple(write_errors)


def run_tariff_calc(
    session_factory: SessionFactory,
    cfg: TariffAnalyzerConfig,
    start_date: date,
    end_date: date | None = None,
    tariff_ids: Sequence[int] | None = None,
) -> tuple[TariffCalcRunOutcome, OperationResult]:
    r"""Calculate the value (revenue/cost) of tariffs and store the result.

    Loads the calculation input from the database and the meter data from the parquet
    store, performs the calculations and writes the tariff value per facility and the
    total tariff value back to the parquet store. Facilities that could not be properly
    calculated are written to a csv file in the error directory of `cfg`.

    The operation is the single entry point for a tariff calculation.

    Parameters
    ----------
    session_factory : elsabio.db.SessionFactory
        The session factory that can produce new database sessions.

    cfg : elsabio.config.TariffAnalyzerConfig
        The configuration of the Tariff Analyzer module, which defines the
        locations of the parquet store and the error directory.

    start_date : datetime.date
        The start date of the interval in which to perform the calculations (inclusive).

    end_date : datetime.date or None, default None
        The end date of the interval in which to perform the calculations (exclusive).
        If None the interval is open and unbounded.

    tariff_ids : Sequence[int] or None, default None
        The tariff_id:s of the tariffs to calculate. If None all defined tariffs are calculated.

    Returns
    -------
    outcome : elsabio.operations.tariff_analyzer.tariff.TariffCalcRunOutcome
        The outcome of the tariff calculation run.

    result : elsabio.core.OperationResult
        The result of the tariff calculation run.
    """

    with session_factory() as session:
        loaded_tariff_ids, result = load_tariff_ids(
            session, tariff_ids=tariff_ids, check_all_loaded=True
        )
        if not result.ok:
            return TariffCalcRunOutcome(), result

        tariff_calc_model, result = load_tariff_calculation_model(
            session=session, tariff_ids=loaded_tariff_ids, start_date=start_date, end_date=end_date
        )
        if not result.ok:
            return TariffCalcRunOutcome(tariff_ids=loaded_tariff_ids), result

    with duckdb.connect() as conn:
        calc_rel = create_tariff_calc_source_rel(model=tariff_calc_model, conn=conn)
        serie_types = get_serie_types(rel=calc_rel)

        meter_data, result = load_meter_data(
            path=cfg.meter_data_dir,
            serie_types=serie_types,
            start_date=start_date,
            end_date=end_date,
            conn=conn,
        )
        if not result.ok:
            return TariffCalcRunOutcome(tariff_ids=loaded_tariff_ids), result

        calc_result, result = calc_tariff_value(calc_rel=calc_rel, conn=conn, meter_data=meter_data)

        df_invalid: pd.DataFrame | None = None
        error_file: Path | None = None
        write_errors: list[OperationResult] = []

        if not result.ok:
            df_invalid = calc_result.df_invalid
            error_file, write_result = write_csv(
                df=df_invalid,
                output_dir=cfg.tariff_value_error_dir,
                filename=TARIFF_CALC_ERROR_FILENAME,
                sep=cfg.error_file_col_sep,
                encoding=cfg.error_file_encoding,
            )
            if not write_result.ok:
                write_errors.append(write_result)

        write_errors.extend(
            _write_tariff_values(
                calc_result_rels=(
                    ('facility', calc_result.tariff_value_facility, cfg.tariff_value_facility_dir),
                    ('total', calc_result.tariff_value_total, cfg.tariff_value_total_dir),
                )
            )
        )

    outcome = TariffCalcRunOutcome(
        tariff_ids=loaded_tariff_ids,
        completed=True,
        df_invalid=df_invalid,
        error_file=error_file,
        write_errors=tuple(write_errors),
    )

    return outcome, result
