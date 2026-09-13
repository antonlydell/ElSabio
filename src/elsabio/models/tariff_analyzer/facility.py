# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The facility models of the Tariff Analyzer module."""

# Standard library
from enum import StrEnum
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, DtypeMapping


class FacilityTypeEnum(StrEnum):
    r"""The available types of facilities.

    Members
    -------
    CONSUMPTION
        A consumption facility.

    PRODUCTION
        A production facility.
    """

    CONSUMPTION = 'consumption'
    PRODUCTION = 'production'


class FacilityTypeMappingDataFrameModel(BaseDataFrameModel):
    r"""A model of the facility types for mapping `code` to `facility_type_id`.

    Parameters
    ----------
    facility_type_id : int
        The unique ID of the facility type.

    code : str
        The unique code of the facility type.
    """

    c_facility_type_id: ClassVar[str] = 'facility_type_id'
    c_code: ClassVar[str] = 'code'

    dtypes: ClassVar[DtypeMapping] = {
        c_facility_type_id: 'uint32[pyarrow]',
        c_code: 'string[pyarrow]',
    }


class FacilityMappingDataFrameModel(BaseDataFrameModel):
    r"""A model of the facilities for mapping `ean` to `facility_id`.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility.

    ean : int
        The unique EAN code of the facility.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_ean: ClassVar[str] = 'ean'

    dtypes: ClassVar[DtypeMapping] = {c_facility_id: 'uint32[pyarrow]', c_ean: 'uint64[pyarrow]'}


class FacilityImportDataFrameModel(BaseDataFrameModel):
    r"""A model of facilities to import to the database.

    Parameters
    ----------
    ean : int
        The unique EAN code of the facility.

    ean_prod : int or None
        The EAN code of the related production facility if the facility has one.

    facility_type_code : str
        The unique code of the type of facility.

    name : str or None
        A descriptive name of the facility.

    description : str or None
        A description of the facility.
    """

    c_ean: ClassVar[str] = 'ean'
    c_ean_prod: ClassVar[str] = 'ean_prod'
    c_facility_type_code: ClassVar[str] = 'facility_type_code'
    c_name: ClassVar[str] = 'name'
    c_description: ClassVar[str] = 'description'

    dtypes: ClassVar[DtypeMapping] = {
        c_ean: 'uint64[pyarrow]',
        c_ean_prod: 'uint64[pyarrow]',
        c_facility_type_code: 'string[pyarrow]',
        c_name: 'string[pyarrow]',
        c_description: 'string[pyarrow]',
    }


class FacilityDataFrameModel(BaseDataFrameModel):
    r"""A model of the facilities represented as a DataFrame.

    Parameters
    ----------
    facility_id : int
        The unique ID of the facility.

    ean : int
        The unique EAN code of the facility.

    ean_prod : int or None
        The EAN code of the related production facility if the facility has one.

    facility_type_id : int
        The type of facility.

    name : str or None
        A descriptive name of the facility.

    description : str or None
        A description of the facility.
    """

    c_facility_id: ClassVar[str] = 'facility_id'
    c_ean: ClassVar[str] = 'ean'
    c_ean_prod: ClassVar[str] = 'ean_prod'
    c_facility_type_id: ClassVar[str] = 'facility_type_id'
    c_name: ClassVar[str] = 'name'
    c_description: ClassVar[str] = 'description'

    dtypes: ClassVar[DtypeMapping] = {
        c_facility_id: 'uint32[pyarrow]',
        c_ean: 'uint64[pyarrow]',
        c_ean_prod: 'uint64[pyarrow]',
        c_facility_type_id: 'uint8[pyarrow]',
        c_name: 'string[pyarrow]',
        c_description: 'string[pyarrow]',
    }
