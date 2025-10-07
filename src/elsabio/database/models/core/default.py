# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The default data of the core tables."""

# ruff: noqa: N816

# Local
from elsabio.database.core import Session

from .models import Currency, Unit

# Currency
sek = Currency(
    currency_id=1,
    iso_code='SEK',
    name='Svenska enkronor',
    minor_unit_name='öre',
    minor_per_major=100,
    display_decimals=2,
    symbol='kr',
    symbol_minor_unit=None,
)
euro = Currency(
    currency_id=2,
    iso_code='EUR',
    name='Euro',
    minor_unit_name='euro cent',
    minor_per_major=100,
    display_decimals=2,
    symbol='€',
    symbol_minor_unit='c',
)

# Unit
kWh = Unit(unit_id=1, code='kWh', display_name='kWh', description='kilo Watt hour')
kVArh = Unit(
    unit_id=2, code='kVArh', display_name='kVArh', description='kilo Volt Ampere reactive hour'
)
kVAh = Unit(unit_id=3, code='kVAh', display_name='kVAh', description='kilo Volt Ampere hour')

MWh = Unit(unit_id=4, code='MWh', display_name='MWh', description='Mega Watt hour')
MVArh = Unit(
    unit_id=5, code='MVArh', display_name='MVArh', description='Mega Volt Ampere reactive hour'
)
MVAh = Unit(unit_id=6, code='MVAh', display_name='MVAh', description='Mega Volt Ampere hour')

GWh = Unit(unit_id=7, code='GWh', display_name='GWh', description='Giga Watt hour')
GVArh = Unit(
    unit_id=8, code='GVArh', display_name='GVArh', description='Giga Volt Ampere reactive hour'
)
GVAh = Unit(unit_id=9, code='GVAh', display_name='GVAh', description='Giga Volt Ampere hour')

TWh = Unit(unit_id=10, code='TWh', display_name='TWh', description='Terra Watt hour')
TVArh = Unit(
    unit_id=11, code='TVArh', display_name='TVArh', description='Terra Volt Ampere reactive hour'
)
TVAh = Unit(unit_id=12, code='TVAh', display_name='TVAh', description='Terra Volt Ampere hour')

kW = Unit(unit_id=13, code='kW', display_name='kW', description='kilo Watt')
kVAr = Unit(unit_id=14, code='kVAr', display_name='kVAr', description='kilo Volt Ampere reactive')
kVA = Unit(unit_id=15, code='kVA', display_name='kVA', description='kilo Volt Ampere')

MW = Unit(unit_id=16, code='MW', display_name='MW', description='Mega Watt')
MVAr = Unit(unit_id=17, code='MVAr', display_name='MVAr', description='Mega Volt Ampere reactive')
MVA = Unit(unit_id=18, code='MVA', display_name='MVA', description='Mega Volt Ampere')

GW = Unit(unit_id=19, code='GW', display_name='GW', description='Giga Watt')
GVAr = Unit(unit_id=20, code='GVAr', display_name='GVAr', description='Giga Volt Ampere reactive')
GVA = Unit(unit_id=21, code='GVA', display_name='GVA', description='Giga Volt Ampere')

TW = Unit(unit_id=22, code='TW', display_name='TW', description='Terra Watt')
TVAr = Unit(unit_id=23, code='TVAr', display_name='TVAr', description='Terra Volt Ampere reactive')
TVA = Unit(unit_id=24, code='TVA', display_name='TVA', description='Terra Volt Ampere')

degrees_celsius = Unit(
    unit_id=25, code='degrees_celsius', display_name='°C', description='Degrees Celsius'
)

per_month = Unit(
    unit_id=26, code='per_month', display_name='/month', description='A unit per month.'
)
per_year = Unit(unit_id=27, code='per_year', display_name='/year', description='A unit per year.')

per_kWh = Unit(
    unit_id=28, code='per_kWh', display_name='/kWh', description='A unit per kilo Watt hour.'
)
per_kVArh = Unit(
    unit_id=29,
    code='per_kVArh',
    display_name='/kVArh',
    description='A unit per kilo Volt Ampere reactive hour.',
)
per_kW_per_month = Unit(
    unit_id=30,
    code='per_kW_per_month',
    display_name='/kW/month',
    description='A unit per kilo Watt per month.',
)
per_kVAr_per_month = Unit(
    unit_id=31,
    code='per_kVAr_per_month',
    display_name='/kVAr/month',
    description='A unit per kilo Volt Ampere reactive per month.',
)
per_kW_per_year = Unit(
    unit_id=32,
    code='per_kW_per_year',
    display_name='kW/year',
    description='A unit per kilo Watt per year.',
)
per_kVAr_per_year = Unit(
    unit_id=33,
    code='per_kVAr_per_year',
    display_name='/kVAr/year',
    description='A unit per kilo Volt Ampere reactive per year.',
)


def add_default_core_models_to_session(session: Session) -> None:
    r"""Add the default core models to the database.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.
    """

    session.add_all(
        (
            # Currency
            sek,
            euro,
            # Unit
            kWh,
            kVArh,
            kVAh,
            MWh,
            MVArh,
            MVAh,
            GWh,
            GVArh,
            GVAh,
            TWh,
            TVArh,
            TVAh,
            kW,
            kVAr,
            kVA,
            MW,
            MVAr,
            MVA,
            GW,
            GVAr,
            GVA,
            TW,
            TVAr,
            TVA,
            degrees_celsius,
            per_month,
            per_year,
            per_kWh,
            per_kVArh,
            per_kW_per_month,
            per_kVAr_per_month,
            per_kW_per_year,
            per_kVAr_per_year,
        )
    )
