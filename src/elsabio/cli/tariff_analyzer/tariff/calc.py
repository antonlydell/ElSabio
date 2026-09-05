# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `elsabio ta tariff calc`."""

# Standard library
import logging

# Third party
import click

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
from elsabio.datetime import DateRange
from elsabio.operations.tariff_analyzer.tariff import run_tariff_calc


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
        'The tariff_id:s of the tariffs to calculate specified as a comma separated list '
        '(e.g. "1, 2"). If not specified all defined tariffs are calculated.'
    ),
)
@click.pass_context
def calc(ctx: click.Context, interval: DateRange, tariffs: tuple[int, ...] | None) -> None:
    """Calculate the value (revenue/cost) of tariffs"""

    cm, session_factory = load_resources(ctx=ctx)

    _start_date, _end_date = interval
    start_date = _start_date.date()
    end_date = _end_date if _end_date is None else _end_date.date()

    outcome, result = run_tariff_calc(
        session_factory=session_factory,
        cfg=cm.tariff_analyzer,
        start_date=start_date,
        end_date=end_date,
        tariff_ids=tariffs,
    )

    if not outcome.completed:
        exit_program(error=True, ctx=ctx, message=result.short_msg)

    if (df_invalid := outcome.df_invalid) is not None:
        echo_with_log(
            message=(
                f'{result.short_msg}\n'
                f'{display_dataframe(df_invalid, as_str=True, max_nr_cols=15)}\n'
            ),
            log_level=logging.ERROR,
            color=Color.ERROR,
        )

    for write_error in outcome.write_errors:
        echo_with_log(message=write_error.short_msg, log_level=logging.ERROR, color=Color.ERROR)

    error = not result.ok

    if error:
        message = (
            f'Calculated tariffs with tariff_id:s {outcome.tariff_ids} '
            f'in interval [{start_date}, {end_date}) with errors detected!\n'
            f'Check "{outcome.error_file}" for details about the facilities '
            f'that could not be calculated.'
        )
    else:
        message = (
            f'Successfully calculated tariffs with tariff_id:s {outcome.tariff_ids} '
            f'in interval [{start_date}, {end_date})!'
        )

    exit_program(error=error, ctx=ctx, message=message)
