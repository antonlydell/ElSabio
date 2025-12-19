# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""Functionality to format objects for display in the terminal."""

# Third party
import click
import pandas as pd


def display_dataframe(df: pd.DataFrame, max_nr_cols: int = 10, width: int | None = None) -> None:
    r"""Display a DataFrame in the terminal.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to display.

    max_nr_cols : int, default 10
        The maximum number of columns to display before truncating the remaining columns.

    width : int or None, default None
        The display width of the DataFrame in characters. If None the width
        will align with the terminal width defined in the click application.
    """

    with pd.option_context('display.max_columns', max_nr_cols, 'display.width', width):
        click.echo(df)
