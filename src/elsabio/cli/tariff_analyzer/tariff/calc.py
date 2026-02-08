# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `elsabio ta tariff calc`."""

# Standard library
import logging

# Third party
import click
import duckdb

# Local
from elsabio.cli.core import (
    DATE_RANGE_PARAM,
    INT_SEQUENCE_PARAM,
    Color,
    echo_with_log,
    exit_program,
    load_resources,
)
from elsabio.cli.display import display_dataframe
from elsabio.database.tariff_analyzer import load_tariff_calculation_model, load_tariff_ids
from elsabio.datetime import DateRange
from elsabio.operations.file import write_csv
from elsabio.operations.tariff_analyzer.tariff import (
    calc_tariff_value,
    create_tariff_calc_source_rel,
    get_serie_types,
    load_meter_data,
    write_tariff_value_calc_result_to_parquet,
)


@click.command()
@click.option(
    '--interval',
    '-i',
    type=DATE_RANGE_PARAM,
    metavar='START..END',
    default='CM-1M..CM',
    help=(
        'The interval (absolute or relative) in which to perform calculations. '
        'Inclusive on start date and exclusive on end date. Examples: '
        '"2025-11-01..2025-12-01", '
        '"CM-1M..CM" : Previous month until but not including current month.'
    ),
)
@click.option(
    '--tariffs',
    '-t',
    type=INT_SEQUENCE_PARAM,
    help=(
        'The tariff_id:s of the tariffs to calculate. '
        'If not specified all defined tariffs are calculated.'
    ),
)
@click.pass_context
def calc(ctx: click.Context, interval: DateRange, tariffs: tuple[int, ...] | None) -> None:
    """Calculate the value (revenue/cost) of tariffs"""

    cm, session_factory = load_resources(ctx=ctx)

    _start_date, _end_date = interval
    start_date = _start_date.date()
    end_date = _end_date if _end_date is None else _end_date.date()

    with session_factory() as session:
        loaded_tariff_ids, result = load_tariff_ids(
            session, tariff_ids=tariffs, check_all_loaded=True
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        tariff_calc_model, result = load_tariff_calculation_model(
            session=session, tariff_ids=loaded_tariff_ids, start_date=start_date, end_date=end_date
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

    with duckdb.connect() as conn:
        calc_rel = create_tariff_calc_source_rel(model=tariff_calc_model, conn=conn)
        serie_types = get_serie_types(rel=calc_rel)

        cfg = cm.tariff_analyzer
        meter_data, result = load_meter_data(
            path=cfg.meter_data_dir,
            serie_types=serie_types,
            start_date=start_date,
            end_date=end_date,
            conn=conn,
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        calc_result, result = calc_tariff_value(calc_rel=calc_rel, conn=conn, meter_data=meter_data)
        if not result.ok:
            error = True
            df_invalid = calc_result.df_invalid
            echo_with_log(
                message=f'{result.short_msg}\n{display_dataframe(df_invalid, as_str=True, max_nr_cols=15)}\n',
                log_level=logging.ERROR,
                color=Color.ERROR,
            )
            error_file, result = write_csv(
                df=df_invalid,
                output_dir=cfg.tariff_value_error_dir,
                filename='tariff_calc_error.csv',
                sep=cfg.error_file_col_sep,
                encoding=cfg.error_file_encoding,
            )
            if not result.ok:
                echo_with_log(message=result.short_msg, log_level=logging.ERROR, color=Color.ERROR)
        else:
            error = False
            error_file = None

        results = (
            (
                'facility',
                calc_result.tariff_value_facility,
                cfg.tariff_value_facility_dir,
            ),
            (
                'total',
                calc_result.tariff_value_total,
                cfg.tariff_value_total_dir,
            ),
        )
        for value in results:
            value_type, rel, path = value
            result = write_tariff_value_calc_result_to_parquet(
                rel=rel,
                path=path,
                tariff_value_type=value_type,  # type: ignore[arg-type]
            )
            if not result.ok:
                echo_with_log(
                    message=(
                        f'Unable to write calculation result tariff value '
                        f'{value_type} to parquet hive! \n{result.short_msg}'
                    ),
                    log_level=logging.ERROR,
                    color=Color.ERROR,
                )

    if error:
        message = (
            f'Calculated tariffs with tariff_id:s {loaded_tariff_ids} '
            f'in interval [{start_date}, {end_date}) with errors detected!\n'
            f'Check "{error_file}" for details about the facilities that could not be calculated.'
        )
    else:
        message = (
            f'Successfully calculated tariffs with tariff_id:s {loaded_tariff_ids} '
            f'in interval [{start_date}, {end_date})!'
        )

    exit_program(error=error, ctx=ctx, message=message)
