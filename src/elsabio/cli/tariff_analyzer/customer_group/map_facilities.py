# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `elsabio ta cg map-facilities`."""

# Standard library
import logging

# Third party
import click
import duckdb
import pandas as pd

# Local
from elsabio.cli.core import DATE_RANGE_PARAM, Color, echo_with_log, exit_program, load_resources
from elsabio.cli.display import display_dataframe
from elsabio.core import OperationResult
from elsabio.database import Session
from elsabio.database.tariff_analyzer import (
    bulk_insert_facility_customer_group_links,
    bulk_update_facility_customer_group_links,
    load_customer_group_model,
    load_facility_contract_extended_model,
    load_facility_customer_group_link_model,
)
from elsabio.datetime import DateRange
from elsabio.operations.tariff_analyzer import (
    create_facility_customer_group_link_upsert_dataframes,
    map_facilities_to_customer_groups,
    validate_duplicate_facility_customer_group_links,
    validate_facility_customer_group_input_data_models,
)


def _upsert_facility_customer_group_links(
    session: Session, df_insert: pd.DataFrame, df_update: pd.DataFrame
) -> OperationResult:
    r"""Insert new and update existing facility customer group links.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.

    df_insert : pandas.DataFrame
        The DataFrame with facility customer group links to insert.

    df_update : pandas.DataFrame
        The DataFrame with facility customer group links to update.

    Returns
    -------
    result : elsabio.core.OperationResult
        The result of inserting and updating the facility customer group links.
    """

    result = bulk_insert_facility_customer_group_links(session=session, df=df_insert)
    if not result.ok:
        return result

    return bulk_update_facility_customer_group_links(session=session, df=df_update)


@click.command()
@click.option(
    '--interval',
    '-i',
    type=DATE_RANGE_PARAM,
    metavar='START..END',
    default='CM-1M..CM',
    help=(
        'The interval (absolute or relative) in which to map facilities. '
        'Inclusive on start date and exclusive on end date. Examples: '
        '"2025-11-01..2025-12-01", '
        '"CM-1M..CM" : Previous month until but not including current month.'
    ),
)
@click.pass_context
def map_facilities(ctx: click.Context, interval: DateRange) -> None:
    """Map facilities to customer groups"""

    _, session_factory = load_resources(ctx=ctx)

    with session_factory() as session:
        cg_model, result = load_customer_group_model(session)
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        _start_date, _end_date = interval
        start_date = _start_date.date()
        end_date = _end_date if _end_date is None else _end_date.date()

        f_cg_link_model, result = load_facility_customer_group_link_model(
            session, start_date=start_date, end_date=end_date
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        fc_model, result = load_facility_contract_extended_model(
            session=session, start_date=start_date, end_date=end_date
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        with duckdb.connect() as conn:
            result = validate_facility_customer_group_input_data_models(
                cg_model=cg_model, fc_model=fc_model
            )
            if not result.ok:
                exit_program(error=True, ctx=ctx, message=result.short_msg)

            f_cg_link_rel, df_unmapped, result = map_facilities_to_customer_groups(
                cg_model=cg_model, fc_model=fc_model, conn=conn
            )
            if not result.ok:
                echo_with_log(
                    message=f'{result.short_msg}\n{display_dataframe(df_unmapped, as_str=True)}\n',
                    log_level=logging.WARNING,
                    color=Color.WARNING,
                )

            result, df_duplicates = validate_duplicate_facility_customer_group_links(
                f_cg_link_rel=f_cg_link_rel
            )
            if not result.ok:
                exit_program(
                    error=True,
                    ctx=ctx,
                    message=f'{result.short_msg}\n{display_dataframe(df_duplicates, as_str=True)}\n',
                )

            dfs = create_facility_customer_group_link_upsert_dataframes(
                f_cg_link_rel=f_cg_link_rel, f_cg_link_model_existing=f_cg_link_model, conn=conn
            )

        result = _upsert_facility_customer_group_links(
            session=session, df_insert=dfs.insert, df_update=dfs.update
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

    exit_program(
        error=False,
        ctx=ctx,
        message=(
            f'Successfully imported {dfs.insert.shape[0]} new facility customer group links '
            f'and updated {dfs.update.shape[0]} existing facility customer group links '
            f'in interval {start_date} - {end_date}!'
        ),
    )
