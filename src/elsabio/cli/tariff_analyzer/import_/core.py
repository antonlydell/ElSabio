# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The entry point of the sub-command `import` of the Tariff Analyzer module."""

# Third party
import click

# Local
from elsabio.config.tariff_analyzer import DataSource


@click.command(name='import')
@click.argument('source', type=click.Choice(DataSource, case_sensitive=False))
@click.pass_context
def import_(ctx: click.Context, source: DataSource) -> None:
    """Import data to the ElSabio Tariff Analyzer module

    The import strategy is based on what is defined in the configuration.

    \b
    Examples
    --------
    Import the facilities:
        $ elsabio ta import facility

    \b
    Import the facility contracts:
        $ elsabio ta import facility_contract
    """
