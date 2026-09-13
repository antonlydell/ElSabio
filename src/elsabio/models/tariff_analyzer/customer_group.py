# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The customer group models of the Tariff Analyzer module."""

# Standard library
from enum import StrEnum
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, DtypeMapping


class CustomerGroupMappingStrategyEnum(StrEnum):
    r"""The available types of customer group mapping strategies.

    Members
    -------
    FUSE_SIZE
        Map facilities to customer groups based on their contracted fuse size.

    SUBSCRIBED_POWER
        Map facilities to customer groups based on their subscribed power.

    CONNECTION_POWER
        Map facilities to customer groups based on their connection power.

    PRODUCT
        Map facilities to customer groups based on the product of their facility contract.
    """

    FUSE_SIZE = 'fuse_size'
    SUBSCRIBED_POWER = 'subscribed_power'
    CONNECTION_POWER = 'connection_power'
    PRODUCT = 'product'


class CustomerGroupDataFrameModel(BaseDataFrameModel):
    r"""A facility is part of a customer group based on its facility contract information.

    Parameters
    ----------
    customer_group_id : int
       The unique ID of the customer group.

    code : str
        The unique code of the customer group.

    name : str
        The name of the customer group.

    min_fuse_size : int or None
        The minimum fuse size [A] of the customer group.

    max_fuse_size : int or None
        The maximum fuse size [A] of the customer group.

    min_subscribed_power : float or None
        The minimum subscribed power of the customer group [kW].

    max_subscribed_power : float or None
        The maximum subscribed power of the customer group [kW].

    min_connection_power : float or None
        The minimum connection power of the customer group [kW].

    max_connection_power : float or None
        The maximum connection power of the customer group [kW].

    min_bound_included : bool, default True
        True if the minimum bound is included in the range when applying the customer
        group mapping strategy from `mapping_strategy_id` and False to exclude it.

    max_bound_included : bool, default True
        True if the maximum bound is included in the range when applying the customer
        group mapping strategy from `mapping_strategy_id` and False to exclude it.

    facility_type_id : int
        The type of facility that can be associated with the customer group.

    customer_type_id : int or None
        The type of customer that can be associated with the customer group.

    product_id : int or None
        The product of a facility contract associated with the customer group. Used
        for mapping facilities to a customer group based on the product of a facility
        contract.

    not_product_id : int or None
        The product of a facility contract to not associate with the customer group. Used
        for mapping facilities to a customer group based on a facility contract not having
        the specified product.

    mapping_strategy_id : int
        The ID of the customer group mapping strategy to apply to map facilities to a customer
        group.

    mapping_strategy_code : str
        The unique code of the customer group mapping strategy to apply to map facilities to a
        customer group.
    """

    c_customer_group_id: ClassVar[str] = 'customer_group_id'
    c_code: ClassVar[str] = 'code'
    c_name: ClassVar[str] = 'name'
    c_min_fuse_size: ClassVar[str] = 'min_fuse_size'
    c_max_fuse_size: ClassVar[str] = 'max_fuse_size'
    c_min_subscribed_power: ClassVar[str] = 'min_subscribed_power'
    c_max_subscribed_power: ClassVar[str] = 'max_subscribed_power'
    c_min_connection_power: ClassVar[str] = 'min_connection_power'
    c_max_connection_power: ClassVar[str] = 'max_connection_power'
    c_min_bound_included: ClassVar[str] = 'min_bound_included'
    c_max_bound_included: ClassVar[str] = 'max_bound_included'
    c_facility_type_id: ClassVar[str] = 'facility_type_id'
    c_customer_type_id: ClassVar[str] = 'customer_type_id'
    c_product_id: ClassVar[str] = 'product_id'
    c_not_product_id: ClassVar[str] = 'not_product_id'
    c_mapping_strategy_id: ClassVar[str] = 'mapping_strategy_id'
    c_mapping_strategy_code: ClassVar[str] = 'mapping_strategy_code'

    dtypes: ClassVar[DtypeMapping] = {
        c_customer_group_id: 'uint16[pyarrow]',
        c_code: 'string[pyarrow]',
        c_name: 'string[pyarrow]',
        c_min_fuse_size: 'uint16[pyarrow]',
        c_max_fuse_size: 'uint16[pyarrow]',
        c_min_subscribed_power: 'float64[pyarrow]',
        c_max_subscribed_power: 'float64[pyarrow]',
        c_min_connection_power: 'float64[pyarrow]',
        c_max_connection_power: 'float64[pyarrow]',
        c_min_bound_included: 'bool[pyarrow]',
        c_max_bound_included: 'bool[pyarrow]',
        c_facility_type_id: 'uint8[pyarrow]',
        c_customer_type_id: 'uint16[pyarrow]',
        c_product_id: 'uint16[pyarrow]',
        c_not_product_id: 'uint16[pyarrow]',
        c_mapping_strategy_id: 'uint8[pyarrow]',
        c_mapping_strategy_code: 'string[pyarrow]',
    }


class FacilityCustomerGroupLinkDataFrameModel(BaseDataFrameModel):
    r"""The link between a facility and a customer group.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility.

    date_id : datetime.date
        The month the link is valid for represented as the first day of the month in the
        configured business timezone of the app.

    customer_group_id : int
        The unique ID of the customer group the facility is part of.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_date_id: ClassVar[str] = 'date_id'
    c_customer_group_id: ClassVar[str] = 'customer_group_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_facility_id: 'uint32[pyarrow]',
        c_customer_group_id: 'uint16[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]
