# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `ta import facility` of the Tariff Analyzer module."""

# Standard library
import logging
from collections.abc import Sequence
from pathlib import Path

# Third party
import click
import duckdb

# Local
from elsabio.cli.core import Color, Obj, echo_with_log, exit_program
from elsabio.config import ConfigManager, ImportMethod
from elsabio.config.tariff_analyzer import DataSource
from elsabio.core import OperationResult
from elsabio.database import SessionFactory
from elsabio.database.tariff_analyzer import (
    bulk_insert_facilities,
    bulk_update_facilities,
    load_facility_mapping_model,
    load_facility_type_mapping_model,
)
from elsabio.operations.file import move_files, read_parquet
from elsabio.operations.tariff_analyzer import create_facility_upsert_dataframes


def _format_list_of_files(files: Sequence[Path]) -> str:
    r"""Format a list of files as an enumerated string of filenames.

    Parameters
    ----------
    files: Sequence[pathlib.Path]
        The files to format.

    Returns
    -------
    output : str
        The formatted string of filenames.
    """

    output = ''

    nr_files = len(files)

    for idx, f in enumerate(files, start=1):
        output += f'{idx:0>{nr_files}}. {f.name}'

    return output


def _load_facilities_to_import(
    method: ImportMethod, path: Path, conn: duckdb.DuckDBPyConnection
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Load the facilities to import.

    Parameters
    ----------
    method : elsabio.config.ImportMethod
        The import method to use for loading the facilities.

    path : pathlib.Path
        The path to the directory where data files to import are located if
        `method` is :attr:ImportMethod.FILE`, or the directory where the input
        data is temporarily saved before import if `method` is :attr:ImportMethod.PLUGIN`.

    conn : duckdb.DuckDBPyConnection
        An open connection DuckDB connection to use for loading the facilities.

    Returns
    -------
    rel : duckdb.DuckDBPyRelation
        The dataset of the loaded facilities.

    result : elsabio.core.OperationResult
        The result of loading the facilities.
    """

    if method == ImportMethod.FILE:
        return read_parquet(path=path, conn=conn)

    if method == ImportMethod.PLUGIN:
        result = OperationResult(
            ok=False, short_msg='facility import through plugins is not implemented yet!'
        )
        return conn.sql('SELECT NULL'), result

    # Guard for possible future import methods
    result = OperationResult(  # type: ignore[unreachable]
        ok=False,
        short_msg=(
            f'Invalid import method "{method}"! '
            f'Valid methods are: {tuple(str(m) for m in ImportMethod)}'
        ),
    )

    return conn.sql('SELECT NULL'), result


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
            import_model, result = _load_facilities_to_import(
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

        echo_with_log(f'Moved input files to "{target_dir}":\n{_format_list_of_files(files)}\n')

        exit_program(
            error=False,
            ctx=ctx,
            message=(
                f'Successfully imported {dfs.insert.shape[0]} new facilities '
                f'and updated {dfs.update.shape[0]} existing facilities!'
            ),
        )
