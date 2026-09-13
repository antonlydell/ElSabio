# ElSabio
# Copyright (C) 2025-present Anton Lydell
# SPDX-License-Identifier: GPL-3.0-or-later
# See the LICENSE file in the project root for details.

r"""The product models of the Tariff Analyzer module."""

# Standard library
from typing import ClassVar

# Local
from elsabio.models.core import BaseDataFrameModel, DtypeMapping


class ProductMappingDataFrameModel(BaseDataFrameModel):
    r"""A model of the products for mapping `external_id` to `product_id`.

    Parameters
    ----------
    product_id : int
        The unique ID of the product.

    external_id : str
        The unique ID of the product in the parent system.
    """

    c_product_id: ClassVar[str] = 'product_id'
    c_external_id: ClassVar[str] = 'external_id'

    dtypes: ClassVar[DtypeMapping] = {
        c_product_id: 'uint16[pyarrow]',
        c_external_id: 'string[pyarrow]',
    }


class ProductImportDataFrameModel(BaseDataFrameModel):
    r"""A model of products to import to the database.

    Parameters
    ----------
    external_id : str
        The unique ID of the product in the parent system.

    name : str
        The unique name of the product.

    description : str or None
        A description of the product.
    """

    c_external_id: ClassVar[str] = 'external_id'
    c_name: ClassVar[str] = 'name'
    c_description: ClassVar[str] = 'description'

    dtypes: ClassVar[DtypeMapping] = {
        c_external_id: 'string[pyarrow]',
        c_name: 'string[pyarrow]',
        c_description: 'string[pyarrow]',
    }


class ProductDataFrameModel(BaseDataFrameModel):
    r"""Products that can be associated with facility contracts.

    Parameters
    ----------
    product_id : int
        The unique ID of the product.

    external_id : str
        The unique ID of the product in the parent system.

    name : str
        The unique name of the product.

    description : str or None
        A description of the product.
    """

    c_product_id: ClassVar[str] = 'product_id'
    c_external_id: ClassVar[str] = 'external_id'
    c_name: ClassVar[str] = 'name'
    c_description: ClassVar[str] = 'description'

    dtypes: ClassVar[DtypeMapping] = {
        c_product_id: 'uint16[pyarrow]',
        c_external_id: 'string[pyarrow]',
        c_name: 'string[pyarrow]',
        c_description: 'string[pyarrow]',
    }
