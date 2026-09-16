# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The tariff calculation models of the Tariff Analyzer module."""

# Standard library
from enum import StrEnum
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, DtypeMapping

# DuckDB column data types
FACILITY_ID_DTYPE = 'UINTEGER'
DATE_ID_DTYPE = 'DATE'
TARIFF_ID_DTYPE = 'USMALLINT'
TARIFF_COST_GROUP_ID_DTYPE = 'USMALLINT'
CUSTOMER_GROUP_ID_DTYPE = 'USMALLINT'
TARIFF_COMPONENT_TYPE_ID_DTYPE = 'USMALLINT'
TARIFF_COMPONENT_ID_DTYPE = 'UINTEGER'
TARIFF_PRICE_DTYPE = 'DECIMAL(20, 6)'
TARIFF_VALUE_DTYPE = 'DECIMAL(20, 3)'
SERIE_VALUE_DTYPE = 'DECIMAL(20, 3)'


class CalcStrategyEnum(StrEnum):
    r"""The available calculation strategies for tariff component types.

    Members
    -------
    FIXED
        A fixed price tariff component type without an associated meter data serie.

    PER_UNIT
        A tariff component type that is calculated per unit of a meter data serie
        e.g. energy or power.

    SUBSCRIBED_POWER
        A tariff component type that is calculated as a price multiplied by the
        subscribed power.

    CONNECTION_POWER
        A tariff component type that is calculated as a price multiplied by the
        connection power.

    OVERSHOOT_SUBSCRIBED_POWER
        A tariff component type where the configured meter data serie is compared
        to see if it exceeds the subscribed power.

    OVERSHOOT_CONNECTION_POWER
        A tariff component type where the configured meter data serie is compared
        to see if it exceeds the connection power.

    OVERSHOOT_COMPARISON_METER_DATA_SERIE
        A tariff component type where the configured meter data serie is compared
        to see if it exceeds its comparison meter data serie.
    """

    FIXED = 'fixed'
    PER_UNIT = 'per_unit'
    SUBSCRIBED_POWER = 'subscribed_power'
    CONNECTION_POWER = 'connection_power'
    OVERSHOOT_SUBSCRIBED_POWER = 'overshoot_subscribed_power'
    OVERSHOOT_CONNECTION_POWER = 'overshoot_connection_power'
    OVERSHOOT_COMPARISON_METER_DATA_SERIE = 'overshoot_comparison_meter_data_serie'


class PeriodizeStrategyEnum(StrEnum):
    r"""The available periodization strategies for tariff component types.

    Periodization means how to periodize a calculated revenue/cost into a
    monthly resolution.

    Members
    -------
    PER_MONTH
        A tariff component type with a price defined per month.

    PER_YEAR_DIVIDE_BY_12
        A tariff component type with a price defined per year where the resulting
        revenue/cost should be periodized per month by dividing by 12.

    PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH
        A tariff component type with a price defined per year where the resulting
        revenue/cost should be periodized per month based on the length
        of the month in proportion to the year.
    """

    PER_MONTH = 'per_month'
    PER_YEAR_DIVIDE_BY_12 = 'per_year_divide_by_12'
    PER_YEAR_PERIODIZE_OVER_MONTH_LENGTH = 'per_year_periodize_over_month_length'


