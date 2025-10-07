# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The default data of the Tariff Analyzer module."""

# Local
from elsabio.database.core import Session
from elsabio.models.tariff_analyzer import CalcStrategy as CalcStrategyEnum
from elsabio.models.tariff_analyzer import FacilityType as FacilityTypeEnum

from .models import CalcStrategy, FacilityType

# FacilityType
facility_type_cons = FacilityType(
    facility_type_id=FacilityTypeEnum.CONSUMPTION.value,
    name='Consumption',
    description='A consumption facility.',
)
facility_type_prod = FacilityType(
    facility_type_id=FacilityTypeEnum.PRODUCTION.value,
    name='Production',
    description='A production facility.',
)

# CalcStrategy
per_unit = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.PER_UNIT.value,
    name='per_unit',
    description='A cost per unit energy or power. E.g. SEK/kWh or SEK/kW',
)
per_year_periodize_over_month_length = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH.value,
    name='per_year_periodize_over_month_length',
    description=(
        'A cost per year that is periodizsed per month based on '
        'the length of the month in proportion to the year. E.g. SEK/year'
    ),
)
per_unit_per_year_periodize_over_month_length = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.PER_UNIT_PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH.value,
    name='per_unit_per_year_periodize_over_month_length',
    description=(
        'A cost per unit energy or power per year that is periodizsed per month based on '
        'the length of the month in proportion to the year. E.g. SEK/kW/year'
    ),
)
active_power_overshoot_subscribed_power = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.ACTIVE_POWER_OVERSHOOT_SUBSCRIBED_POWER.value,
    name='active_power_overshoot_subscribed_power',
    description='A cost for active power exceeding the subscribed power. E.g. SEK/kW/month',
)
reactive_power_cons_overshoot_active_power_cons = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.REACTIVE_POWER_CONS_OVERSHOOT_ACTIVE_POWER_CONS.value,
    name='reactive_power_cons_overshoot_active_power_cons',
    description=(
        'A cost for consuming reactive power exceeding the allowed limit '
        'in relation to the active power consumption. E.g. SEK/kVAr/year'
    ),
)
reactive_power_prod_overshoot_active_power_cons = CalcStrategy(
    calc_strategy_id=CalcStrategyEnum.REACTIVE_POWER_PROD_OVERSHOOT_ACTIVE_POWER_CONS.value,
    name='reactive_power_prod_overshoot_active_power_cons',
    description=(
        'A cost for producing reactive power exceeding the allowed limit '
        'in relation to the active power consumption. E.g. SEK/kVAr/year'
    ),
)


def add_default_tariff_analyzer_models_to_session(session: Session) -> None:
    r"""Add the default Tariff Analyzer models to the database.

    Parameters
    ----------
    session : elsabio.db.Session
        An active database session.
    """

    session.add_all(
        (
            # FacilityType
            facility_type_cons,
            facility_type_prod,
            # CalcStrategy
            per_unit,
            per_year_periodize_over_month_length,
            per_unit_per_year_periodize_over_month_length,
            active_power_overshoot_subscribed_power,
            reactive_power_cons_overshoot_active_power_cons,
            reactive_power_prod_overshoot_active_power_cons,
        )
    )
