# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `cg` of the Tariff Analyzer module."""

# Third party
import click

# Local
from .map_facilities import map_facilities


@click.group(name='cg')
def customer_group() -> None:
    """Manage customer groups of the ElSabio Tariff Analyzer module

    \b
    Examples
    --------
    Map facilities to customer groups for the previous month:
        $ elsabio ta cg map-facilities
    """


for cmd in (map_facilities,):
    customer_group.add_command(cmd)