class TariffDataFrameModel(BaseDataFrameModel):
    r"""The tariffs available to work with, presented by name rather than by ID.

    Parameters
    ----------
    tariff_id : int
        The unique ID of the tariff.

    name : str
        The unique name of the tariff.

    currency_iso_code : str
        The ISO code of the currency of the tariff. E.g. SEK.

    validity_start : datetime.date or None
        The start date the tariff is valid from (inclusive)
        in the configured business timezone of the app.

    validity_end : datetime.date or None
        The end date the tariff is valid until (exclusive)
        in the configured business timezone of the app.

    last_edited_at : datetime.datetime
        The timestamp at which the tariff itself was last edited (UTC). The timestamp of
        the latest update of the tariff and the timestamp of its creation if it has never
        been updated. It does not yet cover the cost groups, the palette and the components
        that belong to the tariff.
    """

    c_tariff_id: ClassVar[str] = 'tariff_id'
    c_name: ClassVar[str] = 'name'
    c_currency_iso_code: ClassVar[str] = 'currency_iso_code'
    c_validity_start: ClassVar[str] = 'validity_start'
    c_validity_end: ClassVar[str] = 'validity_end'
    c_last_edited_at: ClassVar[str] = 'last_edited_at'

    dtypes: ClassVar[DtypeMapping] = {
        c_tariff_id: 'uint16[pyarrow]',
        c_name: 'string[pyarrow]',
        c_currency_iso_code: 'string[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_validity_start, c_validity_end, c_last_edited_at]


class TariffCalculationDataFrameModel(BaseDataFrameModel):
    r"""The model of the input dataset to the tariff calculations.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility the tariff value references.

    date_id : datetime.date
        The month the tariff value is valid for represented as the first day of
        the month in in the configured business timezone of the app.

    tariff_id : int
        The unique ID of the tariff that the computed value is associated with.

    tariff_cost_group_id : int
        The unique ID of the tariff cost group that the facility belongs to.

    customer_group_id : int
        The unique ID of the customer group that the facility belongs to.

    tariff_component_type_id : int
        The unique ID of type of tariff component that the tariff value is calculated from.

    tariff_component_id : int
        The unique ID of the tariff component that the tariff value is calculated from.

    calc_strategy_code : str
        The unique code of the calculation strategy to apply to the tariff calculations.

    periodize_strategy_code : str
        The unique code of the periodization strategy to to periodize the calculated tariff value
        to a monthly resolution.

    total_price : float
        The total price of the tariff component that was used in the tariff value calculation.
        The total price is the sum of `price` and `authority_fee`.

    price : float
        The price of the tariff component that was used in the tariff value calculation.

    authority_fee : float
        The authority fee of the tariff component that was used in the tariff value calculation.

    subscribed_power : float
        The subscribed power from the contract of the facility [kW].

    connection_power : float
        The connection power from the contract of the facility [kW].

    serie_type_code : str
        The unique code of the meter data serie to use in the calculation of a tariff component.

    comparison_serie_type_code : str
        The unique code of the meter data serie to compare against `serie_type_code` in
        tariff calculations for overshoot components.

    overshoot_limit : float
        The allowed limit of an overshoot component. in relation to `subscribed_power`,
        `connection_power` or `comparison_serie_value`.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_date_id: ClassVar[str] = 'date_id'

    c_tariff_id: ClassVar[str] = 'tariff_id'
    c_tariff_cost_group_id: ClassVar[str] = 'tariff_cost_group_id'
    c_customer_group_id: ClassVar[str] = 'customer_group_id'
    c_tariff_component_type_id: ClassVar[str] = 'tariff_component_type_id'
    c_tariff_component_id: ClassVar[str] = 'tariff_component_id'

    c_calc_strategy_code: ClassVar[str] = 'calc_strategy_code'
    c_periodize_strategy_code: ClassVar[str] = 'periodize_strategy_code'

    c_total_price: ClassVar[str] = 'total_price'
    c_price: ClassVar[str] = 'price'
    c_authority_fee: ClassVar[str] = 'authority_fee'

    c_subscribed_power: ClassVar[str] = 'subscribed_power'
    c_connection_power: ClassVar[str] = 'connection_power'
    c_serie_type_code: ClassVar[str] = 'serie_type_code'
    c_comparison_serie_type_code: ClassVar[str] = 'comparison_serie_type_code'
    c_overshoot_limit: ClassVar[str] = 'overshoot_limit'

    duckdb_dtypes: ClassVar[DtypeMapping] = {
        c_facility_id: FACILITY_ID_DTYPE,
        c_date_id: DATE_ID_DTYPE,
        c_tariff_id: TARIFF_ID_DTYPE,
        c_tariff_cost_group_id: TARIFF_COST_GROUP_ID_DTYPE,
        c_customer_group_id: CUSTOMER_GROUP_ID_DTYPE,
        c_tariff_component_type_id: TARIFF_COMPONENT_TYPE_ID_DTYPE,
        c_tariff_component_id: TARIFF_COMPONENT_ID_DTYPE,
        c_calc_strategy_code: 'VARCHAR',
        c_periodize_strategy_code: 'VARCHAR',
        c_total_price: TARIFF_PRICE_DTYPE,
        c_price: TARIFF_PRICE_DTYPE,
        c_authority_fee: TARIFF_PRICE_DTYPE,
        c_overshoot_limit: 'DECIMAL(9, 6)',
        c_subscribed_power: SERIE_VALUE_DTYPE,
        c_connection_power: SERIE_VALUE_DTYPE,
        c_serie_type_code: 'VARCHAR',
        c_comparison_serie_type_code: 'VARCHAR',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]


class TariffCalculationExtendedDataFrameModel(TariffCalculationDataFrameModel):
    r"""The extended dataset of input data to the tariff calculations.

    Parameters
    ----------
    periodization_factor : float
        The multiplication factor to periodize a tariff value into monthly resolution.

    total_value : float
        The total tariff value of the tariff component.
        The total value is the sum of `price_value` and `authority_fee_value`.

    price_value : float
        The tariff value of the price part of the tariff component.

    authority_fee_value : float
        The tariff value of the authority fee part of the tariff component.
    """

    c_periodization_factor: ClassVar[str] = 'periodization_factor'
    c_total_value: ClassVar[str] = 'total_value'
    c_price_value: ClassVar[str] = 'price_value'
    c_authority_fee_value: ClassVar[str] = 'authority_fee_value'
    c_serie_value: ClassVar[str] = 'serie_value'
    c_comparison_serie_value: ClassVar[str] = 'comparison_serie_value'
    c_overshoot_value: ClassVar[str] = 'overshoot_value'

    duckdb_dtypes: ClassVar[DtypeMapping] = TariffCalculationDataFrameModel.duckdb_dtypes | {
        c_periodization_factor: 'DOUBLE',
        c_total_value: TARIFF_VALUE_DTYPE,
        c_price_value: TARIFF_VALUE_DTYPE,
        c_authority_fee_value: TARIFF_VALUE_DTYPE,
        c_serie_value: SERIE_VALUE_DTYPE,
        c_comparison_serie_value: SERIE_VALUE_DTYPE,
        c_overshoot_value: SERIE_VALUE_DTYPE,
    }


class TariffValueFacilityDataFrameModel(BaseDataFrameModel):
    r"""The tariff value (revenue/cost) per facility and tariff component.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility the tariff value references.

    date_id : datetime.date
        The month the tariff value is valid for represented as the first day of the month in
        in the configured business timezone of the app.

    tariff_id : int
        The unique ID of the tariff that the computed value is associated with.

    tariff_cost_group_id : int
        The unique ID of the tariff cost group that the facility belongs to.

    customer_group_id : int
        The unique ID of the customer group that the facility belongs to.

    tariff_component_type_id : int
        The unique ID of type of tariff component that the tariff value is calculated from.

    tariff_component_id : int
        The unique ID of the tariff component that the tariff value is calculated from.

    total_price : float
        The total price of the tariff component that was used in the tariff value calculation.
        The total price is the sum of `price` and `authority_fee`.

    total_value : float
        The total tariff value of the tariff component.
        The total value is the sum of `price_value` and `authority_fee_value`.

    price : float
        The price of the tariff component that was used in the tariff value calculation.

    price_value : float
        The tariff value of the price part of the tariff component.

    authority_fee : float
        The authority fee of the tariff component that was used in the tariff value calculation.

    authority_fee_value : float
        The tariff value of the authority fee part of the tariff component.

    serie_value : float
        The meter data serie, subscribed power or connection power that was used in
        the tariff value calculation.

    comparison_serie_value : float
        The meter data serie, subscribed power or connection power that was compared
        against `serie_value` in the tariff value calculation.

    overshoot_value : float or None
        The calculated overshoot value for overshoot components.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_date_id: ClassVar[str] = 'date_id'
    c_tariff_id: ClassVar[str] = 'tariff_id'
    c_tariff_cost_group_id: ClassVar[str] = 'tariff_cost_group_id'
    c_customer_group_id: ClassVar[str] = 'customer_group_id'
    c_tariff_component_type_id: ClassVar[str] = 'tariff_component_type_id'
    c_tariff_component_id: ClassVar[str] = 'tariff_component_id'

    c_total_price: ClassVar[str] = 'total_price'
    c_total_value: ClassVar[str] = 'total_value'
    c_price: ClassVar[str] = 'price'
    c_price_value: ClassVar[str] = 'price_value'
    c_authority_fee: ClassVar[str] = 'authority_fee'
    c_authority_fee_value: ClassVar[str] = 'authority_fee_value'

    c_serie_value: ClassVar[str] = 'serie_value'
    c_comparison_serie_value: ClassVar[str] = 'comparison_serie_value'
    c_overshoot_value: ClassVar[str] = 'overshoot_value'

    duckdb_dtypes: ClassVar[DtypeMapping] = {
        c_facility_id: FACILITY_ID_DTYPE,
        c_date_id: DATE_ID_DTYPE,
        c_tariff_id: TARIFF_ID_DTYPE,
        c_tariff_cost_group_id: TARIFF_COST_GROUP_ID_DTYPE,
        c_customer_group_id: CUSTOMER_GROUP_ID_DTYPE,
        c_tariff_component_type_id: TARIFF_COMPONENT_TYPE_ID_DTYPE,
        c_tariff_component_id: TARIFF_COMPONENT_ID_DTYPE,
        c_total_price: TARIFF_PRICE_DTYPE,
        c_total_value: TARIFF_VALUE_DTYPE,
        c_price: TARIFF_PRICE_DTYPE,
        c_price_value: TARIFF_VALUE_DTYPE,
        c_authority_fee: TARIFF_PRICE_DTYPE,
        c_authority_fee_value: TARIFF_VALUE_DTYPE,
        c_serie_value: SERIE_VALUE_DTYPE,
        c_comparison_serie_value: SERIE_VALUE_DTYPE,
        c_overshoot_value: SERIE_VALUE_DTYPE,
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]


class TariffValueTotalDataFrameModel(BaseDataFrameModel):
    r"""The total tariff value (revenue/cost) per tariff component.

    Parameters
    ----------
    tariff_id : int
        The unique ID of the tariff that the computed value is associated with.

    date_id : datetime.date
        The month the tariff value is valid for represented as the first day of the month in
        in the configured business timezone of the app.

    tariff_cost_group_id : int
        The unique ID of the tariff cost group associated with the tariff value.

    customer_group_id : int
        The unique ID of the customer group associated with the tariff value.

    tariff_component_type_id : int
        The unique ID of type of tariff component that the tariff value is calculated from.

    tariff_component_id : int
        The unique ID of the tariff component that the tariff value is calculated from.

    total_value : float
        The total tariff value of the tariff component.
        The total value is the sum of `price_value` and `authority_fee_value`.

    price_value : float
        The tariff value of the price part of the tariff component.

    authority_fee_value : float
        The tariff value of the authority fee part of the tariff component.
    """

    c_tariff_id: ClassVar[str] = 'tariff_id'
    c_date_id: ClassVar[str] = 'date_id'
    c_tariff_cost_group_id: ClassVar[str] = 'tariff_cost_group_id'
    c_customer_group_id: ClassVar[str] = 'customer_group_id'
    c_tariff_component_type_id: ClassVar[str] = 'tariff_component_type_id'
    c_tariff_component_id: ClassVar[str] = 'tariff_component_id'
    c_total_value: ClassVar[str] = 'total_value'
    c_price_value: ClassVar[str] = 'price_value'
    c_authority_fee_value: ClassVar[str] = 'authority_fee_value'

    duckdb_dtypes: ClassVar[DtypeMapping] = {
        c_tariff_id: TARIFF_ID_DTYPE,
        c_date_id: DATE_ID_DTYPE,
        c_tariff_cost_group_id: TARIFF_COST_GROUP_ID_DTYPE,
        c_customer_group_id: CUSTOMER_GROUP_ID_DTYPE,
        c_tariff_component_type_id: TARIFF_COMPONENT_TYPE_ID_DTYPE,
        c_tariff_component_id: TARIFF_COMPONENT_ID_DTYPE,
        c_total_value: TARIFF_VALUE_DTYPE,
        c_price_value: TARIFF_VALUE_DTYPE,
        c_authority_fee_value: TARIFF_VALUE_DTYPE,
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]
