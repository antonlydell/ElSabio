# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The core functionality for the sub-command `import` of the Tariff Analyzer module."""

# Standard library
from collections.abc import Sequence
from pathlib import Path

# Third party
import duckdb

# Local
from elsabio.config import ImportMethod
from elsabio.core import OperationResult
from elsabio.operations.file import read_parquet


def format_list_of_files(files: Sequence[Path]) -> str:
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


def load_data_model_to_import(
    method: ImportMethod, path: Path, conn: duckdb.DuckDBPyConnection
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Load the data model to import.

    Parameters
    ----------
    method : elsabio.config.ImportMethod
        The import method to use for loading the data.
        Import through :attr:`ImportMethod.PLUGIN` is not implemented yet.

    path : pathlib.Path
        The path to the directory where data files to import are located if
        `method` is :attr:ImportMethod.FILE`, or the directory where the input
        data is temporarily saved before import if `method` is :attr:`ImportMethod.PLUGIN`.

    conn : duckdb.DuckDBPyConnection
        An open DuckDB connection to use for loading the data.

    Returns
    -------
    rel : duckdb.DuckDBPyRelation
        The loaded dataset.

    result : elsabio.core.OperationResult
        The result of loading the data.
    """

    if method == ImportMethod.FILE:
        return read_parquet(path=path, conn=conn)

    if method == ImportMethod.PLUGIN:
        result = OperationResult(
            ok=False, short_msg='Data import through plugins is not implemented yet!'
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
