# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The facility contract models of the Tariff Analyzer module."""

# Standard library
from enum import StrEnum
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, ColumnList, DtypeMapping


class CustomerTypeEnum(StrEnum):
    r"""The available types of customers.

    Members
    -------
    PRIVATE_PERSON
        A private person customer.

    COMPANY
        A company customer.
    """

    PRIVATE_PERSON = 'private_person'
    COMPANY = 'company'


class CustomerTypeMappingDataFrameModel(BaseDataFrameModel):
    r"""A model of the customer types for mapping `code` to `customer_type_id`.

    Parameters
    ----------
    customer_type_id : int
        The unique ID of the customer type.

    code : str
        The unique code of the customer type.
    """

    c_customer_type_id: ClassVar[str] = 'customer_type_id'
    c_code: ClassVar[str] = 'code'

    dtypes: ClassVar[DtypeMapping] = {
        c_customer_type_id: 'uint32[pyarrow]',
        c_code: 'string[pyarrow]',
    }


class FacilityContractMappingDataFrameModel(BaseDataFrameModel):
    r"""A model for determining existing facility contracts by primary key.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility.

    date_id : datetime.date
        The month the contract data is valid for represented as the first
        day of the month in the configured business timezone of the app.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_date_id: ClassVar[str] = 'date_id'

    dtypes: ClassVar[DtypeMapping] = {c_facility_id: 'uint32[pyarrow]'}

    parse_dates: ClassVar[ColumnList] = [c_date_id]


class FacilityContractImportDataFrameModel(BaseDataFrameModel):
    r"""Contract related information of a facility to import to the database.

    Parameters
    ----------
    ean : int
        The unique EAN code of the facility.

    date_id : datetime.date
        The month the contract data is valid for represented as the first day of the month in
        in the configured business timezone of the app.

    fuse_size : int or None
        The contracted fuse size [A].

    subscribed_power : float or None
        The subscribed power [kW].

    connection_power : float or None
        The connection power of the facility [kW].

    account_nr : int or None
        The bookkeeping account of the facility contract.

    customer_type_code : str
        The unique code of the type of customer associated with the facility contract.

    ext_product_id : int or None
        The external ID of the product that the facility contract belongs to. The ID
        is external from the perspective of ElSabio and internal to the parent system.
    """

    c_ean: ClassVar[str] = 'ean'
    c_date_id: ClassVar[str] = 'date_id'
    c_fuse_size: ClassVar[str] = 'fuse_size'
    c_subscribed_power: ClassVar[str] = 'subscribed_power'
    c_connection_power: ClassVar[str] = 'connection_power'
    c_account_nr: ClassVar[str] = 'account_nr'
    c_customer_type_code: ClassVar[str] = 'customer_type_code'
    c_ext_product_id: ClassVar[str] = 'ext_product_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_ean: 'uint64[pyarrow]',
        c_fuse_size: 'uint16[pyarrow]',
        c_subscribed_power: 'float64[pyarrow]',
        c_connection_power: 'float64[pyarrow]',
        c_account_nr: 'uint16[pyarrow]',
        c_customer_type_code: 'string[pyarrow]',
        c_ext_product_id: 'string[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]


class FacilityContractDataFrameModel(BaseDataFrameModel):
    r"""Contract related information of a facility valid per month.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility.

    date_id : datetime.date
        The month the contract data is valid for represented as the first day of the month in
        in the configured business timezone of the app.

    fuse_size : int or None
        The contracted fuse size [A].

    subscribed_power : float or None
        The subscribed power [kW].

    connection_power : float or None
        The connection power of the facility [kW].

    account_nr : int or None
        The bookkeeping account of the facility contract.

    customer_type_id : int
        The ID of the type of customer associated with the facility contract.

    product_id : int or None
        The ID of the product associated with the facility contract.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_date_id: ClassVar[str] = 'date_id'
    c_fuse_size: ClassVar[str] = 'fuse_size'
    c_subscribed_power: ClassVar[str] = 'subscribed_power'
    c_connection_power: ClassVar[str] = 'connection_power'
    c_account_nr: ClassVar[str] = 'account_nr'
    c_customer_type_id: ClassVar[str] = 'customer_type_id'
    c_product_id: ClassVar[str] = 'product_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_facility_id: 'uint32[pyarrow]',
        c_fuse_size: 'uint16[pyarrow]',
        c_subscribed_power: 'float64[pyarrow]',
        c_connection_power: 'float64[pyarrow]',
        c_account_nr: 'uint16[pyarrow]',
        c_customer_type_id: 'uint16[pyarrow]',
        c_product_id: 'uint16[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]


class FacilityContractExtendedDataFrameModel(FacilityContractDataFrameModel):
    r""":class:`FacilityContractDataFrameModel` with extended information.

    Parameters
    ----------
    facility_type_id : int
        The unique ID of the type of facility associated with the contract.
    """

    c_facility_type_id: ClassVar[str] = 'facility_type_id'

    dtypes: ClassVar[DtypeMapping] = FacilityContractDataFrameModel.dtypes | {
        c_facility_type_id: 'uint8[pyarrow]'
    }
