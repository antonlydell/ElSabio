# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The default data of the Tariff Analyzer module."""

# Local
from elsabio.database.core import Session
from elsabio.models.tariff_analyzer import (
    CalcStrategyEnum,
    CustomerGroupMappingStrategyEnum,
    CustomerTypeEnum,
    FacilityTypeEnum,
    PeriodizeStrategyEnum,
)

from .models import (
    CalcStrategy,
    CustomerGroupMappingStrategy,
    CustomerType,
    FacilityType,
    PeriodizeStrategy,
)

# FacilityType
default_facility_types = (
    {
        'code': FacilityTypeEnum.CONSUMPTION,
        'name': 'Consumption',
        'description': 'A consumption facility.',
    },
    {
        'code': FacilityTypeEnum.PRODUCTION,
        'name': 'Production',
        'description': 'A production facility.',
    },
)

# CustomerType
default_customer_types = (
    {
        'code': CustomerTypeEnum.PRIVATE_PERSON,
        'name': 'Private person',
        'description': 'A private person customer.',
    },
    {
        'code': CustomerTypeEnum.COMPANY,
        'name': 'Company',
        'description': 'A company customer.',
    },
)

# CustomerGroupMappingStrategy
default_customer_group_mapping_strategies = (
    {
        'code': CustomerGroupMappingStrategyEnum.FUSE_SIZE,
        'name': 'Fuse Size',
        'description': 'Map facilities to customer groups based on their contracted fuse size.',
    },
    {
        'code': CustomerGroupMappingStrategyEnum.SUBSCRIBED_POWER,
        'name': 'Subscribed Power',
        'description': 'Map facilities to customer groups based on their subscribed power.',
    },
    {
        'code': CustomerGroupMappingStrategyEnum.CONNECTION_POWER,
        'name': 'Connection Power',
        'description': 'Map facilities to customer groups based on their connection power.',
    },
    {
        'code': CustomerGroupMappingStrategyEnum.PRODUCT,
        'name': 'Product',
        'description': (
            'Map facilities to customer groups based on the product of their facility contract.'
        ),
    },
)

# CalcStrategy
default_calc_strategies = (
    {
        'code': CalcStrategyEnum.FIXED,
        'name': 'Fixed',
        'description': 'A fixed price tariff component type without an associated meter data.',
    },
    {
        'code': CalcStrategyEnum.PER_UNIT,
        'name': 'Per Unit',
        'description': (
            'A tariff component that is calculated per unit of a meter data serie '
            'e.g. energy or power.'
        ),
    },
    {
        'code': CalcStrategyEnum.SUBSCRIBED_POWER,
        'name': 'Subscribed Power',
        'description': (
            'A tariff component type that is calculated as a price multiplied by the '
            'subscribed power.'
        ),
    },
    {
        'code': CalcStrategyEnum.CONNECTION_POWER,
        'name': 'Connection Power',
        'description': (
            'A tariff component type that is calculated as a price multiplied by the '
            'connection power.'
        ),
    },
    {
        'code': CalcStrategyEnum.OVERSHOOT_SUBSCRIBED_POWER,
        'name': 'Overshoot Subscribed Power',
        'description': (
            'A tariff component type where the configured meter data serie is compared '
            'to see if it exceeds the subscribed power.'
        ),
    },
    {
        'code': CalcStrategyEnum.OVERSHOOT_CONNECTION_POWER,
        'name': 'Overshoot Connection Power',
        'description': (
            'A tariff component type where the configured meter data serie is compared '
            'to see if it exceeds the connection power.'
        ),
    },
    {
        'code': CalcStrategyEnum.OVERSHOOT_COMPARISON_METER_DATA_SERIE,
        'name': 'Overshoot Compared to a Meter Data Serie',
        'description': (
            'A tariff component type where the configured meter data serie is compared '
            'to see if it exceeds its comparison meter data serie.'
        ),
    },
)

# PeriodizeStrategy
default_periodize_strategies = (
    {
        'code': PeriodizeStrategyEnum.PER_MONTH,
        'name': 'Per Month',
        'description': 'A tariff component type with a price defined per month.',
    },
    {
        'code': PeriodizeStrategyEnum.PER_YEAR_DIVIDE_BY_12,
        'name': 'Per Year Divide By 12',
        'description': (
            'A tariff component type with a price defined per year where the resulting '
            'revenue/cost should be periodized per month by dividing by 12.'
        ),
    },
    {
        'code': PeriodizeStrategyEnum.PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH,
        'name': 'Per Year Periodize Over Month Length',
        'description': (
            'A tariff component type with a price defined per year where the resulting '
            'revenue/cost should be periodized per month based on based on the length '
            'of the month in proportion to the year.'
        ),
    },
)


def add_default_tariff_analyzer_models_to_session(session: Session) -> None:
    r"""Add the default Tariff Analyzer models to the database.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.
    """

    session.add_all(FacilityType(**item) for item in default_facility_types)
    session.add_all(CustomerType(**item) for item in default_customer_types)
    session.add_all(
        CustomerGroupMappingStrategy(**item) for item in default_customer_group_mapping_strategies
    )
    session.add_all(CalcStrategy(**item) for item in default_calc_strategies)
    session.add_all(PeriodizeStrategy(**item) for item in default_periodize_strategies)
