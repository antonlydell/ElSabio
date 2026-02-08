# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `tariff` of the Tariff Analyzer module."""

# Third party
import click

# Local
from .calc import calc


@click.group()
def tariff() -> None:
    """Manage tariffs of the ElSabio Tariff Analyzer module

    \b
    Examples
    --------
    Calculate all tariffs for the previous month:
        $ elsabio ta tariff calc
    """


for cmd in (calc,):
    tariff.add_command(cmd)
