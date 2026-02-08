# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Operations for working with files."""

# Standard library
import os
from collections.abc import Sequence
from datetime import date
from functools import partial
from pathlib import Path
from typing import Literal

# Third party
import duckdb
import pandas as pd

# Local
from elsabio.core import OperationResult
from elsabio.datetime import get_current_timestamp
from elsabio.exceptions import ElSabioError
from elsabio.models.tariff_analyzer import SerieValueDataFrameModel


def read_parquet(
    path: Path, conn: duckdb.DuckDBPyConnection | None = None
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Load the contents of parquet file(s).

    Parameters
    ----------
    path : pathlib.Path
        The path to the parquet file or directory of parquet files.

    conn : duckdb.DuckDBPyConnection or None, default None
        The DuckDB connection to use for querying the parquet file(s).
        If None the global DuckDB in-memory database is used.

    Returns
    -------
    rel : duckdb.DuckDBPyRelation
        The DuckDB relation object of the dataset from the parquet file.

    result : elsabio.core.OperationResult
        The result of loading the parquet files.
    """

    if not path.exists():
        result = OperationResult(
            ok=False, short_msg=f'The parquet file path "{path}" does not exist!'
        )
        rel = duckdb.sql('SELECT NULL')
        return rel, result

    pattern = str(path / '*.parquet') if path.is_dir() else str(path)
    _conn = duckdb if conn is None else conn

    try:
        rel = _conn.read_parquet(pattern)
    except (duckdb.IOException, duckdb.InvalidInputException) as e:
        result = OperationResult(
            ok=False,
            short_msg=str(e),
            code=f'{e.__module__}.{e.__class__.__name__}',
        )
        rel = duckdb.sql('SELECT NULL')
    else:
        result = OperationResult(ok=True)

    return rel, result


def read_meter_data_parquet_hive(
    path: Path,
    serie_type_code: str,
    start_date: date,
    end_date: date | None,
    order_by: Sequence[tuple[str, Literal['ASC', 'DESC']]] | None = None,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> tuple[duckdb.DuckDBPyRelation, OperationResult]:
    r"""Load meter data from a parquet hive.

    Parameters
    ----------
    path : pathlib.Path
        The path to the parquet file or directory of parquet files.

    serie_type_code : str
        The unique code of the serie type of the meter data to load.

    start_date : datetime.date
        The start date of the interval in which to load the meter data (inclusive).

    end_date : datetime.date or None
        The end date of the interval in which to load the meter data (exclusive).
        If None the interval is open and unbounded.

    order_by : Sequence[tuple[str, Literal['ASC', 'DESC']]] or None
        The columns to use for ordering the loaded meter data.
        If None the dataset is ordered by the columns "date_id" and "facility_id".

    conn : duckdb.DuckDBPyConnection or None, default None
        The DuckDB connection to use for querying the parquet file(s).
        If None the global DuckDB in-memory database is used.

    Returns
    -------
    rel : duckdb.DuckDBPyRelation
        The DuckDB relation object of the dataset from the parquet files. Adheres to the
        structure of :class:`elsabio.models.tariff_analyzer.SerieValueDataFrameModel`.

    result : elsabio.core.OperationResult
        The result of loading the parquet files.
    """

    if not path.exists():
        result = OperationResult(
            ok=False, short_msg=f'The parquet file path "{path}" does not exist!'
        )
        rel = duckdb.sql('SELECT NULL')
        return rel, result

    c_serie_type_code = SerieValueDataFrameModel.c_serie_type_code
    c_date_id = SerieValueDataFrameModel.c_date_id
    c_facility_id = SerieValueDataFrameModel.c_facility_id

    filter_by = f"{c_serie_type_code} = '{serie_type_code}'\nAND {c_date_id} >= '{start_date}'"
    if end_date:
        filter_by = f"{filter_by}\nAND {c_date_id} < '{end_date}'"

    pattern = str(path / f'{c_serie_type_code}=*' / f'{c_date_id}=*' / '*.parquet')
    _conn = duckdb if conn is None else conn

    try:
        rel = _conn.read_parquet(pattern, hive_partitioning=True).filter(filter_by)
    except (duckdb.IOException, duckdb.InvalidInputException) as e:
        result = OperationResult(
            ok=False,
            short_msg=str(e),
            code=f'{e.__module__}.{e.__class__.__name__}',
        )
        return duckdb.sql('SELECT NULL'), result

    if order_by:
        order = ', '.join(f'{c} {asc_desc}' for c, asc_desc in order_by)
    else:
        order = f'{c_date_id} ASC, {c_facility_id} ASC'

    return rel.order(order), OperationResult(ok=True)


def write_parquet(
    rel: duckdb.DuckDBPyRelation,
    path: Path | str,
    partition_by: list[str] | None = None,
    overwrite: bool = False,
    row_group_size: int | None = None,
) -> OperationResult:
    r"""Write the contents of a DuckDB relation object to a parquet file.

    Parameters
    ----------
    rel : duckdb.DuckDBPyRelation
        The relation object of the data model to write to the parquet file.

    path : pathlib.Path
        The path to the parquet file or directory root of a parquet hive partition.

    partition_by : list[str] or None, default None
        The columns to partition the data by.

    overwrite : bool, default False
        True if files that already exist in the parquet hive should be allowed to
        be overwritten and False otherwise. Used in conjunction with `partition_by`.

    row_group_size : int or None, default None
        The number of rows to write into each row group.
        If None, the default of 122880 rows per group is used.
    """

    try:
        rel.to_parquet(
            file_name=str(path),
            partition_by=partition_by,
            overwrite=overwrite,
            row_group_size=row_group_size,
        )
    except duckdb.IOException as e:
        result = OperationResult(
            ok=False,
            short_msg=str(e),
            code=f'{e.__module__}.{e.__class__.__name__}',
        )
        rel = duckdb.sql('SELECT NULL')
    else:
        result = OperationResult(ok=True)

    return result


def write_csv(
    df: pd.DataFrame | duckdb.DuckDBPyRelation,
    output_dir: Path,
    filename: str,
    sep: str = ';',
    encoding: str = 'utf-8',
    prepend_creation_datetime: bool = True,
) -> tuple[Path, OperationResult]:
    r"""Write a dataset to a csv file.

    Parameters
    ----------
    df : pandas.DataFrame or duckdb.DuckDBPyRelation
        The DataFrame with the error content.

    path : pathlib.Path
        The path to the output directory where to write the file.

    filename : str
        The name of the output filename including the file extension.

    sep : str, default ';'
        The column separator to use in the csv file.

    encoding : str, default 'utf-8'
        The character encoding of the file.

    prepend_creation_datetime : bool, default True
        True if the creation datetime of the file should be prepended
        to the filename and False otherwise.

    Returns
    -------
    file : pathlib.Path
        The full path to the written csv file.

    result : elsabio.core.OperationResult
        The result of writing the DataFrame `df` to the csv file.

    Raises
    ------
    elsabio.ElSabioError
        If an invalid type for `df` is supplied.
    """

    if prepend_creation_datetime:
        creation_datetime = get_current_timestamp().isoformat(timespec='seconds').replace(':', '.')
        filename = f'{creation_datetime}_{filename}'

    file = output_dir / filename

    if isinstance(df, pd.DataFrame):
        func = partial(df.to_csv, path_or_buf=file, sep=sep, encoding=encoding)
    elif isinstance(df, duckdb.DuckDBPyRelation):
        func = partial(df.to_csv, file_name=str(file), sep=sep, encoding=encoding)
    else:
        raise ElSabioError(
            f'df must be a pandas.DataFrame or duckdb.DuckDBPyRelation, got {type(df)}!'
        )

    try:
        func()
    except (PermissionError, OSError) as e:
        result = OperationResult(
            ok=False, short_msg=f'Unable to write error DataFrame to file : "{file}"!\n{e!s}'
        )
    else:
        result = OperationResult(
            ok=True, short_msg=f'Successfully wrote error DataFrame to path : "{file}"!'
        )

    return file, result


def move_files(
    source_dir: Path, target_dir: Path, prepend_move_datetime: bool = False
) -> tuple[list[Path], OperationResult]:
    r"""Move the files in `source_dir` to `target_dir`.

    Parameters
    ----------
    source_dir : pathlib.Path
        The source directory where the files to move are located.

    target_dir : pathlib.Path
        The target directory where to move the files.

    prepend_move_datetime : bool, default False
        True if a the current timestamp should be prepended to the filename when
        moved to `target_dir` and False to preserve the original filename as is.

    Returns
    -------
    files : list[pathlib.Path]
        The files in `source_dir` that were moved to `target_dir`.

    result : elsabio.core.OperationResult
        The result of moving the files in `source_dir` to `target_dir`.
    """

    files = []
    errors = []

    for item in source_dir.iterdir():
        if item.is_dir():
            continue

        if prepend_move_datetime:
            move_datetime = get_current_timestamp().strftime(r'%Y-%m-%dT%H.%M.%S%z')
            target_filename = f'{move_datetime}_{item.name}'
        else:
            target_filename = item.name

        target_file = target_dir / target_filename
        files.append(item)

        try:
            os.renames(item, target_file)
        except (PermissionError, OSError) as e:
            errors.append(f'Unable to move "{item}" to "{target_dir}"!\n{e!s}')
            result = OperationResult(ok=False, short_msg=str(e), code=e.__class__.__name__)

    if errors:
        result = OperationResult(ok=False, short_msg='\n'.join(e for e in errors))
    else:
        result = OperationResult(ok=True)

    return files, result
