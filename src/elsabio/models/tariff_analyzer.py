# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The data models of the Tariff Analyzer module."""

# Standard library
from enum import Enum


class FacilityType(Enum):
    r"""The available types of facilities.

    Members
    -------
    CONSUMPTION
        A consumption facility.

    PRODUCTION
        A production facility.
    """

    CONSUMPTION = 1
    PRODUCTION = 2


class CalcStrategy(Enum):
    r"""The available strategies for the tariff calculations.

    Members
    -------
    PER_UNIT
        A cost per unit energy or power. E.g. SEK/kWh or SEK/kW

    PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH
        A cost per year that is periodizsed per month based on the
        length of the month in proportion to the year. E.g. SEK/year

    PER_UNIT_PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH
        A cost per unit energy or power per year that is periodizsed per month based on
        the length of the month in proportion to the year. E.g. SEK/kW/year

    ACTIVE_POWER_OVERSHOOT_SUBSCRIBED_POWER
        A cost for active power exceeding the subscribed power. E.g. SEK/kW/month

    REACTIVE_POWER_CONS_OVERSHOOT_ACTIVE_POWER_CONS
        A cost for consuming reactive power exceeding the allowed limit
        in relation to the active power consumption. E.g. SEK/kVAr/year

    REACTIVE_POWER_PROD_OVERSHOOT_ACTIVE_POWER_CONS
        A cost for producing reactive power exceeding the allowed limit
        in relation to the active power consumption. E.g. SEK/kVAr/year
    """

    PER_UNIT = 1
    PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH = 2
    PER_UNIT_PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH = 3
    ACTIVE_POWER_OVERSHOOT_SUBSCRIBED_POWER = 4
    REACTIVE_POWER_CONS_OVERSHOOT_ACTIVE_POWER_CONS = 5
    REACTIVE_POWER_PROD_OVERSHOOT_ACTIVE_POWER_CONS = 6
