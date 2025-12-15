# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `ta import facility` of the Tariff Analyzer module."""

# Standard library
import logging

# Third party
import click
import duckdb

# Local
from elsabio.cli.core import Color, Obj, echo_with_log, exit_program
from elsabio.cli.tariff_analyzer.import_.core import format_list_of_files, load_data_model_to_import
from elsabio.config import ConfigManager
from elsabio.config.tariff_analyzer import DataSource
from elsabio.database import SessionFactory
from elsabio.database.tariff_analyzer import (
    bulk_insert_facilities,
    bulk_update_facilities,
    load_facility_mapping_model,
    load_facility_type_mapping_model,
)
from elsabio.operations.file import move_files
from elsabio.operations.tariff_analyzer import create_facility_upsert_dataframes


@click.command(name='facility')
@click.pass_context
def facility(ctx: click.Context) -> None:
    """Import facilities to the database of the Tariff Analyzer module."""

    cm: ConfigManager = ctx.obj[Obj.CONFIG]
    session_factory: SessionFactory = ctx.obj[Obj.SESSION_FACTORY]
    cfg = cm.tariff_analyzer.data.get(DataSource.FACILITY)

    if cfg is None:
        exit_program(
            error=True,
            ctx=ctx,
            message='No data configuration found for "tariff_analyzer.data.facility"',
        )

    with session_factory() as session:
        with duckdb.connect() as conn:
            import_model, result = load_data_model_to_import(
                method=cfg.method, path=cfg.path, conn=conn
            )
            if not result.ok:
                exit_program(error=True, ctx=ctx, message=result.short_msg)

            # TODO : Check for duplicates

            facility_model, result = load_facility_mapping_model(session)
            if not result.ok:
                exit_program(error=True, ctx=ctx, message=result.short_msg)

            facility_type_model, result = load_facility_type_mapping_model(session=session)
            if not result.ok:
                exit_program(error=True, ctx=ctx, message=result.short_msg)

            dfs, result = create_facility_upsert_dataframes(
                import_model=import_model,
                facility_model=facility_model,
                facility_type_model=facility_type_model,
                conn=conn,
            )
            if not result.ok:
                if dfs.missing_facility_type.shape[0] > 0:
                    echo_with_log(result.short_msg, log_level=logging.ERROR, color=Color.ERROR)
                    click.echo(dfs.missing_facility_type)
                    exit_program(error=True, ctx=ctx)

                exit_program(error=True, ctx=ctx, message=result.short_msg)

        result = bulk_insert_facilities(session=session, df=dfs.insert)
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        result = bulk_update_facilities(session=session, df=dfs.update)
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        target_dir = cfg.path / 'success'
        files, result = move_files(
            source_dir=cfg.path, target_dir=target_dir, prepend_move_datetime=True
        )
        if not result.ok:
            exit_program(error=True, ctx=ctx, message=result.short_msg)

        echo_with_log(f'Moved input files to "{target_dir}":\n{format_list_of_files(files)}\n')

        exit_program(
            error=False,
            ctx=ctx,
            message=(
                f'Successfully imported {dfs.insert.shape[0]} new facilities '
                f'and updated {dfs.update.shape[0]} existing facilities!'
            ),
        )
