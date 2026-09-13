# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The meter data serie value models of the Tariff Analyzer module."""

# Standard library
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, DtypeMapping


class SerieValueImportDataFrameModel(BaseDataFrameModel):
    r"""The values of a meter data serie to import to the parquet hive.

    Parameters
    ----------
    serie_type_code : str
        The unique code of the type of serie the meter data represents.

    ean : int
        The unique EAN code of the facility.

    date_id : datetime.date
        The month the meter data covers represented as the first day of the month
        in the configured business timezone of the app.

    serie_value : float
        The meter data value.

    status_id : str
        The status value of `serie_value`.
    """

    c_serie_type_code: ClassVar[str] = 'serie_type_code'
    c_ean: ClassVar[str] = 'ean'
    c_date_id: ClassVar[str] = 'date_id'
    c_serie_value: ClassVar[str] = 'serie_value'
    c_status_id: ClassVar[str] = 'status_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_serie_type_code: 'string[pyarrow]',
        c_ean: 'uint64[pyarrow]',
        c_serie_value: 'float64[pyarrow]',
        c_status_id: 'string[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]


class SerieValueDataFrameModel(BaseDataFrameModel):
    r"""The values of a meter data serie.

    Parameters
    ----------
    serie_type_code : str
        The unique code of the type of serie the meter data represents.

    facility_id : int
        The unique ID of the facility that the serie values belong to.

    ean : int
        The unique EAN code of the facility.

    date_id : datetime.date
        The month the meter data covers represented as the first day of the month
        in the configured business timezone of the app.

    serie_value : float
        The meter data value.

    status_id : str
        The status value of `serie_value`.
    """

    c_serie_type_code: ClassVar[str] = 'serie_type_code'
    c_facility_id: ClassVar[str] = 'facility_id'
    c_ean: ClassVar[str] = 'ean'
    c_date_id: ClassVar[str] = 'date_id'
    c_serie_value: ClassVar[str] = 'serie_value'
    c_status_id: ClassVar[str] = 'status_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_serie_type_code: 'string[pyarrow]',
        c_facility_id: 'uint32[pyarrow]',
        c_ean: 'uint64[pyarrow]',
        c_serie_value: 'float64[pyarrow]',
        c_status_id: 'string[pyarrow]',
    }

    parse_dates: ClassVar[list[str]] = [c_date_id]
